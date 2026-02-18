"""Data coordinator for Ferrellgas."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FerrellgasAccountData,
    FerrellgasApiClient,
    FerrellgasApiError,
    FerrellgasAuthenticationError,
    FerrellgasConnectionError,
)
from .const import (
    CONF_ACCOUNT_ID,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class FerrellgasDataUpdateCoordinator(DataUpdateCoordinator[FerrellgasAccountData]):
    """Coordinate Ferrellgas data updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: FerrellgasApiClient,
    ) -> None:
        """Initialize coordinator."""
        self.api_client = api_client

        scan_interval_minutes = config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES,
            DEFAULT_SCAN_INTERVAL_MINUTES,
        )
        update_interval = timedelta(minutes=int(scan_interval_minutes))
        if update_interval.total_seconds() <= 0:
            update_interval = DEFAULT_SCAN_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> FerrellgasAccountData:
        """Fetch data from Ferrellgas API."""
        username = self.config_entry.data[CONF_USERNAME]
        password = self.config_entry.data[CONF_PASSWORD]
        account_id = self.config_entry.data[CONF_ACCOUNT_ID]

        try:
            return await self.api_client.async_get_account_summary(
                username=username,
                password=password,
                account_id=account_id,
            )
        except FerrellgasAuthenticationError as err:
            raise ConfigEntryAuthFailed("Authentication with Ferrellgas failed") from err
        except FerrellgasConnectionError as err:
            raise UpdateFailed(f"Error connecting to Ferrellgas API: {err}") from err
        except FerrellgasApiError as err:
            raise UpdateFailed(f"Error fetching data from Ferrellgas API: {err}") from err
