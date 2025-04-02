# src/api/yandex_client.py
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.api.base_client import MarketplaceClient
from src.utils.logging import logger

class YandexAPIClient(MarketplaceClient):
    """Client for interacting with Yandex Market API."""

    def __init__(self, api_token: str, base_url: str, campaign_id: str, business_id: str):
        self.api_token = api_token
        self.base_url = base_url
        self.campaign_id = campaign_id
        self.business_id = business_id
        self.headers = {
            "Api-Key": api_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_orders(self, status: str, substatus: str) -> List[Dict]:
        response = requests.get(
            f"{self.base_url}/campaigns/{self.campaign_id}/orders?status={status}&substatus={substatus}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("orders", [])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_market_sku(self, shop_skus: List[str]) -> Dict[str, Dict[str, str]]:
        payload = {"offerIds": shop_skus}
        response = requests.post(
            f"{self.base_url}/businesses/{self.business_id}/offer-mappings",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        mappings = response.json().get("result", {}).get("offerMappings", [])
        sku_mapping = {}
        for mapping in mappings:
            shop_sku = mapping["offer"]["offerId"]
            market_sku = mapping.get("mapping", {}).get("marketSku")
            market_model_id = mapping.get("mapping", {}).get("marketModelId")
            if market_sku and market_model_id:
                sku_mapping[shop_sku] = {"marketSku": str(market_sku), "marketModelId": str(market_model_id)}
        return sku_mapping

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_label(self, order_id: str) -> Optional[bytes]:
        response = requests.get(
            f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}/delivery/labels",
            headers={"Api-Key": self.api_token},
            params={"format": "A9"}
        )
        if response.status_code == 200:
            return response.content
        logger.error(f"Failed to fetch label for order #{order_id}: {response.status_code}")
        return None

    def get_pickup_point_address(self, order_id: str) -> str:
        today=datetime.today() - timedelta(days=1)
        tommorow = datetime.today() + timedelta(days=1)
        payload = {"dateFrom": today.strftime("%Y-%m-%d"),
                   "dateTo": tommorow.strftime("%Y-%m-%d")}
        response = requests.put(
            f"{self.base_url}/campaigns/{self.campaign_id}/first-mile/shipments",
            headers=self.headers,
            json=payload
        )
        if response.status_code == 200:
            shipments = response.json()["result"].get("shipments", [])
            if shipments:
                for shipment in shipments:
                    if int(order_id) in shipment["orderIds"]:
                        return str(shipment["warehouseTo"]["address"])
        logger.warning(f"Pickup point address for order #{order_id} not found")
        return "Pickup point address not found"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def set_order_status(self, order_id: str, status: str, substatus: str, items: List[Dict]) -> Dict:
        payload = {"order": {"status": status, "substatus": substatus, "items": items}}
        response = requests.put(
            f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}/status",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_order_info(self, order_id: str) -> Dict:
        response = requests.get(
            f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("order", {})