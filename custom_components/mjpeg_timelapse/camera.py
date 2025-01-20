import asyncio
import logging
import email.utils as eut
import datetime as dt
import io
import pathlib
import shutil
import hashlib
import itertools
from urllib.parse import urlparse
from collections import deque

from PIL import Image, UnidentifiedImageError
import aiohttp
import voluptuous as vol

from homeassistant.components.camera import (
    DEFAULT_CONTENT_TYPE,
    PLATFORM_SCHEMA,
    CameraEntityFeature,
    Camera,
    async_get_still_stream,
)
from homeassistant.components.camera.const import DOMAIN as CAMERA_DOMAIN

from homeassistant.const import (
    CONF_NAME,
    CONF_USERNAME,
    CONF_PASSWORD,
)

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.reload import async_setup_reload_service
import homeassistant.util.dt as dt_util

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
    CONF_PAUSED,
    SERVICE_CLEAR_IMAGES,
    SERVICE_PAUSE_RECORDING,
    SERVICE_RESUME_RECORDING,
    CONF_START_TIME,
    CONF_END_TIME,
    CONF_ENABLING_ENTITY_ID,
    DEFAULT_ENABLING_ENTITY_ID,
    CONF_MAX_DURATION_MINUTES,
    DEFAULT_MAX_DURATION_MINUTES,
)

