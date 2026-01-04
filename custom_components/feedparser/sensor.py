"""Feedparser sensor."""
from __future__ import annotations

import asyncio
import email.utils
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, TypedDict
from urllib.parse import urlparse

import aiohttp
import feedparser  # type: ignore[import]
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from dateutil import parser
from feedparser import FeedParserDict
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

if TYPE_CHECKING:
    pass

__version__ = "0.2.1"

COMPONENT_REPO = "https://github.com/custom-components/feedparser/"

CONF_FEED_URL = "feed_url"
CONF_DATE_FORMAT = "date_format"
CONF_LOCAL_TIME = "local_time"
CONF_INCLUSIONS = "inclusions"
CONF_EXCLUSIONS = "exclusions"
CONF_SHOW_TOPN = "show_topn"
CONF_REMOVE_SUMMARY_IMG = "remove_summary_image"

DEFAULT_DATE_FORMAT = "%a, %b %d %I:%M %p"
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_THUMBNAIL = "https://www.home-assistant.io/images/favicon-192x192-full.png"
DEFAULT_TOPN = 9999
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2
USER_AGENT = f"Home Assistant Feed-parser Integration {__version__}"
IMAGE_REGEX = r"<img.+?src=\"(.+?)\".+?>"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_FEED_URL): cv.string,
        vol.Required(CONF_DATE_FORMAT, default=DEFAULT_DATE_FORMAT): cv.string,
        vol.Optional(CONF_LOCAL_TIME, default=False): cv.boolean,
        vol.Optional(CONF_SHOW_TOPN, default=DEFAULT_TOPN): cv.positive_int,
        vol.Optional(CONF_REMOVE_SUMMARY_IMG, default=False): cv.boolean,
        vol.Optional(CONF_INCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_EXCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    },
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class FeedEntryDict(TypedDict, total=False):
    """Type definition for feed entry dictionary."""

    title: str
    link: str
    description: str
    summary: str
    content: str
    published: str
    updated: str
    created: str
    expired: str
    image: str
    author: str
    category: str


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_devices: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,  # noqa: ARG001
) -> None:
    """Set up the Feedparser sensor."""
    async_add_devices(
        [
            FeedParserSensor(
                hass=hass,
                feed=config[CONF_FEED_URL],
                name=config[CONF_NAME],
                date_format=config[CONF_DATE_FORMAT],
                show_topn=config[CONF_SHOW_TOPN],
                remove_summary_image=config[CONF_REMOVE_SUMMARY_IMG],
                inclusions=config[CONF_INCLUSIONS],
                exclusions=config[CONF_EXCLUSIONS],
                scan_interval=config[CONF_SCAN_INTERVAL],
                local_time=config[CONF_LOCAL_TIME],
            ),
        ],
        update_before_add=True,
    )


