import asyncio
import logging
import email.utils as eut
import datetime as dt
import io
import pathlib
import shutil
import hashlib
import itertools

from PIL import Image, UnidentifiedImageError
import aiohttp
import voluptuous as vol

from homeassistant.components.camera import (
    DEFAULT_CONTENT_TYPE,
    PLATFORM_SCHEMA,
    SUPPORT_STREAM,
    Camera,
    async_get_still_stream,
)
from homeassistant.components.camera.const import DOMAIN

from homeassistant.const import (
    CONF_ID,
    CONF_AUTHENTICATION,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    HTTP_BASIC_AUTHENTICATION,
    HTTP_DIGEST_AUTHENTICATION,
)

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.reload import async_setup_reload_service
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1

CONF_IMAGE_URL = "image_url"
CONF_FETCH_INTERVAL = "fetch_interval"
CONF_MAX_FRAMES = "max_frames"
CONF_FRAMERATE = "framerate"
CONF_QUALITY = "quality"
CONF_LOOP = "loop"

DEFAULT_NAME = "Mjpeg Timelapse Camera"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IMAGE_URL): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_FETCH_INTERVAL, default=60.0): vol.Any(
            cv.small_float, cv.positive_int
        ),
        vol.Optional(CONF_FRAMERATE, default=2): vol.Any(
            cv.small_float, cv.positive_int
        ),
        vol.Optional(CONF_MAX_FRAMES, default=100): cv.positive_int,
        vol.Optional(CONF_QUALITY, default=75): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional(CONF_LOOP, default=True): cv.boolean,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([MjpegTimelapseCamera(hass, config)])

class MjpegTimelapseCamera(Camera):
    def __init__(self, hass, device_info):
        super().__init__()
        self.hass = hass
        self._last_modified = None
        self._loaded = False

        self._image_url = device_info[CONF_IMAGE_URL]
        self._image_url_hash = hashlib.sha256(self._image_url.encode("utf-8")).hexdigest()
        self._image_dir = pathlib.Path(hass.config.path(DOMAIN)) / self._image_url_hash
        self._name = device_info[CONF_NAME]
        self._frame_interval = 1 / device_info[CONF_FRAMERATE]
        self._fetch_interval = dt.timedelta(seconds=device_info[CONF_FETCH_INTERVAL])
        self._max_frames = device_info[CONF_MAX_FRAMES]
        self._quality = device_info[CONF_QUALITY]
        self._loop = device_info[CONF_LOOP]
        self._supported_features = None

        self._remove_listener = hass.helpers.event.async_track_time_interval(self.__fetch_image, self._fetch_interval)

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def frame_interval(self):
        """Return the interval between frames of the mjpeg stream."""
        return self._frame_interval

    @property
    def fetch_interval(self):
        """Return the fetch interval."""
        return self._fetch_interval

    @property
    def max_frames(self):
        """Return the maximum frames."""
        return self._max_frames

    @property
    def quality(self):
        """Return the quality."""
        return self._quality

    async def __fetch_image(self, _time):
        session = async_get_clientsession(self.hass)

        if self._last_modified:
            headers = {"If-Modified-Since": self._last_modified}
        else:
            headers = {}

        try:
            async with session.get(self._image_url, timeout=5, headers=headers) as res:
                res.raise_for_status()

                if res.status == 304:
                    _LOGGER.debug("HTTP 304 - success")
                    return True

                last_modified = res.headers.get("Last-Modified")
                if last_modified:
                    self._last_modified = last_modified
                    last_modified = dt.datetime(*eut.parsedate(last_modified)[:6])

                data = await res.read()
                _LOGGER.debug("HTTP 200 - Last-Modified: %s", self._last_modified)

                timestamp = dt_util.as_timestamp(dt_util.as_utc(last_modified or dt_util.utcnow()))
                try:
                    await self.hass.async_add_executor_job(self.__save_image, str(int(timestamp)), data)
                except OSError as err:
                    _LOGGER.error("Can't write image to file: %s", err)

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to fetch image, %s", type(err))

    def __save_image(self, basename, data):
        try:
            image = Image.open(io.BytesIO(data)).convert('RGB')
        except UnidentifiedImageError as err:
            raise vol.Invalid("Unable to identify image file") from err

        self._image_dir.mkdir(parents=True, exist_ok=True)
        media_file = self._image_dir / "{}.jpg".format(basename)

        _LOGGER.debug("Storing file %s", media_file)

        with media_file.open("wb") as target:
            image.save(target, "JPEG", quality=self._quality)

        self.__cleanup()

    def __cleanup(self):
        images = self._image_filenames()
        total_frames = len(images)
        d = total_frames > self._max_frames and total_frames - self._max_frames or 0
        for file in images[:d]:
            file.unlink(missing_ok=True)

    def _image_filenames(self):
        return sorted(self._image_dir.glob("*.jpg"))

    def camera_image(self):
        try:
            last_image = self._image_filenames().pop()
            with open(last_image, "rb") as file:
                return file.read()
        except IndexError as err:
            return None

    async def handle_async_mjpeg_stream(self, request):
        images = self._image_filenames()

        if self._loop:
            images = itertools.cycle(images)
        else:
            images = iter(images)

        async def next_image():
            try:
                with open(next(images), "rb") as file:
                    return file.read()
            except StopIteration as err:
                return None

        return await async_get_still_stream(request, next_image, DEFAULT_CONTENT_TYPE, self._frame_interval)

    async def async_removed_from_registry(self):
        await self.hass.async_add_executor_job(shutil.rmtree, self._image_dir)

