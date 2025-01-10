from datetime import time

DOMAIN = "mjpeg_timelapse"
PLATFORMS = ["camera"]

# Configuration keys
CONF_IMAGE_URL = "image_url"
CONF_FETCH_INTERVAL = "fetch_interval"
CONF_MAX_FRAMES = "max_frames"
CONF_FRAMERATE = "framerate"
CONF_QUALITY = "quality"
CONF_LOOP = "loop"
CONF_HEADERS = "headers"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PAUSED = "paused"

# New configuration keys
CONF_START_TIME = "start_time"
CONF_END_TIME = "end_time"
CONF_ENABLING_ENTITY_ID = "enabling_entity_id"

# Default values
DEFAULT_NAME = "Mjpeg Timelapse"
DEFAULT_FETCH_INTERVAL = 60
DEFAULT_FRAMERATE = 2
DEFAULT_MAX_FRAMES = 100
DEFAULT_QUALITY = 75
DEFAULT_LOOP = True
DEFAULT_ENABLING_ENTITY_ID = ""

# Default values for new configuration keys
DEFAULT_START_TIME = time(0, 0, 0)  # Default to 00:00
DEFAULT_END_TIME = time(23, 59, 59)  # Default to 23:59:59

# Services
SERVICE_CLEAR_IMAGES = "clear_images"
SERVICE_PAUSE_RECORDING = "pause_recording"
SERVICE_RESUME_RECORDING = "resume_recording"