class FeedParserSensor(SensorEntity):
    """Representation of a Feedparser sensor."""

    _attr_force_update = True
    _attr_icon = "mdi:rss"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "entries"

    def __init__(
        self: FeedParserSensor,
        hass: HomeAssistant,
        feed: str,
        name: str,
        date_format: str,
        show_topn: int,
        remove_summary_image: bool,
        exclusions: list[str | None],
        inclusions: list[str | None],
        scan_interval: timedelta,
        local_time: bool,
    ) -> None:
        """Initialize the Feedparser sensor."""
        self.hass = hass
        self._feed = feed
        self._attr_name = name
        self._date_format = date_format
        self._show_topn: int = show_topn
        self._remove_summary_image = remove_summary_image
        self._inclusions = inclusions
        self._exclusions = exclusions
        self._scan_interval = scan_interval
        self._local_time = local_time
        self._entries: list[FeedEntryDict] = []
        self._attr_extra_state_attributes = {"entries": self._entries}
        self._attr_attribution = "Data retrieved using RSS feedparser"
        self._session: aiohttp.ClientSession | None = None
        self._available = True
        _LOGGER.debug("Feed %s: FeedParserSensor initialized - %s", self.name, self)

    async def async_added_to_hass(self: FeedParserSensor) -> None:
        """When entity is added to hass."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            headers={"User-Agent": USER_AGENT},
        )

    async def async_will_remove_from_hass(self: FeedParserSensor) -> None:
        """When entity will be removed from hass."""
        if self._session:
            await self._session.close()
            self._session = None

    def __repr__(self: FeedParserSensor) -> str:
        """Return the representation."""
        return (
            f'FeedParserSensor(name="{self.name}", feed="{self._feed}", '
            f"show_topn={self._show_topn}, "
            f"remove_summary_image={self._remove_summary_image}, "
            f"inclusions={self._inclusions}, "
            f"exclusions={self._exclusions}, scan_interval={self._scan_interval}, "
            f'local_time={self._local_time}, date_format="{self._date_format}")'
        )

    @property
    def available(self: FeedParserSensor) -> bool:
        """Return if entity is available."""
        return self._available

    async def async_update(self: FeedParserSensor) -> None:
        """Parse the feed and update the state of the sensor."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
                headers={"User-Agent": USER_AGENT},
            )

        _LOGGER.debug("Feed %s: Polling feed data from %s", self.name, self._feed)

        parsed_url = urlparse(self._feed)
        if parsed_url.scheme == "file":
            try:
                with open(parsed_url.path, encoding="utf-8") as file:
                    feed_text = file.read()
                parsed_feed = feedparser.parse(feed_text)
            except (OSError, UnicodeDecodeError) as err:
                _LOGGER.error(
                    "Feed %s: Error reading local file %s: %s",
                    self.name,
                    parsed_url.path,
                    err,
                )
                self._available = False
                self._attr_native_value = None
                return
        else:
            feed_text = await self._fetch_feed_with_retry()
            if not feed_text:
                self._available = False
                self._attr_native_value = None
                return
            parsed_feed = feedparser.parse(feed_text)

        if parsed_feed.bozo and parsed_feed.bozo_exception:
            _LOGGER.warning(
                "Feed %s: Feed parsing warning: %s",
                self.name,
                parsed_feed.bozo_exception,
            )

        if not parsed_feed.entries:
            self._attr_native_value = None
            self._available = True
            _LOGGER.warning("Feed %s: No entries found in feed.", self.name)
            return

        _LOGGER.debug("Feed %s: Feed data fetched successfully", self.name)

        valid_entries = [
            entry
            for entry in parsed_feed.entries
            if entry.get("title") or entry.get("link")
        ]

        if not valid_entries:
            _LOGGER.warning(
                "Feed %s: No valid entries found (missing title or link).",
                self.name,
            )
            self._attr_native_value = None
            self._available = True
            return

        entry_count = min(len(valid_entries), self._show_topn)
        self._attr_native_value = entry_count

        _LOGGER.debug(
            "Feed %s: %s entries will be added to the sensor",
            self.name,
            entry_count,
        )

        self._entries.clear()
        self._entries.extend(self._generate_entries(valid_entries[:entry_count]))
        self._available = True

        _LOGGER.debug(
            "Feed %s: Sensor state updated - %s entries",
            self.name,
            len(self.feed_entries),
        )

    async def _fetch_feed_with_retry(self: FeedParserSensor) -> str | None:
        """Fetch feed with retry logic and exponential backoff."""
        if not self._session:
            return None

        last_exception: Exception | None = None

        for attempt in range(DEFAULT_MAX_RETRIES):
            try:
                async with self._session.get(self._feed) as response:
                    response.raise_for_status()
                    return await response.text()

            except asyncio.TimeoutError as err:
                last_exception = err
                _LOGGER.warning(
                    "Feed %s: Timeout fetching feed (attempt %d/%d): %s",
                    self.name,
                    attempt + 1,
                    DEFAULT_MAX_RETRIES,
                    err,
                )

            except aiohttp.ClientError as err:
                last_exception = err
                _LOGGER.warning(
                    "Feed %s: Client error fetching feed (attempt %d/%d): %s",
                    self.name,
                    attempt + 1,
                    DEFAULT_MAX_RETRIES,
                    err,
                )

            except Exception as err:
                last_exception = err
                _LOGGER.error(
                    "Feed %s: Unexpected error fetching feed (attempt %d/%d): %s",
                    self.name,
                    attempt + 1,
                    DEFAULT_MAX_RETRIES,
                    err,
                )

            if attempt < DEFAULT_MAX_RETRIES - 1:
                delay = DEFAULT_RETRY_DELAY * (2**attempt)
                _LOGGER.debug(
                    "Feed %s: Retrying in %d seconds...",
                    self.name,
                    delay,
                )
                await asyncio.sleep(delay)

        _LOGGER.error(
            "Feed %s: Failed to fetch feed after %d attempts: %s",
            self.name,
            DEFAULT_MAX_RETRIES,
            last_exception,
        )
        return None

    def _generate_entries(
        self: FeedParserSensor,
        feed_entries: list[FeedParserDict],
    ) -> list[FeedEntryDict]:
        """Generate sensor entries from feed entries."""
        return [
            self._generate_sensor_entry(feed_entry)
            for feed_entry in feed_entries
        ]

    def _generate_sensor_entry(
        self: FeedParserSensor,
        feed_entry: FeedParserDict,
    ) -> FeedEntryDict:
        """Generate a sensor entry from a feed entry."""
        _LOGGER.debug("Feed %s: Generating sensor entry for %s", self.name, feed_entry)
        sensor_entry: FeedEntryDict = {}

        for key, value in feed_entry.items():
            if (
                (self._inclusions and key not in self._inclusions)
                or ("parsed" in key)
                or (key in self._exclusions)
            ):
                continue

            if key in ["published", "updated", "created", "expired"]:
                try:
                    parsed_date = self._parse_date(value)
                    sensor_entry[key] = parsed_date.strftime(self._date_format)  # type: ignore[literal-required]
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Feed %s: Error parsing date field %s: %s",
                        self.name,
                        key,
                        err,
                    )
                    continue

            elif key == "image":
                if isinstance(value, dict):
                    sensor_entry["image"] = value.get("href", "")  # type: ignore[literal-required]
                else:
                    sensor_entry["image"] = str(value)  # type: ignore[literal-required]

            elif key == "content":
                if isinstance(value, list) and value:
                    content_item = value[0]
                    if isinstance(content_item, dict):
                        sensor_entry["content"] = content_item.get("value", "")  # type: ignore[literal-required]
                    else:
                        sensor_entry["content"] = str(content_item)  # type: ignore[literal-required]
                elif isinstance(value, dict):
                    sensor_entry["content"] = value.get("value", "")  # type: ignore[literal-required]
                else:
                    sensor_entry["content"] = str(value) if value is not None else ""  # type: ignore[literal-required]

            else:
                if isinstance(value, (list, dict)):
                    sensor_entry[key] = str(value)  # type: ignore[literal-required]
                else:
                    sensor_entry[key] = str(value) if value is not None else ""  # type: ignore[literal-required]

        if "image" in self._inclusions and "image" not in sensor_entry:
            sensor_entry["image"] = self._process_image(feed_entry)  # type: ignore[literal-required]

        if (
            "link" in self._inclusions
            and "link" not in sensor_entry
            and (processed_link := self._process_link(feed_entry))
        ):
            sensor_entry["link"] = processed_link  # type: ignore[literal-required]

        if self._remove_summary_image and "summary" in sensor_entry:
            sensor_entry["summary"] = re.sub(  # type: ignore[literal-required]
                IMAGE_REGEX,
                "",
                sensor_entry.get("summary", ""),
            )

        _LOGGER.debug("Feed %s: Generated sensor entry: %s", self.name, sensor_entry)
        return sensor_entry

    def _parse_date(self: FeedParserSensor, date: str | None) -> datetime:
        """Parse a date string to datetime object."""
        if not date:
            raise ValueError("Date string is None or empty")

        # Detect ISO 8601 format (e.g., 2024-02-01T00:00:01Z or 2024-02-01T00:00:01+00:00)
        is_iso_format = "T" in date and (
            date.endswith("Z") or "+" in date or (date.count("-") >= 2 and ":" in date)
        )

        parsed_time: datetime | None = None

        if is_iso_format:
            _LOGGER.debug(
                "Feed %s: Detected ISO 8601 format, using dateutil parser for %s",
                self.name,
                date,
            )
            try:
                parsed_time = parser.parse(date)
            except (ValueError, TypeError) as err:
                _LOGGER.debug(
                    "Feed %s: dateutil failed for ISO date %s, trying RFC-822: %s",
                    self.name,
                    date,
                    err,
                )
                try:
                    parsed_time = email.utils.parsedate_to_datetime(date)
                except (ValueError, TypeError) as parse_err:
                    msg = (
                        f"Feed {self.name}: Unable to parse ISO 8601 date {date}, "
                        "caused by an incorrect date format"
                    )
                    raise ValueError(msg) from parse_err
        else:
            try:
                parsed_time = email.utils.parsedate_to_datetime(date)
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Feed %s: Unable to parse RFC-822 date from %s, trying dateutil",
                    self.name,
                    date,
                )
                try:
                    parsed_time = parser.parse(date)
                except (ValueError, TypeError) as err:
                    msg = (
                        f"Feed {self.name}: Unable to parse date {date}, "
                        "caused by an incorrect date format"
                    )
                    raise ValueError(msg) from err

        # Handle timezone-naive dates by assuming UTC
        if not parsed_time.tzinfo:
            _LOGGER.debug(
                "Feed %s: Date %s has no timezone, assuming UTC",
                self.name,
                date,
            )
            parsed_time = parsed_time.replace(tzinfo=timezone.utc)

        # Replace tzinfo with UTC offset if tzinfo doesn't have a TZ name
        if parsed_time.tzinfo and not parsed_time.tzname():
            offset = parsed_time.utcoffset()
            if offset:
                parsed_time = parsed_time.replace(tzinfo=timezone(offset))

        if self._local_time:
            parsed_time = dt.as_local(parsed_time)

        _LOGGER.debug("Feed %s: Parsed date: %s", self.name, parsed_time)
        return parsed_time

    def _process_image(self: FeedParserSensor, feed_entry: FeedParserDict) -> str:
        """Extract image URL from feed entry."""
        def is_image_url(url: str) -> bool:
            """Check if URL appears to be an image."""
            if not url:
                return False
            url_lower = url.lower()
            if "image/" in url_lower:
                return True
            return any(url_lower.endswith(ext) for ext in IMAGE_EXTENSIONS)

        if feed_entry.get("enclosures"):
            images = [
                enc
                for enc in feed_entry["enclosures"]
                if enc.get("type", "").startswith("image/")
                or is_image_url(enc.get("href", ""))
            ]
            if images:
                return images[0].get("href", DEFAULT_THUMBNAIL)

        if "media_content" in feed_entry:
            media_items = feed_entry["media_content"]
            if isinstance(media_items, list):
                for media in media_items:
                    if isinstance(media, dict):
                        media_type = media.get("type", "")
                        media_url = media.get("url", "")
                        if media_type.startswith("image/") or is_image_url(media_url):
                            return media_url or DEFAULT_THUMBNAIL
            elif isinstance(media_items, dict):
                media_type = media_items.get("type", "")
                media_url = media_items.get("url", "")
                if media_type.startswith("image/") or is_image_url(media_url):
                    return media_url or DEFAULT_THUMBNAIL

        if "media_thumbnail" in feed_entry:
            thumbnails = feed_entry["media_thumbnail"]
            if isinstance(thumbnails, list) and thumbnails:
                thumb = thumbnails[0]
                if isinstance(thumb, dict):
                    thumb_url = thumb.get("url", "")
                    if thumb_url:
                        return thumb_url
            elif isinstance(thumbnails, dict):
                thumb_url = thumbnails.get("url", "")
                if thumb_url:
                    return thumb_url

        if "links" in feed_entry:
            for link in feed_entry["links"]:
                if isinstance(link, dict):
                    link_type = link.get("type", "")
                    link_href = link.get("href", "")
                    if link_type.startswith("image/") or is_image_url(link_href):
                        return link_href

        if "content" in feed_entry:
            content_items = feed_entry["content"]
            if isinstance(content_items, list):
                for content_item in content_items:
                    if isinstance(content_item, dict):
                        content_value = content_item.get("value", "")
                        if content_value:
                            images = re.findall(IMAGE_REGEX, content_value)
                            if images:
                                return images[0]

        if "summary" in feed_entry:
            images = re.findall(IMAGE_REGEX, feed_entry["summary"])
            if images:
                return images[0]

        _LOGGER.debug(
            "Feed %s: Image is in inclusions, but no image was found for entry",
            self.name,
        )
        return DEFAULT_THUMBNAIL

    def _process_link(self: FeedParserSensor, feed_entry: FeedParserDict) -> str:
        """Extract link from feed entry."""
        if "links" in feed_entry and feed_entry["links"]:
            if len(feed_entry["links"]) > 1:
                _LOGGER.debug(
                    "Feed %s: More than one link found. Using the first link.",
                    self.name,
                )
            return feed_entry["links"][0].get("href", "")
        return ""

    @property
    def feed_entries(self: FeedParserSensor) -> list[FeedEntryDict]:
        """Return feed entries."""
        return self._entries

    @property
    def local_time(self: FeedParserSensor) -> bool:
        """Return local_time."""
        return self._local_time

    @local_time.setter
    def local_time(self: FeedParserSensor, value: bool) -> None:
        """Set local_time."""
        self._local_time = value

    @property
    def extra_state_attributes(self: FeedParserSensor) -> dict[str, list[FeedEntryDict]]:
        """Return entity specific state attributes."""
        return {"entries": self.feed_entries}