from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IMAGE_URL): cv.url,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_FETCH_INTERVAL, default=60.0): vol.Any(
            cv.small_float, cv.positive_int
        ),
        vol.Optional(CONF_START_TIME, default="00:00"): vol.Coerce(str),
        vol.Optional(CONF_END_TIME, default="23:59"): vol.Coerce(str),
        vol.Optional(CONF_ENABLING_ENTITY_ID, default=DEFAULT_ENABLING_ENTITY_ID): cv.string, 
        vol.Optional(CONF_FRAMERATE, default=2): vol.Any(
            cv.small_float, cv.positive_int
        ),
        vol.Optional(CONF_MAX_FRAMES, default=100): cv.positive_int,
        vol.Optional(CONF_QUALITY, default=75): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional(CONF_LOOP, default=True): cv.boolean,
        vol.Optional(CONF_HEADERS, default={}): dict,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_MAX_DURATION_MINUTES): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))), 
    }
)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup Mjpeg Timelapse from a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    async_add_entities([MjpegTimelapseCamera(hass, data)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_CLEAR_IMAGES,
        {},
        "clear_images",
    )
    platform.async_register_entity_service(
        SERVICE_PAUSE_RECORDING,
        {},
        "pause_recording",
    )
    platform.async_register_entity_service(
        SERVICE_RESUME_RECORDING,
        {},
        "resume_recording",
    )

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup Mjpeg Timelapse Camera"""
    async_add_entities([MjpegTimelapseCamera(hass, config)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_CLEAR_IMAGES,
        {},
        "clear_images",
    )
    platform.async_register_entity_service(
        SERVICE_PAUSE_RECORDING,
        {},
        "pause_recording",
    )
    platform.async_register_entity_service(
        SERVICE_RESUME_RECORDING,
        {},
        "resume_recording",
    )

class MjpegTimelapseCamera(Camera):
    def __init__(self, hass, device_info):
        super().__init__()
        self.hass = hass
        self.last_modified = None
        self.last_updated = None
        self._fetching_listener = None

        self._attr_image_url = device_info[CONF_IMAGE_URL]
        self._attr_attribution = urlparse(self._attr_image_url).netloc
        self._attr_name = device_info.get(CONF_NAME, self._attr_attribution)
        self._attr_unique_id = hashlib.sha256(self._attr_image_url.encode("utf-8")).hexdigest()
        self.image_dir = pathlib.Path(hass.config.path(CAMERA_DOMAIN)) / self._attr_unique_id
        self._attr_frame_rate = device_info.get(CONF_FRAMERATE, 2)
        self._attr_fetch_interval = dt.timedelta(seconds=device_info.get(CONF_FETCH_INTERVAL, 60))
        self._attr_max_frames = device_info.get(CONF_MAX_FRAMES, 100)
        self._attr_quality = device_info.get(CONF_QUALITY, 100)
        self._attr_supported_features = CameraEntityFeature.ON_OFF
        self._attr_loop = device_info.get(CONF_LOOP, False)
        self._attr_headers = device_info.get(CONF_HEADERS, {})
        self._attr_username = device_info.get(CONF_USERNAME, {})
        self._attr_password = device_info.get(CONF_PASSWORD, {})
        self._attr_is_paused = device_info.get(CONF_PAUSED, False)

        # Convert string times to datetime.time objects
        self._attr_start_time = self._parse_time(device_info.get(CONF_START_TIME, "00:00"))
        self._attr_end_time = self._parse_time(device_info.get(CONF_END_TIME, "23:59"))

        self._attr_enabling_entity_id = device_info.get(CONF_ENABLING_ENTITY_ID, DEFAULT_ENABLING_ENTITY_ID)

        # New attribute for max duration in minutes, optional
        self._attr_max_duration_minutes = device_info.get(CONF_MAX_DURATION_MINUTES)

        # Add a state listener if enabling entity id is specified
        if self._attr_enabling_entity_id:
            async_track_state_change_event(
                self.hass, [self._attr_enabling_entity_id], self._enabling_entity_changed
            )

        if self._attr_is_on == True:
            self.start_fetching()

    def _parse_time(self, time_str):
        """Parse a time string and return a time object, accepting both HH:MM and HH:MM:SS formats."""
        try:
            return dt.datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            return dt.datetime.strptime(time_str, "%H:%M").time()

    async def _enabling_entity_changed(self, event):
        """Handle state changes of the enabling entity."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            self.start_fetching()
        else:
            self.stop_fetching()

    async def fetch_image(self, _time):
        # Ensure self.hass is not None before accessing its states attribute
        if self.hass is None:
            _LOGGER.error("Home Assistant instance is not set.")
            return

        # Check if the current time is within the specified start and end time
        now = dt_util.now().time()
        if not (self._attr_start_time <= now <= self._attr_end_time):
            return

        # Check the state of the enabling entity if it is specified
        if self._attr_enabling_entity_id:
            state = self.hass.states.get(self._attr_enabling_entity_id)
            if state is None or state.state != "on":
                return

        headers = {**self.headers}
        session = async_get_clientsession(self.hass)
        auth = None

        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified

        if self.username is not None:
            auth = aiohttp.BasicAuth(self.username, self.password, 'utf-8')

        try:
            async with session.get(self.image_url, timeout=5, headers=headers, auth=auth) as res:
                res.raise_for_status()
                self._attr_available = True

                if res.status == 304:
                    return

                last_modified = res.headers.get("Last-Modified")
                if last_modified:
                    self.last_modified = last_modified
                    last_modified = dt.datetime(*eut.parsedate(last_modified)[:6])

                data = await res.read()
                self.last_updated = dt_util.as_timestamp(dt_util.as_utc(last_modified or dt_util.utcnow()))
                await self.hass.async_add_executor_job(self.save_image, str(int(self.last_updated)), data)

                # Clean up old frames based on the max duration if set
                if self._attr_max_duration_minutes:
                    self.cleanup_old_frames()

        except OSError as err:
            _LOGGER.error("Can't write image for '%s' to file: %s", self.name, err)
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to fetch image for '%s': %s", self.name, err)
            self._attr_available = False

        self.async_write_ha_state()

    def cleanup_old_frames(self):
        """Remove frames older than the max duration."""
        current_time = dt_util.utcnow().timestamp()
        max_age = self._attr_max_duration_minutes * 60  # Convert minutes to seconds

        for file in self.image_filenames():
            timestamp = file.stem  # Assuming the file name is the timestamp
            file_time = dt.datetime.fromtimestamp(int(timestamp))
            if (current_time - file_time.timestamp()) > max_age:
                file.unlink(missing_ok=True)

    def start_fetching(self):
        if self._fetching_listener is None:
            self._fetching_listener = async_track_time_interval(
                self.hass, self.fetch_image, self._attr_fetch_interval
            )

    def stop_fetching(self):
        if self._fetching_listener:
            self._fetching_listener()
            self._fetching_listener = None

    async def handle_async_mjpeg_stream(self, request):
        def get_images():
            if self.loop:
                return itertools.cycle(self.image_filenames())
            else:
                return iter(self.image_filenames())

        images = get_images()

        async def next_image():
            nonlocal images

            try:
                while self.is_on:
                    try:
                        with open(next(images), "rb") as file:
                            return file.read()
                    except FileNotFoundError:
                        images = get_images()
            except StopIteration:
                return None

        return await async_get_still_stream(request, next_image, DEFAULT_CONTENT_TYPE, self.frame_interval)

    def save_image(self, basename, data):
        try:
            image = Image.open(io.BytesIO(data)).convert('RGB')
        except UnidentifiedImageError as err:
            raise vol.Invalid("Unable to identify image file") from err

        self.image_dir.mkdir(parents=True, exist_ok=True)
        media_file = self.image_dir / "{}.jpg".format(basename)

        with media_file.open("wb") as target:
            image.save(target, "JPEG", quality=self.quality)

        self.cleanup()

    def cleanup(self):
        """Removes excess images based on max frames."""
        images = self.image_filenames()
        total_frames = len(images)
        d = total_frames > self.max_frames and total_frames - self.max_frames or 0
        for file in images[:d]:
            file.unlink(missing_ok=True)

    def clear_images(self):
        """Remove all images."""
        return self.hass.async_add_executor_job(shutil.rmtree, self.image_dir)

    def image_filenames(self):
        return sorted(self.image_dir.glob("*.jpg"))

    def camera_image(self):
        try:
            last_image = self.image_filenames().pop()
            with open(last_image, "rb") as file:
                return file.read()
        except IndexError as err:
            return None

    async def async_removed_from_registry(self):
        self.stop_fetching()
        await self.clear_images()

    @property
    def should_poll(self):
        """Return false for should poll."""
        return False

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:image-multiple"

    @property
    def image_url(self):
        """Return the image url."""
        return self._attr_image_url

    @property
    def frame_rate(self):
        """Return the framerate."""
        return self._attr_frame_rate

    @property
    def frame_interval(self):
        """Return the frame interval."""
        return 1 / self.frame_rate

    @property
    def fetch_interval(self):
        """Return the fetch interval."""
        return self._attr_fetch_interval

    @property
    def max_frames(self):
        """Return the maximum frames."""
        return self._attr_max_frames

    @property
    def quality(self):
        """Return the quality."""
        return self._attr_quality

    @property
    def loop(self):
        """Indicate whether to loop or not."""
        return self._attr_loop

    @property
    def headers(self):
        """Return additional headers for request."""
        return self._attr_headers

    @property
    def username(self):
        """Return the basic auth username."""
        return self._attr_username

    @property
    def password(self):
        """Return the basic auth password."""
        return self._attr_password

    @property
    def is_paused(self):
        """Returns whether recording is paused."""
        return self._attr_is_paused

    @property
    def is_recording(self):
        """Indicate whether recording or not."""
        return self._fetching_listener is not None

    def turn_on(self):
        """Turn on the camera."""
        if not self.is_paused:
            self.start_fetching()
        self._attr_is_on = True

    def turn_off(self):
        """Turn off the camera."""
        self.stop_fetching()
        self._attr_is_on = False

    @property
    def extra_state_attributes(self):
        return {
            "image_url": self.image_url,
            "fetch_interval": self.fetch_interval.total_seconds(),
            "frame_rate": self.frame_rate,
            "max_frames": self.max_frames,
            "quality": self.quality,
            "loop": self.loop,
            "headers": self.headers,
            "last_updated": self.last_updated,
            "start_time": self._attr_start_time.strftime("%H:%M"),
            "end_time": self._attr_end_time.strftime("%H:%M:%S"),
            "max_duration_minutes": self._attr_max_duration_minutes,
        }

    def pause_recording(self):
        """Pause recording images."""
        self.stop_fetching()
        self._attr_is_paused = True
        self.schedule_update_ha_state()

    def resume_recording(self):
        """Resume recording images."""
        self.start_fetching()
        self._attr_is_paused = False
        self.schedule_update_ha_state()
