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
from homeassistant.helpers import selector
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_DATE_FORMAT,
    CONF_EXCLUSIONS,
    CONF_FEED_URL,
    CONF_INCLUSIONS,
    CONF_LOCAL_TIME,
    CONF_REMOVE_SUMMARY_IMG,
    CONF_SCAN_INTERVAL_UNIT,
    CONF_SCAN_INTERVAL_VALUE,
    CONF_SHOW_TOPN,
    DATE_FORMAT_OPTIONS,
    DEFAULT_DATE_FORMAT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_UNIT,
    DEFAULT_SCAN_INTERVAL_VALUE,
    DEFAULT_TOPN,
    DOMAIN,
    SCAN_INTERVAL_UNITS,
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


def parse_scan_interval(value: str | int | timedelta | dict[str, Any]) -> timedelta:
    """Parse scan interval from various formats including new unit-based format."""
    if isinstance(value, timedelta):
        return value
    if isinstance(value, dict):
        interval_value = value.get(CONF_SCAN_INTERVAL_VALUE, DEFAULT_SCAN_INTERVAL_VALUE)
        interval_unit = value.get(CONF_SCAN_INTERVAL_UNIT, DEFAULT_SCAN_INTERVAL_UNIT)
        try:
            value_float = float(interval_value)
            unit_seconds = SCAN_INTERVAL_UNITS.get(interval_unit, 3600)
            return timedelta(seconds=value_float * unit_seconds)
        except (ValueError, TypeError):
            return DEFAULT_SCAN_INTERVAL
    if isinstance(value, int):
        return timedelta(hours=value)
    if isinstance(value, str):
        try:
            hours = float(value.strip())
            return timedelta(hours=hours)
        except ValueError:
            pass
    return DEFAULT_SCAN_INTERVAL


def format_scan_interval(value: timedelta) -> dict[str, Any]:
    """Format timedelta as value and unit dict for UI."""
    total_seconds = int(value.total_seconds())
    
    if total_seconds % 86400 == 0:
        return {
            CONF_SCAN_INTERVAL_VALUE: total_seconds // 86400,
            CONF_SCAN_INTERVAL_UNIT: "days",
        }
    elif total_seconds % 3600 == 0:
        return {
            CONF_SCAN_INTERVAL_VALUE: total_seconds // 3600,
            CONF_SCAN_INTERVAL_UNIT: "hours",
        }
    else:
        return {
            CONF_SCAN_INTERVAL_VALUE: total_seconds // 60,
            CONF_SCAN_INTERVAL_UNIT: "minutes",
        }


def get_date_format_selector(current_format: str | None = None):
    """Get selector for date format with human-readable options."""
    options = [
        selector.SelectOptionDict(
            value=fmt,
            label=f"{label} ({fmt})",
        )
        for fmt, label in DATE_FORMAT_OPTIONS.items()
    ]
    
    if current_format and current_format not in DATE_FORMAT_OPTIONS:
        options.append(
            selector.SelectOptionDict(
                value=current_format,
                label=f"Custom: {current_format}",
            )
        )
    
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


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
                        CONF_DATE_FORMAT: DEFAULT_DATE_FORMAT,
                        CONF_LOCAL_TIME: False,
                        CONF_SHOW_TOPN: DEFAULT_TOPN,
                        CONF_REMOVE_SUMMARY_IMG: False,
                        CONF_INCLUSIONS: [],
                        CONF_EXCLUSIONS: [],
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_FEED_URL): str,
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
            
            show_topn = user_input.get(CONF_SHOW_TOPN, DEFAULT_TOPN)
            if show_topn == 0 or show_topn is None:
                show_topn = 9999
            processed_input[CONF_SHOW_TOPN] = show_topn
            
            scan_interval_dict = {
                CONF_SCAN_INTERVAL_VALUE: user_input.get(
                    CONF_SCAN_INTERVAL_VALUE, DEFAULT_SCAN_INTERVAL_VALUE
                ),
                CONF_SCAN_INTERVAL_UNIT: user_input.get(
                    CONF_SCAN_INTERVAL_UNIT, DEFAULT_SCAN_INTERVAL_UNIT
                ),
            }
            processed_input[CONF_SCAN_INTERVAL] = parse_scan_interval(scan_interval_dict)
            
            processed_input.pop(CONF_SCAN_INTERVAL_VALUE, None)
            processed_input.pop(CONF_SCAN_INTERVAL_UNIT, None)
            
            return self.async_create_entry(title="", data=processed_input)

        options = self.config_entry.options

        def format_list_for_ui(value: list[str] | str) -> str:
            """Format list as comma-separated string for UI."""
            if isinstance(value, list):
                return ", ".join(value)
            if isinstance(value, str):
                return value
            return ""

        current_date_format = options.get(CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT)

        current_scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if isinstance(current_scan_interval, str):
            current_scan_interval = parse_scan_interval(current_scan_interval)
        elif not isinstance(current_scan_interval, timedelta):
            current_scan_interval = DEFAULT_SCAN_INTERVAL
        
        scan_interval_formatted = format_scan_interval(current_scan_interval)
        
        current_show_topn = options.get(CONF_SHOW_TOPN, DEFAULT_TOPN)
        if current_show_topn == 9999:
            display_show_topn = 0
        else:
            display_show_topn = current_show_topn

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DATE_FORMAT,
                    default=current_date_format,
                ): get_date_format_selector(current_date_format),
                vol.Optional(
                    CONF_LOCAL_TIME,
                    default=options.get(CONF_LOCAL_TIME, False),
                ): bool,
                vol.Optional(
                    CONF_SHOW_TOPN,
                    default=display_show_topn,
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
                    CONF_SCAN_INTERVAL_VALUE,
                    default=scan_interval_formatted.get(
                        CONF_SCAN_INTERVAL_VALUE, DEFAULT_SCAN_INTERVAL_VALUE
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_SCAN_INTERVAL_UNIT,
                    default=scan_interval_formatted.get(
                        CONF_SCAN_INTERVAL_UNIT, DEFAULT_SCAN_INTERVAL_UNIT
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="minutes", label="Minutes"),
                            selector.SelectOptionDict(value="hours", label="Hours"),
                            selector.SelectOptionDict(value="days", label="Days"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

