"""DataUpdateCoordinator for Feedparser integration."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import aiohttp
import feedparser
from feedparser import FeedParserDict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

__version__ = "0.2.1"
USER_AGENT = f"Home Assistant Feed-parser Integration {__version__}"


class FeedParserData:
    """Data structure for feed parser results."""

    def __init__(
        self,
        feed: FeedParserDict,
        feed_url: str,
        feed_id: str,
    ) -> None:
        """Initialize feed data."""
        self.feed = feed
        self.feed_url = feed_url
        self.feed_id = feed_id
        self.valid_entries = [
            entry
            for entry in feed.entries
            if entry.get("title") or entry.get("link")
        ]


class FeedParserCoordinator(DataUpdateCoordinator[FeedParserData]):
    """Class to manage fetching feed data."""

    def __init__(
        self,
        hass: HomeAssistant,
        feed_url: str,
        name: str,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        self.feed_url = feed_url
        self.name = name
        self.feed_id = hashlib.md5(feed_url.encode()).hexdigest()
        self._session: aiohttp.ClientSession | None = None
        self._update_interval = update_interval

        self.last_successful_fetch: datetime | None = None
        self.last_error: str | None = None
        self.is_connected: bool = False
        self.fetch_count: int = 0
        self.error_count: int = 0

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=update_interval,
        )

    @property
    def configured_update_interval(self) -> timedelta:
        """Return the configured update interval."""
        return self._update_interval

    async def _async_update_data(self) -> FeedParserData:
        """Fetch data from feed."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
                headers={"User-Agent": USER_AGENT},
            )

        _LOGGER.debug("Feed %s: Polling feed data from %s", self.name, self.feed_url)
        self.fetch_count += 1

        parsed_url = urlparse(self.feed_url)
        if parsed_url.scheme == "file":
            try:
                feed_text = await self.hass.async_add_executor_job(
                    self._read_local_file, parsed_url.path
                )
                parsed_feed = await self.hass.async_add_executor_job(
                    feedparser.parse, feed_text
                )
                self.is_connected = True
                self.last_successful_fetch = datetime.now(timezone.utc)
                self.last_error = None
            except (OSError, UnicodeDecodeError) as err:
                self.is_connected = False
                self.last_error = str(err)
                self.error_count += 1
                _LOGGER.error(
                    "Feed %s: Error reading local file %s: %s",
                    self.name,
                    parsed_url.path,
                    err,
                )
                raise UpdateFailed(f"Error reading local file: {err}") from err
        else:
            feed_text = await self._fetch_feed_with_retry()
            if not feed_text:
                self.is_connected = False
                self.last_error = "Failed to fetch feed after retries"
                self.error_count += 1
                raise UpdateFailed("Failed to fetch feed")
            parsed_feed = await self.hass.async_add_executor_job(
                feedparser.parse, feed_text
            )
            self.is_connected = True
            self.last_successful_fetch = datetime.now(timezone.utc)
            self.last_error = None

        if parsed_feed.bozo and parsed_feed.bozo_exception:
            _LOGGER.warning(
                "Feed %s: Feed parsing warning: %s",
                self.name,
                parsed_feed.bozo_exception,
            )

        if not parsed_feed.entries:
            _LOGGER.warning("Feed %s: No entries found in feed.", self.name)
            return FeedParserData(parsed_feed, self.feed_url, self.feed_id)

        _LOGGER.debug("Feed %s: Feed data fetched successfully", self.name)

        return FeedParserData(parsed_feed, self.feed_url, self.feed_id)

    async def _fetch_feed_with_retry(self) -> str | None:
        """Fetch feed with retry logic and exponential backoff."""
        if not self._session:
            return None

        last_exception: Exception | None = None

        for attempt in range(DEFAULT_MAX_RETRIES):
            try:
                async with self._session.get(self.feed_url) as response:
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

    @staticmethod
    def _read_local_file(file_path: str) -> str:
        """Read local file synchronously (called from executor)."""
        with open(file_path, encoding="utf-8") as file:
            return file.read()

    async def async_shutdown(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

