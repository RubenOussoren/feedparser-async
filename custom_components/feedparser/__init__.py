"""Feedparser integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

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
    DEFAULT_TOPN,
    DOMAIN,
)
from .coordinator import FeedParserCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


def get_scan_interval_timedelta(options: dict[str, Any]) -> timedelta:
    """Get scan interval as timedelta from options."""
    scan_interval = options.get(CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds()))
    if isinstance(scan_interval, timedelta):
        return scan_interval
    if isinstance(scan_interval, int):
        return timedelta(seconds=scan_interval)
    return DEFAULT_SCAN_INTERVAL


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Feedparser component (YAML configuration)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Feedparser from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    feed_url = entry.data[CONF_FEED_URL]
    name = entry.data[CONF_NAME]
    options = entry.options

    coordinator = FeedParserCoordinator(
        hass=hass,
        feed_url=feed_url,
        name=name,
        update_interval=get_scan_interval_timedelta(options),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(coordinator.async_shutdown)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: FeedParserCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        new_data = {**entry.data}
        new_options = {**entry.options}

        if CONF_DATE_FORMAT not in new_options:
            new_options[CONF_DATE_FORMAT] = DEFAULT_DATE_FORMAT
        if CONF_LOCAL_TIME not in new_options:
            new_options[CONF_LOCAL_TIME] = False
        if CONF_SHOW_TOPN not in new_options:
            new_options[CONF_SHOW_TOPN] = DEFAULT_TOPN
        if CONF_REMOVE_SUMMARY_IMG not in new_options:
            new_options[CONF_REMOVE_SUMMARY_IMG] = False
        if CONF_INCLUSIONS not in new_options:
            new_options[CONF_INCLUSIONS] = []
        if CONF_EXCLUSIONS not in new_options:
            new_options[CONF_EXCLUSIONS] = []
        if CONF_SCAN_INTERVAL not in new_options:
            new_options[CONF_SCAN_INTERVAL] = int(DEFAULT_SCAN_INTERVAL.total_seconds())

        entry.version = 2
        hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)

    _LOGGER.info("Migration to version %s successful", entry.version)
    return True
