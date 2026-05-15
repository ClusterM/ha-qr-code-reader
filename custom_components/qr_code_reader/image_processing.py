"""Support for the QR code image processing."""

from __future__ import annotations

import inspect
import io
import json
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any

from PIL import Image, ImageOps
from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode

from homeassistant.components.image_processing import ImageProcessingEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    ATTR_DECODE_METHOD,
    ATTR_ORIENTATION,
    ATTR_POLYGON,
    ATTR_QUALITY,
    ATTR_RECT,
    ATTR_SCAN_JSON,
    ATTR_SYMBOL_TYPE,
    CONF_QR_ONLY,
    CONF_SCAN_INTERVAL,
    CONF_USE_GRAYSCALE_ENHANCEMENTS,
    CONF_USE_ORIGINAL,
    CONF_USE_SCALED,
    SCAN_ROUTINE_LOG_DEBUG_BELOW_SEC,
    SCALE_FACTORS,
    merged_options,
)

_LOGGER = logging.getLogger(__name__)


def zbar_symbol_to_attributes(symbol: Any) -> dict[str, Any]:
    """Map pyzbar Decoded metadata to JSON-friendly state attributes."""
    attrs: dict[str, Any] = {}

    sym_type = getattr(symbol, "type", None)
    if sym_type is not None:
        attrs[ATTR_SYMBOL_TYPE] = (
            sym_type.name if hasattr(sym_type, "name") else str(sym_type)
        )

    rect = getattr(symbol, "rect", None)
    if rect is not None:
        attrs[ATTR_RECT] = {
            "left": int(rect.left),
            "top": int(rect.top),
            "width": int(rect.width),
            "height": int(rect.height),
        }

    polygon = getattr(symbol, "polygon", None)
    if polygon:
        points: list[list[int]] = []
        for p in polygon:
            if hasattr(p, "x") and hasattr(p, "y"):
                points.append([int(p.x), int(p.y)])
            else:
                points.append([int(p[0]), int(p[1])])
        attrs[ATTR_POLYGON] = points

    quality = getattr(symbol, "quality", None)
    if quality is not None:
        attrs[ATTR_QUALITY] = int(quality)

    orientation = getattr(symbol, "orientation", None)
    if orientation is not None:
        if isinstance(orientation, str | int | float):
            attrs[ATTR_ORIENTATION] = orientation
        elif hasattr(orientation, "name"):
            attrs[ATTR_ORIENTATION] = orientation.name
        else:
            attrs[ATTR_ORIENTATION] = str(orientation)

    return attrs


