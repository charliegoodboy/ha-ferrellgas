"""API client for Ferrellgas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import logging
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util

from .const import (
    API_ACCOUNT_SUMMARY_ENDPOINT,
    API_BFF_BASE_URL,
    API_LOGIN_ENDPOINT,
    API_USER_ME_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class FerrellgasApiError(Exception):
    """Base exception for API failures."""


class FerrellgasAuthenticationError(FerrellgasApiError):
    """Raised when authentication fails."""


class FerrellgasConnectionError(FerrellgasApiError):
    """Raised when network access to the API fails."""


@dataclass(slots=True)
class FerrellgasTankData:
    """Parsed tank data from account summary."""

    installed_product_id: str
    site_id: str
    site_name: str
    product_description: str
    product_id: str | None
    full_capacity: float | None
    fill_capacity: float | None
    est_curr_pct: float | None
    estimated_percentage_date: datetime | None


@dataclass(slots=True)
class FerrellgasAccountData:
    """Parsed account summary data."""

    account_id: str
    account_name: str
    balance: float | None
    tanks: list[FerrellgasTankData]


class FerrellgasApiClient:
    """Ferrellgas REST API client."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize API client."""
        self._session = session

    async def async_get_accounts(self, username: str, password: str) -> list[str]:
        """Authenticate and return available account IDs for the user."""
        access_token = await self._async_login(username, password)
        user_me = await self._async_get(
            f"{API_BFF_BASE_URL}{API_USER_ME_ENDPOINT}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        accounts = user_me.get("Accounts", [])
        if not isinstance(accounts, list):
            raise FerrellgasApiError("Unexpected response type for Accounts")
        return [str(account) for account in accounts]

    async def async_get_account_summary(
        self,
        username: str,
        password: str,
        account_id: str,
    ) -> FerrellgasAccountData:
        """Authenticate and fetch account summary for an account ID."""
        access_token = await self._async_login(username, password)
        payload = await self._async_get(
            f"{API_BFF_BASE_URL}{API_ACCOUNT_SUMMARY_ENDPOINT.format(account_id=account_id)}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return self._parse_account_summary(account_id, payload)

    async def _async_login(self, username: str, password: str) -> str:
        """Authenticate and return access token."""
        payload = {
            "username": username,
            "password": password,
            "changePwd": False,
            "newPassword": "",
            "ReturnUrl": "",
        }

        response = await self._async_post(
            f"{API_BFF_BASE_URL}{API_LOGIN_ENDPOINT}",
            json_payload=payload,
        )

        if not response.get("success"):
            error_msg = response.get("error") or "Login failed"
            raise FerrellgasAuthenticationError(str(error_msg))

        access_token = response.get("accessToken")
        if not isinstance(access_token, str) or not access_token:
            raise FerrellgasAuthenticationError("Login succeeded but access token missing")

        return access_token

    async def _async_get(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        """Issue GET request and parse JSON response."""
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                return await self._async_handle_response(response)
        except aiohttp.ClientError as err:
            raise FerrellgasConnectionError(f"GET request failed: {err}") from err

    async def _async_post(self, url: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        """Issue POST request and parse JSON response."""
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            async with self._session.post(url, json=json_payload, timeout=timeout) as response:
                return await self._async_handle_response(response)
        except aiohttp.ClientError as err:
            raise FerrellgasConnectionError(f"POST request failed: {err}") from err

    async def _async_handle_response(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        """Validate HTTP response and parse JSON body."""
        if response.status in (401, 403):
            raise FerrellgasAuthenticationError(f"Authentication error: HTTP {response.status}")

        if response.status >= 400:
            body = await response.text()
            raise FerrellgasApiError(f"API request failed: HTTP {response.status} - {body}")

        try:
            data = await response.json(content_type=None)
        except aiohttp.ContentTypeError as err:
            raise FerrellgasApiError("API returned non-JSON response") from err

        if not isinstance(data, dict):
            raise FerrellgasApiError("API returned unexpected payload type")

        return data

    def _parse_account_summary(self, account_id: str, payload: dict[str, Any]) -> FerrellgasAccountData:
        """Parse account summary payload into typed account data."""
        financial_summary = payload.get("FinancialSummary")
        balance: float | None = None
        if isinstance(financial_summary, dict):
            raw_balance = financial_summary.get("Balance")
            if isinstance(raw_balance, (int, float)):
                balance = float(raw_balance)

        account_name = str(payload.get("Name", account_id))

        tanks: list[FerrellgasTankData] = []
        site_summary = payload.get("SiteSummary", [])
        if not isinstance(site_summary, list):
            _LOGGER.debug("SiteSummary had unexpected type: %s", type(site_summary))
            site_summary = []

        for site_index, site in enumerate(site_summary):
            if not isinstance(site, dict):
                continue

            site_id = str(site.get("SiteId") or f"site_{site_index}")
            site_name = str(site.get("SiteName") or site.get("Address1") or site_id)

            ip_summary = site.get("IPSummary", [])
            if not isinstance(ip_summary, list):
                continue

            for tank_index, tank in enumerate(ip_summary):
                if not isinstance(tank, dict):
                    continue

                installed_product_id = tank.get("InstalledProductId")
                if not isinstance(installed_product_id, str) or not installed_product_id:
                    installed_product_id = f"{site_id}_{tank_index}"

                product_description = str(tank.get("ProductDescription") or "Ferrellgas Tank")
                product_id = tank.get("ProductId")
                if product_id is not None and not isinstance(product_id, str):
                    product_id = str(product_id)

                full_capacity = self._to_float(tank.get("FullCapacity"))
                fill_capacity = self._to_float(tank.get("FillCapacity"))
                est_curr_pct = self._to_float(tank.get("EstCurrPct"))

                estimated_percentage_date = self._parse_datetime(tank.get("EstimatedPercentageDate"))

                tanks.append(
                    FerrellgasTankData(
                        installed_product_id=installed_product_id,
                        site_id=site_id,
                        site_name=site_name,
                        product_description=product_description,
                        product_id=product_id,
                        full_capacity=full_capacity,
                        fill_capacity=fill_capacity,
                        est_curr_pct=est_curr_pct,
                        estimated_percentage_date=estimated_percentage_date,
                    )
                )

        return FerrellgasAccountData(
            account_id=account_id,
            account_name=account_name,
            balance=balance,
            tanks=tanks,
        )

    @staticmethod
    def _to_float(value: Any) -> float | None:
        """Convert API numeric fields to float safely."""
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse date/datetime values from API."""
        if not isinstance(value, str) or not value:
            return None

        parsed = dt_util.parse_datetime(value)
        if parsed is not None:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed

        try:
            parsed_date = date.fromisoformat(value)
            return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
        except ValueError:
            _LOGGER.debug("Unable to parse timestamp from Ferrellgas payload: %s", value)
            return None
