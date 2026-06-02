import time
import hmac
import hashlib
import urllib.parse
import requests
from bot.logging_config import logger

class BinanceClientError(Exception):
    """Base exception for Binance Client errors."""
    pass

class BinanceAPIError(BinanceClientError):
    """Exception raised for API errors returned by Binance (e.g., code, msg)."""
    def __init__(self, code: int, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"Binance API Error {code}: {message} (HTTP Status {status_code})")

class BinanceNetworkError(BinanceClientError):
    """Exception raised for network issues (connection refused, timeouts)."""
    pass

class BinanceFuturesClient:
    """
    Binance Futures REST API client for USDT-M Futures.
    Handles signed/unsigned requests, server time syncing, and exception wrapping.
    """
    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = "https://testnet.binancefuture.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded"
            })
        
        # Keep track of local-to-server time offset to handle timestamp sync issues
        self.time_offset = 0
        self.sync_time()

    def sync_time(self):
        """
        Synchronizes local time offset with Binance server time.
        Helps prevent 'Timestamp for this request is outside of the recvWindow' (-1021).
        """
        try:
            url = f"{self.base_url}/fapi/v1/time"
            logger.debug(f"Syncing time with server: {url}")
            before = int(time.time() * 1000)
            response = self.session.get(url, timeout=10)
            after = int(time.time() * 1000)
            
            if response.status_code == 200:
                server_time = response.json()["serverTime"]
                # Calculate latency-adjusted offset
                rtt = (after - before) // 2
                self.time_offset = server_time - before - rtt
                logger.debug(f"Time synchronized. Offset: {self.time_offset}ms, RTT: {rtt}ms")
            else:
                logger.warning(f"Failed to sync time. Status code: {response.status_code}. Using local time.")
        except Exception as e:
            logger.warning(f"Error syncing server time: {e}. Using local system time.")
            self.time_offset = 0

    def _get_timestamp(self) -> int:
        """
        Returns latency-adjusted millisecond timestamp.
        """
        return int(time.time() * 1000) + self.time_offset

    def _sign(self, query_string: str) -> str:
        """
        Generates HMAC-SHA256 signature using the API secret.
        """
        if not self.api_secret:
            raise BinanceClientError("API Secret is required for signing requests but was not provided.")
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def request(self, method: str, path: str, params: dict = None, signed: bool = False) -> dict:
        """
        Sends an HTTP request to the Binance API.
        Logs details, signs if required, and parses the response.
        """
        url = f"{self.base_url}{path}"
        params = dict(params or {})
        
        # Prepare parameters and signature if request needs to be signed
        if signed:
            if not self.api_key:
                raise BinanceClientError("API Key is required for signed endpoints.")
            params["timestamp"] = self._get_timestamp()
            query_string = urllib.parse.urlencode(params)
            signature = self._sign(query_string)
            params["signature"] = signature
        
        logger.debug(f"Request: {method} {url} | Params: { {k: v for k, v in params.items() if 'signature' not in k} }")
        
        try:
            # We pass all params as URL query params because Binance Futures REST API
            # supports and prefers query-string parameters for both GET and POST requests.
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params if method.upper() in ["GET", "DELETE", "POST"] else None,
                data=params if method.upper() not in ["GET", "DELETE", "POST"] else None,
                timeout=15
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error executing request: {e}")
            raise BinanceNetworkError(f"Network error: {e}")
            
        logger.debug(f"Response Status: {response.status_code} | Body: {response.text}")
        
        # Parse response
        try:
            data = response.json()
        except ValueError:
            logger.error(f"Invalid JSON returned: {response.text}")
            raise BinanceClientError(f"Failed to parse JSON response. Status: {response.status_code}, Body: {response.text}")
            
        if response.status_code != 200:
            code = data.get("code", -1)
            msg = data.get("msg", "Unknown error")
            logger.error(f"API Error: Code={code}, Msg={msg}, Status={response.status_code}")
            raise BinanceAPIError(code=code, message=msg, status_code=response.status_code)
            
        return data

    # Account info endpoints (useful for the Streamlit dashboard)
    def get_account_info(self) -> dict:
        """
        Gets current account balance and position details.
        """
        return self.request("GET", "/fapi/v2/account", signed=True)

    def get_position_risk(self) -> list:
        """
        Gets details for active positions.
        """
        return self.request("GET", "/fapi/v2/positionRisk", signed=True)

    def get_open_orders(self, symbol: str = None) -> list:
        """
        Gets current open orders.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self.request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """
        Cancels an active open order.
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        return self.request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_ticker_price(self, symbol: str) -> dict:
        """
        Gets current price for a symbol (unsigned).
        """
        return self.request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol}, signed=False)
