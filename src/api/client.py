import requests
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from src.utils.logging import logger

class YandexAPIClient:
    """Client for interacting with Yandex Market API."""

    def __init__(self, api_token: str, base_url: str):
        """Initialize the API client.

        Args:
            api_token (str): Yandex API token.
            base_url (str): Base URL of the Yandex API.
        """
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            "Api-Key": api_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_orders(self, campaign_id: str, status: str, substatus: str) -> List[Dict]:
        """Fetch orders by status and substatus with retry logic.

        Args:
            campaign_id (str): Campaign ID.
            status (str): Order status.
            substatus (str): Order substatus.

        Returns:
            List[Dict]: List of order dictionaries.

        Raises:
            requests.RequestException: If the request fails after retries.
        """
        response = requests.get(
            f"{self.base_url}/campaigns/{campaign_id}/orders?status={status}&substatus={substatus}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("orders", [])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_market_sku(self, business_id: str, shop_skus: List[str]) -> Dict[str, Dict[str, str]]:
        """Fetch market SKU and model ID for shop SKUs with retry logic.

        Args:
            business_id (str): Business ID.
            shop_skus (List[str]): List of shop SKUs.

        Returns:
            Dict[str, Dict[str, str]]: Mapping of shop SKU to market SKU and model ID.
        """
        payload = {"offerIds": shop_skus}
        response = requests.post(
            f"{self.base_url}/businesses/{business_id}/offer-mappings",
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
    def get_label(self, campaign_id: str, order_id: str) -> Optional[bytes]:
        """Fetch PDF label for an order with retry logic.

        Args:
            campaign_id (str): Campaign ID.
            order_id (str): Order ID.

        Returns:
            Optional[bytes]: PDF content or None if failed.
        """
        response = requests.get(
            f"{self.base_url}/campaigns/{campaign_id}/orders/{order_id}/delivery/labels",
            headers={"Api-Key": self.api_token},
            params={"format": "A9"}
        )
        if response.status_code == 200:
            return response.content
        logger.error(f"Failed to fetch label for order #{order_id}: {response.status_code}")
        return None

    def get_pickup_point_address(self, campaign_id: str, order_id: str) -> str:
        """Fetch pickup point address for an order.

        Args:
            campaign_id (str): Campaign ID.
            order_id (str): Order ID.

        Returns:
            str: Pickup point address or fallback message.
        """
        response = requests.get(
            f"{self.base_url}/campaigns/{campaign_id}/first-mile/shipments",
            headers=self.headers
        )
        if response.status_code == 200:
            shipments = response.json().get("shipments", [])
            if shipments:
                shipment = shipments[0]
                if "delivery" in shipment and "address" in shipment["delivery"]:
                    addr = shipment["delivery"]["address"]
                    return f"{addr.get('city', '')}, {addr.get('street', '')}, {addr.get('house', '')}"
                shipment_id = shipment["id"]
                shipment_response = requests.get(
                    f"{self.base_url}/campaigns/{campaign_id}/first-mile/shipments/{shipment_id}",
                    headers=self.headers
                )
                if shipment_response.status_code == 200:
                    shipment_data = shipment_response.json()
                    if "delivery" in shipment_data and "address" in shipment_data["delivery"]:
                        addr = shipment_data["delivery"]["address"]
                        return f"{addr.get('city', '')}, {addr.get('street', '')}, {addr.get('house', '')}"
        logger.warning(f"Pickup point address for order #{order_id} not found")
        return "Pickup point address not found"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def set_order_status(self, campaign_id: str, order_id: str, status: str, substatus: str, items: List[Dict]) -> Dict:
        """Update order status with retry logic.

        Args:
            campaign_id (str): Campaign ID.
            order_id (str): Order ID.
            status (str): New status.
            substatus (str): New substatus.
            items (List[Dict]): List of items in the order.

        Returns:
            Dict: API response.
        """
        payload = {"order": {"status": status, "substatus": substatus, "items": items}}
        response = requests.put(
            f"{self.base_url}/campaigns/{campaign_id}/orders/{order_id}/status",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_order_info(self, campaign_id: str, order_id: str) -> Dict:
        """Fetch order information with retry logic.

        Args:
            campaign_id (str): Campaign ID.
            order_id (str): Order ID.

        Returns:
            Dict: Order data or empty dict if failed.
        """
        response = requests.get(
            f"{self.base_url}/campaigns/{campaign_id}/orders/{order_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("order", {})