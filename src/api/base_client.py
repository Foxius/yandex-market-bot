# src/api/base_client.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class MarketplaceClient(ABC):
    """Abstract base class for marketplace API clients."""

    @abstractmethod
    def get_orders(self, status: str, substatus: str) -> List[Dict]:
        """Fetch orders by status and substatus."""
        pass

    @abstractmethod
    def get_market_sku(self, shop_skus: List[str]) -> Dict[str, Dict[str, str]]:
        """Fetch market SKU and model ID for shop SKUs."""
        pass

    @abstractmethod
    def get_label(self, order_id: str) -> Optional[bytes]:
        """Fetch PDF label for an order."""
        pass

    @abstractmethod
    def get_pickup_point_address(self, order_id: str) -> str:
        """Fetch pickup point address for an order."""
        pass

    @abstractmethod
    def set_order_status(self, order_id: str, status: str, substatus: str, items: List[Dict]) -> Dict:
        """Update order status."""
        pass

    @abstractmethod
    def get_order_info(self, order_id: str) -> Dict:
        """Fetch detailed order information."""
        pass