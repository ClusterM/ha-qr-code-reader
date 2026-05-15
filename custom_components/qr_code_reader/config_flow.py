"""Config flow for QR Code Reader."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DEFAULT_QR_ONLY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_GRAYSCALE_ENHANCEMENTS,
    DEFAULT_USE_ORIGINAL,
    DEFAULT_USE_SCALED,
    DOMAIN,
    CONF_QR_ONLY,
    CONF_SCAN_INTERVAL,
    CONF_USE_GRAYSCALE_ENHANCEMENTS,
    CONF_USE_ORIGINAL,
    CONF_USE_SCALED,
)

DEFAULT_OPTIONS: dict[str, Any] = {
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_USE_ORIGINAL: DEFAULT_USE_ORIGINAL,
    CONF_USE_GRAYSCALE_ENHANCEMENTS: DEFAULT_USE_GRAYSCALE_ENHANCEMENTS,
    CONF_USE_SCALED: DEFAULT_USE_SCALED,
    CONF_QR_ONLY: DEFAULT_QR_ONLY,
}

OPTION_KEYS: tuple[str, ...] = (
    CONF_SCAN_INTERVAL,
    CONF_USE_ORIGINAL,
    CONF_USE_GRAYSCALE_ENHANCEMENTS,
    CONF_USE_SCALED,
    CONF_QR_ONLY,
)


def _pipeline_option_fields(opts: dict[str, Any]) -> dict[vol.Marker, Any]:
    """Vol schema fields for preprocessing / scan options."""
    return {
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=opts[CONF_SCAN_INTERVAL],
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=86400,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
        vol.Required(
            CONF_USE_ORIGINAL,
            default=opts[CONF_USE_ORIGINAL],
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_USE_GRAYSCALE_ENHANCEMENTS,
            default=opts[CONF_USE_GRAYSCALE_ENHANCEMENTS],
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_USE_SCALED,
            default=opts[CONF_USE_SCALED],
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_QR_ONLY,
            default=opts[CONF_QR_ONLY],
        ): selector.BooleanSelector(),
    }


def _normalize_options_dict(values: dict[str, Any]) -> dict[str, Any]:
    """Coerce option values for storage."""
    out = dict(values)
    out[CONF_SCAN_INTERVAL] = int(float(out[CONF_SCAN_INTERVAL]))
    return out


def _options_from_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Pick option keys from a merged form submission."""
    return {k: user_input[k] for k in OPTION_KEYS}


def _pipeline_valid(options: dict[str, Any]) -> bool:
    return bool(
        options[CONF_USE_ORIGINAL]
        or options[CONF_USE_GRAYSCALE_ENHANCEMENTS]
        or options[CONF_USE_SCALED]
    )


class QrCodeReaderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for QR Code Reader."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> QrCodeReaderOptionsFlowHandler:
        """Get the options flow for this handler."""
        return QrCodeReaderOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick camera, name, and all scan options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            opt = _normalize_options_dict(_options_from_user_input(user_input))
            if not _pipeline_valid(opt):
                errors["base"] = "pipeline_required"
            else:
                camera = user_input[CONF_ENTITY_ID]
                await self.async_set_unique_id(camera)
                self._abort_if_unique_id_configured()

                name = user_input.get(CONF_NAME, "").strip() or None

                return self.async_create_entry(
                    title=name or self._default_title(camera),
                    data={
                        CONF_ENTITY_ID: camera,
                        CONF_NAME: name or "",
                    },
                    options=opt,
                )

        opts = dict(DEFAULT_OPTIONS)
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="camera")
            ),
            vol.Optional(CONF_NAME): selector.TextSelector(),
        }
        schema_dict.update(_pipeline_option_fields(opts))
        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    def _default_title(self, camera_entity_id: str) -> str:
        """Title when name is omitted."""
        object_id = camera_entity_id.partition(".")[2]
        return f"QR {object_id}"


class QrCodeReaderOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            opt = _normalize_options_dict(user_input)
            if not _pipeline_valid(opt):
                errors["base"] = "pipeline_required"
            else:
                return self.async_create_entry(title="", data=opt)

        opts = {**DEFAULT_OPTIONS, **self.config_entry.options}
        schema = vol.Schema(_pipeline_option_fields(opts))

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