def scan_metadata_json(method: str, symbol: Any) -> str:
    """Single-line JSON with decode pipeline label and pyzbar Decoded fields."""
    payload: dict[str, Any] = {ATTR_DECODE_METHOD: method}
    payload.update(zbar_symbol_to_attributes(symbol))
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _otsu_threshold(histogram: list[int] | tuple[int, ...]) -> int:
    """Otsu threshold 0..255 from a 256-bin grayscale histogram."""
    total = sum(histogram)
    if total == 0:
        return 127
    sum_all = sum(i * histogram[i] for i in range(256))
    sum_b = 0
    w_b = 0
    max_var = 0.0
    thresh = 0
    for t in range(256):
        w_b += histogram[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * histogram[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > max_var:
            max_var = var_between
            thresh = t
    return thresh


def _normalize_mode(img: Image.Image) -> Image.Image:
    if img.mode in ("RGB", "RGBA", "L", "1"):
        return img
    return img.convert("RGB")


def _gray_variants(gray: Image.Image, prefix: str) -> Iterator[tuple[str, Image.Image]]:
    yield f"{prefix}L", gray
    yield f"{prefix}L_autocontrast", ImageOps.autocontrast(gray)
    yield f"{prefix}L_equalize", ImageOps.equalize(gray)
    t = _otsu_threshold(gray.histogram())
    yield f"{prefix}L_otsu_high(t={t})", gray.point(lambda x, thr=t: 255 if x > thr else 0)
    yield f"{prefix}L_otsu_low(t={t})", gray.point(lambda x, thr=t: 255 if x <= thr else 0)


def iter_decode_candidates(
    img: Image.Image,
    *,
    use_original: bool,
    use_grayscale_enhancements: bool,
    use_scaled: bool,
) -> Iterator[tuple[str, Image.Image]]:
    """Yield (label, image) variants to try with zbar."""
    base = _normalize_mode(img)
    gray = base.convert("L")

    if use_original:
        yield "original", base
    if use_grayscale_enhancements:
        yield from _gray_variants(gray, "")
    if use_scaled:
        w, h = gray.size
        for scale in SCALE_FACTORS:
            nw = max(32, int(w * scale))
            nh = max(32, int(h * scale))
            if (nw, nh) == (w, h):
                continue
            g2 = gray.resize((nw, nh), Image.Resampling.LANCZOS)
            yield from _gray_variants(g2, f"scale={scale:.2f}:")


def decode_best_effort(
    img: Image.Image,
    *,
    use_original: bool,
    use_grayscale_enhancements: bool,
    use_scaled: bool,
    qr_only: bool,
) -> tuple[list[Any], str | None]:
    """Try zbar on configured preprocessings until something decodes."""
    symbols_kw: dict[str, Any] = {}
    if qr_only:
        symbols_kw["symbols"] = [ZBarSymbol.QRCODE]

    for label, variant in iter_decode_candidates(
        img,
        use_original=use_original,
        use_grayscale_enhancements=use_grayscale_enhancements,
        use_scaled=use_scaled,
    ):
        _LOGGER.debug("trying %s", label)
        symbols = zbar_decode(variant, **symbols_kw)
        if symbols:
            return symbols, label
    return [], None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up QR image processing from a config entry."""
    result = async_add_entities([QrEntity(entry)])
    if inspect.isawaitable(result):
        await result


class QrEntity(ImageProcessingEntity):
    """A QR image processing entity."""

    _scan_json: str | None
    _quiet_routine_depth: int

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize QR image processing entity."""
        super().__init__()
        self._config_entry = entry
        camera = entry.data[CONF_ENTITY_ID]
        self._attr_camera_entity = camera
        name = entry.data.get(CONF_NAME, "").strip()
        if name:
            self._attr_name = name
        else:
            self._attr_name = f"QR {split_entity_id(camera)[1]}"
        self._attr_unique_id = entry.unique_id or camera
        self._attr_should_poll = False
        self._attr_state = None
        self._scan_json = None
        self._quiet_routine_depth = 0

    def _log_scan_routine(self, msg: str, *args: Any, quiet: bool) -> None:
        """INFO for manual / slow polling; DEBUG for fast timer-driven scans."""
        if quiet:
            _LOGGER.debug(msg, *args)
        else:
            _LOGGER.info(msg, *args)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Compact JSON with last successful scan metadata."""
        if self._scan_json is None:
            return {}
        return {ATTR_SCAN_JSON: self._scan_json}

    def _options(self) -> dict[str, Any]:
        return merged_options(self._config_entry)

    async def async_added_to_hass(self) -> None:
        """Register periodic update when scan_interval > 0."""
        await super().async_added_to_hass()
        interval_sec = self._options()[CONF_SCAN_INTERVAL]
        if interval_sec <= 0:
            return

        def _fire(_now: datetime) -> None:
            def _schedule_update() -> None:
                async def _timer_scan() -> None:
                    """Timer path: async_update may return before process_image runs in executor."""
                    interval = self._options()[CONF_SCAN_INTERVAL]
                    use_quiet = interval < SCAN_ROUTINE_LOG_DEBUG_BELOW_SEC
                    if use_quiet:
                        self._quiet_routine_depth += 1
                    try:
                        await self.async_update_ha_state(True)
                    except BaseException:
                        if use_quiet:
                            self._quiet_routine_depth = max(
                                0, self._quiet_routine_depth - 1
                            )
                        raise

                self.hass.async_create_task(_timer_scan())

            # Interval callback may run outside the event loop; never call
            # async_create_task from there (see HA asyncio thread safety).
            self.hass.loop.call_soon_threadsafe(_schedule_update)

        cancel = async_track_time_interval(
            self.hass,
            _fire,
            timedelta(seconds=interval_sec),
        )
        self.async_on_remove(cancel)

        async def _prime_after_add() -> None:
            try:
                await self.async_update_ha_state(True)
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Initial scheduled scan failed for %s (entity will retry on interval)",
                    self.entity_id,
                    exc_info=True,
                )

        self.hass.async_create_task(_prime_after_add())

    def process_image(self, image: bytes) -> None:
        """Process image."""
        quiet = self._quiet_routine_depth > 0
        try:
            self._log_scan_routine(
                "Starting QR scan for %s", self.entity_id, quiet=quiet
            )
            opts = self._options()
            try:
                stream = io.BytesIO(image)
                img = Image.open(stream)

                barcodes, method = decode_best_effort(
                    img,
                    use_original=opts[CONF_USE_ORIGINAL],
                    use_grayscale_enhancements=opts[CONF_USE_GRAYSCALE_ENHANCEMENTS],
                    use_scaled=opts[CONF_USE_SCALED],
                    qr_only=opts[CONF_QR_ONLY],
                )
                if barcodes:
                    first = barcodes[0]
                    payload = first.data.decode("utf-8")
                    self._attr_state = payload
                    self._scan_json = scan_metadata_json(method, first)
                    self._log_scan_routine(
                        "QR scan for %s succeeded (method=%s): %s",
                        self.entity_id,
                        method,
                        payload,
                        quiet=quiet,
                    )
                else:
                    self._attr_state = None
                    self._scan_json = None
                    self._log_scan_routine(
                        "QR scan for %s completed: no barcode detected",
                        self.entity_id,
                        quiet=quiet,
                    )
            except UnicodeDecodeError as err:
                self._attr_state = None
                self._scan_json = None
                _LOGGER.error(
                    "QR scan for %s failed: barcode data is not valid UTF-8: %s",
                    self.entity_id,
                    err,
                )
            except (OSError, ValueError) as err:
                self._attr_state = None
                self._scan_json = None
                _LOGGER.error(
                    "QR scan for %s failed while reading or decoding image: %s",
                    self.entity_id,
                    err,
                )
            except Exception:  # noqa: BLE001
                self._attr_state = None
                self._scan_json = None
                _LOGGER.exception(
                    "QR scan for %s failed with an unexpected error",
                    self.entity_id,
                )
        finally:
            if quiet:
                self._quiet_routine_depth = max(0, self._quiet_routine_depth - 1)
