from homeassistant.helpers import entity_platform

from .camera import MjpegTimelapseCamera
from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_IMAGES,
    CONF_ENABLING_ENTITY_ID,
    DEFAULT_ENABLING_ENTITY_ID,
)

async def async_setup_entry(hass, entry):
    """Setup Mjpeg Timelapse from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Add migration logic if needed
    if CONF_ENABLING_ENTITY_ID not in entry.data:
        new_data = {**entry.data, CONF_ENABLING_ENTITY_ID: DEFAULT_ENABLING_ENTITY_ID}
        hass.config_entries.async_update_entry(entry, data=new_data)

    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass, entry):
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload
