"""Feedparser sensor."""
from __future__ import annotations

import email.utils
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, TypedDict

import feedparser  # type: ignore[import]
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from dateutil import parser
from feedparser import FeedParserDict
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

from .const import (
    CONF_DATE_FORMAT,
    CONF_EXCLUSIONS,
    CONF_FEED_URL,
    CONF_INCLUSIONS,
    CONF_LOCAL_TIME,
    CONF_REMOVE_SUMMARY_IMG,
    CONF_SHOW_TOPN,
    DEFAULT_DATE_FORMAT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_THUMBNAIL,
    DEFAULT_TOPN,
    DOMAIN,
    IMAGE_EXTENSIONS,
    IMAGE_REGEX,
)

MAX_ATTRIBUTE_SIZE = 15000
MAX_SUMMARY_LENGTH = 200
ESSENTIAL_FIELDS = {"title", "link", "published", "updated", "summary", "image", "author"}
from .coordinator import FeedParserCoordinator, FeedParserData

if TYPE_CHECKING:
    pass

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


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_FEED_URL): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DATE_FORMAT, default=DEFAULT_DATE_FORMAT): cv.string,
        vol.Optional(CONF_LOCAL_TIME, default=False): cv.boolean,
        vol.Optional(CONF_SHOW_TOPN, default=DEFAULT_TOPN): cv.positive_int,
        vol.Optional(CONF_REMOVE_SUMMARY_IMG, default=False): cv.boolean,
        vol.Optional(CONF_INCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_EXCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    },
)


