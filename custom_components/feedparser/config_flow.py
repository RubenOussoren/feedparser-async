"""Config flow for Feedparser integration."""
from __future__ import annotations

import hashlib
import logging
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
                        CONF_INCLUSIONS: user_input.get(CONF_INCLUSIONS, []),
                        CONF_EXCLUSIONS: user_input.get(CONF_EXCLUSIONS, []),
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
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
                vol.Optional(CONF_INCLUSIONS, default=[]): vol.All(
                    cv.ensure_list, [str]
                ),
                vol.Optional(CONF_EXCLUSIONS, default=[]): vol.All(
                    cv.ensure_list, [str]
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): cv.time_period,
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
                CONF_INCLUSIONS: import_info.get(CONF_INCLUSIONS, []),
                CONF_EXCLUSIONS: import_info.get(CONF_EXCLUSIONS, []),
                CONF_SCAN_INTERVAL: import_info.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
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
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
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
                    default=options.get(CONF_INCLUSIONS, []),
                ): vol.All(cv.ensure_list, [str]),
                vol.Optional(
                    CONF_EXCLUSIONS,
                    default=options.get(CONF_EXCLUSIONS, []),
                ): vol.All(cv.ensure_list, [str]),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): cv.time_period,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

