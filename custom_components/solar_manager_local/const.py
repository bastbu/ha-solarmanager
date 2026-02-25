from datetime import timedelta

DOMAIN = "solar_manager_local"
NAME = "Solar Manager Local"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_API_KEY_SECRET = "api_key_secret"
DEFAULT_API_KEY_SECRET = "solar_manager_api_key"

ENDPOINT_POINT = "/v2/point"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=7)
REQUEST_TIMEOUT_SECONDS = 10
