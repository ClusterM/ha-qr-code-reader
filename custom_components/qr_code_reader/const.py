"""Constants for the QR Code Reader integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

DOMAIN = "qr_code_reader"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_USE_ORIGINAL = "use_original"
CONF_USE_GRAYSCALE_ENHANCEMENTS = "use_grayscale_enhancements"
CONF_USE_SCALED = "use_scaled"
CONF_QR_ONLY = "qr_only"

DEFAULT_SCAN_INTERVAL = 10
DEFAULT_USE_ORIGINAL = True
DEFAULT_USE_GRAYSCALE_ENHANCEMENTS = True
DEFAULT_USE_SCALED = False
DEFAULT_QR_ONLY = False

ATTR_DECODE_METHOD = "decode_method"
ATTR_SYMBOL_TYPE = "type"
ATTR_RECT = "rect"
ATTR_POLYGON = "polygon"
ATTR_QUALITY = "quality"
ATTR_ORIENTATION = "orientation"
ATTR_SCAN_JSON = "scan_json"

# Timer-driven scans with interval below this use DEBUG for routine logs (less log spam).
SCAN_ROUTINE_LOG_DEBUG_BELOW_SEC = 10

SCALE_FACTORS: tuple[float, ...] = (0.35, 0.5, 0.65, 1.5, 2.0, 3.0)


def merged_options(entry: ConfigEntry) -> dict[str, Any]:
    """Options with defaults; JSON null / missing keys must not break entity setup."""
    raw: dict[str, Any] = dict(entry.options or {})

    def pick(key: str, default: Any) -> Any:
        if key not in raw:
            return default
        val = raw[key]
        return default if val is None else val

    scan_raw = pick(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    return {
        CONF_SCAN_INTERVAL: int(float(scan_raw)),
        CONF_USE_ORIGINAL: bool(pick(CONF_USE_ORIGINAL, DEFAULT_USE_ORIGINAL)),
        CONF_USE_GRAYSCALE_ENHANCEMENTS: bool(
            pick(CONF_USE_GRAYSCALE_ENHANCEMENTS, DEFAULT_USE_GRAYSCALE_ENHANCEMENTS)
        ),
        CONF_USE_SCALED: bool(pick(CONF_USE_SCALED, DEFAULT_USE_SCALED)),
        CONF_QR_ONLY: bool(pick(CONF_QR_ONLY, DEFAULT_QR_ONLY)),
    }
