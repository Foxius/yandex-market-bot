# src/api/ozon_client.py
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.api.base_client import MarketplaceClient
from src.utils.logging import logger

class OzonAPIClient(MarketplaceClient):
    """Client for interacting with Ozon Seller API."""

    def __init__(self, api_key: str, client_id: str, base_url: str = "https://api-seller.ozon.ru"):
        self.api_key = api_key
        self.client_id = client_id
        self.base_url = base_url
        self.headers = {
            "Api-Key": api_key,
            "Client-Id": client_id,
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_orders(self, status: str, substatus: str = None) -> List[Dict]:
        since = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        to = datetime.today().strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "dir": "ASC",
            "filter": {
                "since": since,
                "to": to,
                "status": status
            },
            "limit": 100,
            "offset": 0,
            "with": {
                "analytics_data": True,
                "barcodes": True,
                "financial_data": True,
                "translit": True
            }
        }
        logger.debug(f"[ozon] Sending request to {self.base_url}/v3/posting/fbs/list with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v3/posting/fbs/list",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        logger.debug(f"[ozon] Response: {response.json()}")
        return response.json().get("result", {}).get("postings", [])

    def get_market_sku(self, shop_skus: List[str]) -> Dict[str, Dict[str, str]]:
        return {sku: {"marketSku": sku, "marketModelId": sku} for sku in shop_skus}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_label(self, order_id: str) -> Optional[bytes]:
        payload = {"posting_number": [order_id]}
        logger.debug(f"[ozon] Sending request to {self.base_url}/v2/posting/fbs/package-label with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v2/posting/fbs/package-label",
            headers=self.headers,
            json=payload
        )
        if response.status_code == 200:
            return response.content
        logger.error(f"[ozon] Failed to fetch label for order #{order_id}: HTTP {response.status_code} - {response.text}")
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_carriage_label(self, carriage_id: int) -> Optional[bytes]:
        payload = {"carriage_id": carriage_id}
        logger.debug(f"[ozon] Sending request to {self.base_url}/v2/posting/fbs/digital/act/get-pdf with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v2/posting/fbs/digital/act/get-pdf",
            headers=self.headers,
            json=payload
        )
        if response.status_code == 200:
            return response.content
        logger.error(f"[ozon] Failed to fetch carriage label for carriage #{carriage_id}: HTTP {response.status_code} - {response.text}")
        return None

    def get_pickup_point_address(self, order_id: str) -> str:
        payload = {"posting_number": order_id}
        logger.debug(f"[ozon] Sending request to {self.base_url}/v2/posting/fbs/get with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v2/posting/fbs/get",
            headers=self.headers,
            json=payload
        )
        if response.status_code == 200:
            data = response.json().get("result", {})
            delivery = data.get("delivery", {})
            address = delivery.get("address", {})
            return f"{address.get('city', '')}, {address.get('address_tail', '')}"
        logger.warning(f"[ozon] Pickup point address for order #{order_id} not found: HTTP {response.status_code} - {response.text}")
        return "Pickup point address not found"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def set_order_status(self, order_id: str, status: str, substatus: str, items: List[Dict]) -> Dict:
        payload = {
            "posting_number": order_id,
            "status": status
        }
        logger.debug(f"[ozon] Sending request to {self.base_url}/v2/posting/fbs/status with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v2/posting/fbs/status",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_order_info(self, order_id: str) -> Dict:
        payload = {"posting_number": order_id}
        logger.debug(f"[ozon] Sending request to {self.base_url}/v2/posting/fbs/get with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v2/posting/fbs/get",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json().get("result", {})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def create_carriage(self, delivery_method_id: int, departure_date: str) -> int:
        payload = {
            "delivery_method_id": delivery_method_id,
            "departure_date": departure_date
        }
        logger.debug(f"[ozon] Creating carriage with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v1/carriage/create",
            headers=self.headers,
            json=payload
        )
        if response.status_code != 200:
            logger.error(f"[ozon] Failed to create carriage: HTTP {response.status_code} - {response.text}")
            response.raise_for_status()
        return response.json()["carriage_id"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def approve_carriage(self, carriage_id: int, containers_count: int = None) -> Dict:
        payload = {"carriage_id": carriage_id}
        if containers_count is not None:
            payload["containers_count"] = containers_count
        logger.debug(f"[ozon] Approving carriage with payload: {payload}")
        response = requests.post(
            f"{self.base_url}/v1/carriage/approve",
            headers=self.headers,
            json=payload
        )
        if response.status_code != 200:
            logger.error(f"[ozon] Failed to approve carriage #{carriage_id}: HTTP {response.status_code} - {response.text}")
            response.raise_for_status()
        return response.json()