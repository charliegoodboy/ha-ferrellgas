"""Constants for the Ferrellgas integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ferrellgas"

CONF_ACCOUNT_ID = "account_id"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_LOW_PROPANE_THRESHOLD = "low_propane_threshold"

DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_SCAN_INTERVAL_MINUTES = 60
DEFAULT_LOW_PROPANE_THRESHOLD = 20

PLATFORMS = ["sensor", "binary_sensor"]

API_BFF_BASE_URL = "https://bff.myferrellgas.com"
API_LOGIN_ENDPOINT = "/api/Auth/Login/"
API_USER_ME_ENDPOINT = "/api/User/me"
API_ACCOUNT_SUMMARY_ENDPOINT = "/api/AccountSummary/{account_id}"
API_ORDERS_BY_IP_ENDPOINT = "/api/Order/IP/{installed_product_id}"
API_ORDER_DETAIL_ENDPOINT = "/api/Order/{order_id}"

REQUEST_TIMEOUT_SECONDS = 30
