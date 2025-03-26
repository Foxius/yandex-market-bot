from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Item:
    """Модель товара в заказе."""
    shop_sku: str
    offer_name: str
    count: int
    id: Optional[str] = None

@dataclass
class Address:
    """Модель адреса доставки."""
    country: str = ""
    postcode: str = ""
    city: str = ""
    street: str = ""
    house: str = ""
    block: str = ""

@dataclass
class Delivery:
    """Модель данных доставки."""
    address: Address
    shipment_date: str

@dataclass
class Order:
    """Модель заказа."""
    id: str
    items: List[Item]
    delivery: Delivery
    items_total: float
    status: str = ""
    substatus: str = ""