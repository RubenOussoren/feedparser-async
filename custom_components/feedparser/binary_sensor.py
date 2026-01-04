"""Feedparser binary sensor."""
from __future__ import annotations

import hashlib
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FEED_URL, DOMAIN
from .coordinator import FeedParserCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Feedparser binary sensors from a config entry."""
    coordinator: FeedParserCoordinator = hass.data[DOMAIN][entry.entry_id]
    feed_url = entry.data[CONF_FEED_URL]
    name = entry.data[CONF_NAME]
    feed_id = hashlib.md5(feed_url.encode()).hexdigest()

    async_add_entities([
        FeedParserConnectivitySensor(
            coordinator=coordinator,
            feed_id=feed_id,
            name=name,
        ),
    ])


class FeedParserConnectivitySensor(
    CoordinatorEntity[FeedParserCoordinator], BinarySensorEntity
):
    """Binary sensor showing feed connectivity status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FeedParserCoordinator,
        feed_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._feed_id = feed_id
        self._feed_name = name
        self._attr_name = f"{name} Connected"
        self._attr_unique_id = f"{feed_id}_connected"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._feed_id)},
            name=f"RSS Feed: {self._feed_name}",
            manufacturer="Feedparser",
            model="RSS/Atom Feed",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        """Return True if the feed is connected."""
        return self.coordinator.is_connected

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Return additional state attributes."""
        attrs: dict[str, str | int | None] = {
            "fetch_count": self.coordinator.fetch_count,
            "error_count": self.coordinator.error_count,
        }
        if self.coordinator.last_error:
            attrs["last_error"] = self.coordinator.last_error
        return attrs

