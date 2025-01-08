from homeassistant.helpers import entity_platform
from .camera import MjpegTimelapseCamera
from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_IMAGES,
    CONF_START_TIME,
    CONF_END_TIME,
)

async def async_setup_entry(hass, entry):
    """Setup Mjpeg Timelapse from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Handle reconfiguration options
    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass, entry):
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload

async def update_listener(hass, entry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