def get_scan_interval_timedelta(value: int | timedelta) -> timedelta:
    """Convert scan interval to timedelta."""
    if isinstance(value, timedelta):
        return value
    if isinstance(value, int):
        return timedelta(seconds=value)
    return DEFAULT_SCAN_INTERVAL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Feedparser sensor from a config entry."""
    coordinator: FeedParserCoordinator = hass.data[DOMAIN][entry.entry_id]
    options = entry.options

    async_add_entities(
        [
            FeedParserSensor(
                hass=hass,
                feed=entry.data[CONF_FEED_URL],
                name=entry.data[CONF_NAME],
                date_format=options.get(CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT),
                show_topn=options.get(CONF_SHOW_TOPN, DEFAULT_TOPN),
                remove_summary_image=options.get(CONF_REMOVE_SUMMARY_IMG, False),
                inclusions=options.get(CONF_INCLUSIONS, []),
                exclusions=options.get(CONF_EXCLUSIONS, []),
                scan_interval=get_scan_interval_timedelta(
                    options.get(CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds()))
                ),
                local_time=options.get(CONF_LOCAL_TIME, False),
                coordinator=coordinator,
            ),
        ],
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_devices: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,  # noqa: ARG001
) -> None:
    """Set up the Feedparser sensor (YAML configuration)."""
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


class FeedParserSensor(CoordinatorEntity[FeedParserCoordinator], SensorEntity):
    """Representation of a Feedparser sensor."""

    _attr_force_update = True
    _attr_icon = "mdi:rss"
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
        scan_interval: timedelta | None,
        local_time: bool,
        coordinator: FeedParserCoordinator | None = None,
    ) -> None:
        """Initialize the Feedparser sensor."""
        if coordinator:
            super().__init__(coordinator)
        else:
            super().__init__(None)  # type: ignore[arg-type]

        self.hass = hass
        self._feed = feed
        self._feed_id = hashlib.md5(feed.encode()).hexdigest()
        self._attr_name = name
        self._attr_unique_id = self._feed_id
        self._date_format = date_format
        self._show_topn: int = show_topn
        self._remove_summary_image = remove_summary_image
        self._inclusions = inclusions
        self._exclusions = exclusions
        self._scan_interval = scan_interval
        self._local_time = local_time
        self._entries: list[FeedEntryDict] = []
        self._feed_title: str | None = None
        self._feed_link: str | None = None
        self._feed_image: str | None = None
        self._feed_description: str | None = None
        self._last_entry_date: str | None = None
        self._attr_extra_state_attributes = {"entries": self._entries}
        self._attr_attribution = "Data retrieved using RSS feedparser"
        self._coordinator = coordinator
        _LOGGER.debug("Feed %s: FeedParserSensor initialized", self.name)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._feed_id)},
            name=f"RSS Feed: {self.name}",
            manufacturer="Feedparser",
            model="RSS/Atom Feed",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self: FeedParserSensor) -> bool:
        """Return if entity is available."""
        if self._coordinator:
            return self.coordinator.last_update_success
        return True

    async def async_added_to_hass(self: FeedParserSensor) -> None:
        """When entity is added to hass."""
        if self._coordinator:
            await super().async_added_to_hass()
            self.async_on_remove(
                self.coordinator.async_add_listener(self._handle_coordinator_update)
            )
            self._handle_coordinator_update()
        else:
            await self.async_update()

    def _handle_coordinator_update(self: FeedParserSensor) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._attr_native_value = None
            self._entries.clear()
            self._feed_title = None
            self._feed_link = None
            self._feed_image = None
            self._feed_description = None
            self._last_entry_date = None
            self.async_write_ha_state()
            return

        data: FeedParserData = self.coordinator.data
        valid_entries = data.valid_entries

        # Extract feed metadata
        feed_info = data.feed.feed if hasattr(data.feed, 'feed') else {}
        self._feed_title = feed_info.get('title', self.name)
        self._feed_link = feed_info.get('link', self._feed)
        self._feed_description = feed_info.get('subtitle') or feed_info.get('description', '')
        
        # Try to get feed image
        if 'image' in feed_info:
            img = feed_info['image']
            if isinstance(img, dict):
                self._feed_image = img.get('href') or img.get('url', '')
            else:
                self._feed_image = str(img) if img else None
        else:
            self._feed_image = None

        if not valid_entries:
            self._attr_native_value = None
            self._entries.clear()
            self._last_entry_date = None
            self.async_write_ha_state()
            return

        entry_count = min(len(valid_entries), self._show_topn)
        self._attr_native_value = entry_count

        _LOGGER.debug(
            "Feed %s: %s entries will be added to the sensor",
            self.name,
            entry_count,
        )

        self._entries.clear()
        self._entries.extend(
            self._generate_entries(valid_entries[:entry_count])
        )
        
        # Get the date of the most recent entry
        if self._entries and self._entries[0].get('published'):
            self._last_entry_date = self._entries[0].get('published')
        elif self._entries and self._entries[0].get('updated'):
            self._last_entry_date = self._entries[0].get('updated')
        else:
            self._last_entry_date = None

        _LOGGER.debug(
            "Feed %s: Sensor state updated - %s entries",
            self.name,
            len(self.feed_entries),
        )
        self.async_write_ha_state()

    async def async_update(self: FeedParserSensor) -> None:
        """Parse the feed and update the state of the sensor (YAML mode)."""
        if self._coordinator:
            return

        _LOGGER.debug(
            "Feed %s: Using legacy update method. Consider migrating to Config Flow.",
            self.name,
        )

        from .coordinator import FeedParserCoordinator

        temp_coordinator = FeedParserCoordinator(
            hass=self.hass,
            feed_url=self._feed,
            name=self.name,
            update_interval=self._scan_interval or DEFAULT_SCAN_INTERVAL,
        )

        try:
            data = await temp_coordinator._async_update_data()
            await temp_coordinator.async_shutdown()

            if not data.valid_entries:
                self._attr_native_value = None
                self._entries.clear()
                return

            entry_count = min(len(data.valid_entries), self._show_topn)
            self._attr_native_value = entry_count

            self._entries.clear()
            self._entries.extend(
                self._generate_entries(data.valid_entries[:entry_count])
            )
        except Exception as err:
            _LOGGER.error("Feed %s: Error updating feed: %s", self.name, err)
            self._attr_native_value = None
            self._entries.clear()

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
        """Generate a sensor entry from a feed entry.
        
        Only includes essential fields to stay within Home Assistant's 16KB attribute limit.
        """
        _LOGGER.debug("Feed %s: Generating sensor entry", self.name)
        sensor_entry: FeedEntryDict = {}

        fields_to_process = self._inclusions if self._inclusions else ESSENTIAL_FIELDS

        for key, value in feed_entry.items():
            if key not in fields_to_process:
                continue
            if "parsed" in key or key in self._exclusions:
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

            elif key == "summary":
                summary_text = str(value) if value else ""
                if self._remove_summary_image:
                    summary_text = re.sub(IMAGE_REGEX, "", summary_text)
                summary_text = self._strip_html(summary_text)
                if len(summary_text) > MAX_SUMMARY_LENGTH:
                    summary_text = summary_text[:MAX_SUMMARY_LENGTH].rsplit(' ', 1)[0] + "..."
                sensor_entry["summary"] = summary_text  # type: ignore[literal-required]

            elif key in ("title", "link", "author"):
                if isinstance(value, (list, dict)):
                    sensor_entry[key] = str(value)  # type: ignore[literal-required]
                else:
                    sensor_entry[key] = str(value) if value is not None else ""  # type: ignore[literal-required]

        if "image" not in sensor_entry:
            sensor_entry["image"] = self._process_image(feed_entry)  # type: ignore[literal-required]

        if "link" not in sensor_entry:
            if processed_link := self._process_link(feed_entry):
                sensor_entry["link"] = processed_link  # type: ignore[literal-required]

        return sensor_entry

    def _strip_html(self: FeedParserSensor, text: str) -> str:
        """Strip HTML tags from text."""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _truncate_content(self: FeedParserSensor, content: str) -> str:
        """Truncate content to prevent exceeding Home Assistant attribute size limits."""
        if len(content.encode("utf-8")) > MAX_ATTRIBUTE_SIZE:
            truncated = content[:MAX_ATTRIBUTE_SIZE]
            while len(truncated.encode("utf-8")) > MAX_ATTRIBUTE_SIZE:
                truncated = truncated[:-1]
            return truncated + "... [truncated]"
        return content

    def _parse_date(self: FeedParserSensor, date: str | None) -> datetime:
        """Parse a date string to datetime object."""
        if not date:
            raise ValueError("Date string is None or empty")

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

        if not parsed_time.tzinfo:
            _LOGGER.debug(
                "Feed %s: Date %s has no timezone, assuming UTC",
                self.name,
                date,
            )
            parsed_time = parsed_time.replace(tzinfo=timezone.utc)

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
    def entity_picture(self: FeedParserSensor) -> str | None:
        """Return the feed image as entity picture."""
        return self._feed_image

    @property
    def extra_state_attributes(self: FeedParserSensor) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs: dict[str, Any] = {
            "entries": self.feed_entries,
            "feed_url": self._feed,
        }
        if self._feed_title:
            attrs["feed_title"] = self._feed_title
        if self._feed_link:
            attrs["feed_link"] = self._feed_link
        if self._feed_description:
            attrs["feed_description"] = self._feed_description
        if self._last_entry_date:
            attrs["last_entry_date"] = self._last_entry_date
        return attrs
