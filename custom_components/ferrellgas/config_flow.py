"""Config flow for the Ferrellgas integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    FerrellgasApiClient,
    FerrellgasApiError,
    FerrellgasAuthenticationError,
    FerrellgasConnectionError,
)
from .const import (
    CONF_ACCOUNT_ID,
    CONF_LOW_PROPANE_THRESHOLD,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_LOW_PROPANE_THRESHOLD,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)


class FerrellgasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ferrellgas."""

    VERSION = 1

    _user_input: dict[str, Any] | None
    _accounts: list[str]

    def __init__(self) -> None:
        """Initialize flow."""
        self._user_input = None
        self._accounts = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input = user_input
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                accounts = await _async_validate_and_fetch_accounts(
                    self.hass,
                    username,
                    password,
                )
            except FerrellgasAuthenticationError:
                errors["base"] = "invalid_auth"
            except FerrellgasConnectionError:
                errors["base"] = "cannot_connect"
            except FerrellgasApiError:
                errors["base"] = "unknown"
            else:
                if not accounts:
                    errors["base"] = "no_accounts"
                elif len(accounts) == 1:
                    return await self._async_create_entry(user_input, accounts[0])
                else:
                    self._accounts = accounts
                    return await self.async_step_account()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_account(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle multi-account selection step."""
        if self._user_input is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}

        if user_input is not None:
            account_id = user_input[CONF_ACCOUNT_ID]
            if account_id not in self._accounts:
                errors["base"] = "invalid_account"
            else:
                return await self._async_create_entry(self._user_input, account_id)

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT_ID): vol.In(self._accounts),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth credential entry."""
        errors: dict[str, str] = {}

        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                await _async_validate_and_fetch_accounts(self.hass, username, password)
            except FerrellgasAuthenticationError:
                errors["base"] = "invalid_auth"
            except FerrellgasConnectionError:
                errors["base"] = "cannot_connect"
            except FerrellgasApiError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=reauth_entry.data.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _async_create_entry(self, credentials: dict[str, Any], account_id: str) -> FlowResult:
        """Create config entry for selected account."""
        await self.async_set_unique_id(account_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Ferrellgas {account_id}",
            data={
                CONF_USERNAME: credentials[CONF_USERNAME],
                CONF_PASSWORD: credentials[CONF_PASSWORD],
                CONF_ACCOUNT_ID: account_id,
            },
            options={
                CONF_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES,
                CONF_LOW_PROPANE_THRESHOLD: DEFAULT_LOW_PROPANE_THRESHOLD,
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> FerrellgasOptionsFlow:
        """Return options flow handler."""
        return FerrellgasOptionsFlow(config_entry)


class FerrellgasOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Ferrellgas."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES,
            DEFAULT_SCAN_INTERVAL_MINUTES,
        )
        current_low_threshold = self._config_entry.options.get(
            CONF_LOW_PROPANE_THRESHOLD,
            DEFAULT_LOW_PROPANE_THRESHOLD,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL_MINUTES,
                        default=current_scan_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                    vol.Required(
                        CONF_LOW_PROPANE_THRESHOLD,
                        default=current_low_threshold,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                }
            ),
        )


async def _async_validate_and_fetch_accounts(
    hass: HomeAssistant,
    username: str,
    password: str,
) -> list[str]:
    """Validate credentials and return account IDs."""
    session = async_get_clientsession(hass)
    client = FerrellgasApiClient(session)
    return await client.async_get_accounts(username, password)
