"""Constants for the Feedparser integration."""
from datetime import timedelta

DOMAIN = "feedparser"

CONF_FEED_URL = "feed_url"
CONF_DATE_FORMAT = "date_format"
CONF_LOCAL_TIME = "local_time"
CONF_INCLUSIONS = "inclusions"
CONF_EXCLUSIONS = "exclusions"
CONF_SHOW_TOPN = "show_topn"
CONF_REMOVE_SUMMARY_IMG = "remove_summary_image"
CONF_SCAN_INTERVAL_VALUE = "scan_interval_value"
CONF_SCAN_INTERVAL_UNIT = "scan_interval_unit"

DEFAULT_DATE_FORMAT = "%a, %b %d %I:%M %p"
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_SCAN_INTERVAL_VALUE = 1
DEFAULT_SCAN_INTERVAL_UNIT = "hours"
DEFAULT_THUMBNAIL = "https://www.home-assistant.io/images/favicon-192x192-full.png"
DEFAULT_TOPN = 50
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2

DATE_FORMAT_OPTIONS = {
    "%a, %b %d %I:%M %p": "Mon, Jan 15 2:30 PM",
    "%Y-%m-%d %H:%M": "2024-01-15 14:30",
    "%d/%m/%Y %H:%M": "15/01/2024 14:30",
    "%B %d, %Y": "January 15, 2024",
    "%d %b %Y": "15 Jan 2024",
    "%m/%d/%Y %I:%M %p": "01/15/2024 2:30 PM",
}

SCAN_INTERVAL_UNITS = {
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
}

IMAGE_REGEX = r"<img.+?src=\"(.+?)\".+?>"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")

