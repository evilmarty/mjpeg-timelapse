import voluptuous as vol
from urllib.parse import urlparse

from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ENTITY_ID,  # Add this import
)
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_IMAGE_URL,
    CONF_FETCH_INTERVAL,
    CONF_MAX_FRAMES,
    CONF_FRAMERATE,
    CONF_QUALITY,
    CONF_LOOP,
    CONF_HEADERS,
    CONF_START_TIME,
    CONF_END_TIME,
)

# Use vol.Coerce(str) to ensure start_time and end_time are strings
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IMAGE_URL): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_FETCH_INTERVAL, default=60): int,
        vol.Optional(CONF_START_TIME, default="00:00"): vol.Coerce(str),
        vol.Optional(CONF_END_TIME, default="23:59:59"): vol.Coerce(str),
        vol.Optional(CONF_ENTITY_ID): cv.entity_id,  # Add entity_id to schema
        vol.Optional(CONF_FRAMERATE, default=2): int,
        vol.Optional(CONF_MAX_FRAMES, default=100): int,
        vol.Optional(CONF_QUALITY, default=75): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional(CONF_LOOP, default=True): bool,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)

def valid_url(url):
    result = urlparse(url)
    return result.scheme != '' and result.netloc != ''

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Mjpeg Timelapse."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = self.validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_options(self, user_input=None):
        """Handle the options flow for Mjpeg Timelapse."""
        errors = {}
        if user_input is not None:
            errors = self.validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self.options.title,
                    data=user_input,
                )
        current_data = self.options.data if self.options else {}
        options_schema = vol.Schema(
            {
                vol.Required(CONF_IMAGE_URL, default=current_data.get(CONF_IMAGE_URL, "")): str,
                vol.Optional(CONF_NAME, default=current_data.get(CONF_NAME, DEFAULT_NAME)): str,
                vol.Optional(CONF_FETCH_INTERVAL, default=current_data.get(CONF_FETCH_INTERVAL, 60)): int,
                vol.Optional(CONF_START_TIME, default=current_data.get(CONF_START_TIME, "00:00:00")): vol.Coerce(str),
                vol.Optional(CONF_END_TIME, default=current_data.get(CONF_END_TIME, "23:59:59")): vol.Coerce(str),
                vol.Optional(CONF_ENTITY_ID, default=current_data.get(CONF_ENTITY_ID, "")): cv.entity_id,  # Add entity_id to options schema
                vol.Optional(CONF_FRAMERATE, default=current_data.get(CONF_FRAMERATE, 2)): int,
                vol.Optional(CONF_MAX_FRAMES, default=current_data.get(CONF_MAX_FRAMES, 100)): int,
                vol.Optional(CONF_QUALITY, default=current_data.get(CONF_QUALITY, 75)): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                vol.Optional(CONF_LOOP, default=current_data.get(CONF_LOOP, True)): bool,
                vol.Optional(CONF_USERNAME, default=current_data.get(CONF_USERNAME, "")): str,
                vol.Optional(CONF_PASSWORD, default=current_data.get(CONF_PASSWORD, "")): str,
            }
        )
        return self.async_show_form(
            step_id="options",
            data_schema=options_schema,
            errors=errors,
        )

    def validate(self, user_input):
        errors = {}
        image_url = user_input[CONF_IMAGE_URL]
        if not valid_url(image_url):
            errors[CONF_IMAGE_URL] = "invalid_url"
        elif self.has_image_url(image_url):
            errors[CONF_IMAGE_URL] = "already_configured"
        if user_input.get(CONF_FETCH_INTERVAL, 0) < 1:
            errors[CONF_FETCH_INTERVAL] = "below_minimum_value"
        if user_input.get(CONF_FRAMERATE, 0) < 1:
            errors[CONF_FRAMERATE] = "below_minimum_value"
        if user_input.get(CONF_MAX_FRAMES, 0) < 1:
            errors[CONF_MAX_FRAMES] = "below_minimum_value"
        if user_input.get(CONF_PASSWORD, '') != '' and user_input.get(CONF_USERNAME, '') == '':
            errors[CONF_USERNAME] = "username_required"
        return errors

    def has_image_url(self, image_url):
        image_urls = {
            entry.data[CONF_IMAGE_URL] for entry in self.hass.config_entries.async_entries(DOMAIN)
        }
        return image_url in image_urls

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({}),
        )
