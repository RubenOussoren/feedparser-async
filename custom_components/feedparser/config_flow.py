"""Config flow for Feedparser integration."""
from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
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

_LOGGER = logging.getLogger(__name__)


def validate_url(url: str) -> bool:
    """Validate feed URL."""
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)


def parse_list_input(value: str | list[str]) -> list[str]:
    """Parse comma-separated string or list into list of strings."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        if not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def parse_scan_interval(value: str | int | timedelta) -> timedelta:
    """Parse scan interval from string (hours), int (hours), or timedelta."""
    if isinstance(value, timedelta):
        return value
    if isinstance(value, int):
        return timedelta(hours=value)
    if isinstance(value, str):
        try:
            hours = float(value.strip())
            return timedelta(hours=hours)
        except ValueError:
            pass
    return DEFAULT_SCAN_INTERVAL


def format_scan_interval(value: timedelta) -> str:
    """Format timedelta as hours string for UI."""
    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600
    return str(hours)


class FeedParserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Feedparser."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> FeedParserOptionsFlowHandler:
        """Get the options flow for this handler."""
        return FeedParserOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            feed_url = user_input[CONF_FEED_URL]
            name = user_input[CONF_NAME]

            if not validate_url(feed_url):
                errors[CONF_FEED_URL] = "invalid_url"
            else:
                await self.async_set_unique_id(
                    hashlib.md5(feed_url.encode()).hexdigest()
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_FEED_URL: feed_url,
                        CONF_NAME: name,
                    },
                    options={
                        CONF_DATE_FORMAT: user_input.get(
                            CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT
                        ),
                        CONF_LOCAL_TIME: user_input.get(CONF_LOCAL_TIME, False),
                        CONF_SHOW_TOPN: user_input.get(CONF_SHOW_TOPN, DEFAULT_TOPN),
                        CONF_REMOVE_SUMMARY_IMG: user_input.get(
                            CONF_REMOVE_SUMMARY_IMG, False
                        ),
                        CONF_INCLUSIONS: parse_list_input(
                            user_input.get(CONF_INCLUSIONS, "")
                        ),
                        CONF_EXCLUSIONS: parse_list_input(
                            user_input.get(CONF_EXCLUSIONS, "")
                        ),
                        CONF_SCAN_INTERVAL: parse_scan_interval(
                            user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                        ),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_FEED_URL): str,
                vol.Optional(
                    CONF_DATE_FORMAT, default=DEFAULT_DATE_FORMAT
                ): str,
                vol.Optional(CONF_LOCAL_TIME, default=False): bool,
                vol.Optional(CONF_SHOW_TOPN, default=DEFAULT_TOPN): vol.Coerce(int),
                vol.Optional(CONF_REMOVE_SUMMARY_IMG, default=False): bool,
                vol.Optional(CONF_INCLUSIONS, default=""): str,
                vol.Optional(CONF_EXCLUSIONS, default=""): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=format_scan_interval(DEFAULT_SCAN_INTERVAL)
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_info: ConfigType) -> FlowResult:
        """Handle import from configuration.yaml."""
        feed_url = import_info[CONF_FEED_URL]
        unique_id = hashlib.md5(feed_url.encode()).hexdigest()

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=import_info[CONF_NAME],
            data={
                CONF_FEED_URL: feed_url,
                CONF_NAME: import_info[CONF_NAME],
            },
            options={
                CONF_DATE_FORMAT: import_info.get(
                    CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT
                ),
                CONF_LOCAL_TIME: import_info.get(CONF_LOCAL_TIME, False),
                CONF_SHOW_TOPN: import_info.get(CONF_SHOW_TOPN, DEFAULT_TOPN),
                CONF_REMOVE_SUMMARY_IMG: import_info.get(
                    CONF_REMOVE_SUMMARY_IMG, False
                ),
                CONF_INCLUSIONS: parse_list_input(
                    import_info.get(CONF_INCLUSIONS, [])
                ),
                CONF_EXCLUSIONS: parse_list_input(
                    import_info.get(CONF_EXCLUSIONS, [])
                ),
                CONF_SCAN_INTERVAL: parse_scan_interval(
                    import_info.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ),
            },
        )


class FeedParserOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Feedparser options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            processed_input = dict(user_input)
            processed_input[CONF_INCLUSIONS] = parse_list_input(
                user_input.get(CONF_INCLUSIONS, "")
            )
            processed_input[CONF_EXCLUSIONS] = parse_list_input(
                user_input.get(CONF_EXCLUSIONS, "")
            )
            processed_input[CONF_SCAN_INTERVAL] = parse_scan_interval(
                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )
            return self.async_create_entry(title="", data=processed_input)

        options = self.config_entry.options

        def format_list_for_ui(value: list[str] | str) -> str:
            """Format list as comma-separated string for UI."""
            if isinstance(value, list):
                return ", ".join(value)
            if isinstance(value, str):
                return value
            return ""

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DATE_FORMAT,
                    default=options.get(CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT),
                ): str,
                vol.Optional(
                    CONF_LOCAL_TIME,
                    default=options.get(CONF_LOCAL_TIME, False),
                ): bool,
                vol.Optional(
                    CONF_SHOW_TOPN,
                    default=options.get(CONF_SHOW_TOPN, DEFAULT_TOPN),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_REMOVE_SUMMARY_IMG,
                    default=options.get(CONF_REMOVE_SUMMARY_IMG, False),
                ): bool,
                vol.Optional(
                    CONF_INCLUSIONS,
                    default=format_list_for_ui(options.get(CONF_INCLUSIONS, [])),
                ): str,
                vol.Optional(
                    CONF_EXCLUSIONS,
                    default=format_list_for_ui(options.get(CONF_EXCLUSIONS, [])),
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=format_scan_interval(
                        options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

