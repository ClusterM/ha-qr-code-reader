"""The QR Code Reader integration."""

from __future__ import annotations

import logging

from homeassistant.components.image_processing import DOMAIN as IMAGE_PROCESSING_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import DATA_INSTANCES

_LOGGER = logging.getLogger(__name__)


def _image_processing_entity_component(hass: HomeAssistant):
    """Return the EntityComponent for the image_processing domain."""
    return hass.data.get(DATA_INSTANCES, {}).get(IMAGE_PROCESSING_DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up QR Code Reader from a config entry."""
    entity_component = _image_processing_entity_component(hass)
    if entity_component is None:
        _LOGGER.error(
            "image_processing component is not initialized; "
            "check that manifest dependencies include image_processing"
        )
        return False

    result = await entity_component.async_setup_entry(entry)
    if not result:
        return False

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entity_component = _image_processing_entity_component(hass)
    if entity_component is None:
        return True
    return await entity_component.async_unload_entry(entry)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
