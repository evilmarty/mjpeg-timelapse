# config_flow.py

import voluptuous as vol
from urllib.parse import urlparse
from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_USERNAME,
    CONF_PASSWORD,
)
from homeassistant.helpers.selector import selector
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
    CONF_ENABLING_ENTITY_ID,
    CONF_MAX_DURATION_MINUTES,
)

# Initial schema with the checkbox to indicate enabling entity usage
INITIAL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IMAGE_URL): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_FETCH_INTERVAL, default=60): int,
        vol.Optional(CONF_START_TIME, default="00:00"): vol.Coerce(str),
        vol.Optional(CONF_END_TIME, default="23:59:59"): vol.Coerce(str),
        vol.Optional(CONF_MAX_DURATION_MINUTES): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("use_enabling_entity", default=False): bool,  # Checkbox for enabling entity
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
            # Validate initial form inputs
            errors = self.validate(user_input)
            if not errors:
                if user_input.get("use_enabling_entity"):
                    # Store initial user input and proceed to the next step
                    self.context["user_input"] = user_input
                    return await self.async_step_entity_selector()
                else:
                    # Remove the checkbox entry and create entry without enabling entity
                    user_input.pop("use_enabling_entity", None)
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input,
                    )
        
        return self.async_show_form(
            step_id="user",
            data_schema=INITIAL_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"use_enabling_entity": "Use Enabling Entity"}
        )

    async def async_step_entity_selector(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Merge user input from both steps
            complete_input = {**self.context["user_input"], **user_input}
            # No need to revalidate fields that were already validated
            errors = self.validate(complete_input, validate_all=False)
            if not errors:
                # Remove the checkbox entry and create entry
                complete_input.pop("use_enabling_entity", None)
                return self.async_create_entry(
                    title=complete_input[CONF_NAME],
                    data=complete_input,
                )

        # Schema with the entity selector
        ENTITY_SELECTOR_SCHEMA = vol.Schema(
            {
                vol.Optional(CONF_ENABLING_ENTITY_ID, default=""): selector({
                    "entity": {
                        "domain": ["sensor", "binary_sensor"],
                        "multiple": False
                    }
                }),
            }
        )

        return self.async_show_form(
            step_id="entity_selector",
            data_schema=ENTITY_SELECTOR_SCHEMA,
            errors=errors,
            description_placeholders={"enabling_entity_id": "Enabling Entity"}
        )

    def validate(self, user_input, validate_all=True):
        errors = {}
        if validate_all:
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
            max_duration = user_input.get(CONF_MAX_DURATION_MINUTES)
            if max_duration is not None and max_duration < 1:
                errors[CONF_MAX_DURATION_MINUTES] = "below_minimum_value"
        else:
            # Validate only enabling entity in the second step
            if user_input.get(CONF_ENABLING_ENTITY_ID) and not user_input[CONF_ENABLING_ENTITY_ID]:
                errors[CONF_ENABLING_ENTITY_ID] = "required"

        return errors

    def has_image_url(self, image_url):
        image_urls = {
            entry.data[CONF_IMAGE_URL] for entry in self.hass.config_entries.async_entries(DOMAIN)
        }
        return image_url in image_urls
