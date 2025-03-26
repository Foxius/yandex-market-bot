from datetime import datetime
from typing import Dict, List
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import quote
from babel.support import Translations
from src.api.models import Order, Item, Address, Delivery
from src.api.client import YandexAPIClient
from src.config.settings import settings
from src.db.redis_db import RedisDB
from src.utils.logging import logger
from prometheus_client import Counter

# Prometheus metrics
NEW_ORDERS_TOTAL = Counter('new_orders_total', 'Total number of new orders processed')
OVERDUE_ORDERS_TOTAL = Counter('overdue_orders_total', 'Total number of overdue orders notified')
API_ERRORS_TOTAL = Counter('api_errors_total', 'Total number of API errors')

class OrderService:
    """Service for managing Yandex Market orders."""

    def __init__(self, client: YandexAPIClient, db: RedisDB):
        """Initialize the order service.

        Args:
            client (YandexAPIClient): Yandex API client instance.
            db (RedisDB): Redis database instance.
        """
        self.client = client
        self.db = db
        self.translations = Translations.load('locale', [settings.LOCALE])

    def _translate(self, message: str) -> str:
        """Translate a message using the current locale.

        Args:
            message (str): Message key to translate.

        Returns:
            str: Translated message.
        """
        return self.translations.gettext(message)

    async def check_new_orders(self, bot: Bot, chat_id: str) -> None:
        """Check for new orders and send notifications.

        Args:
            bot (Bot): Telegram bot instance.
            chat_id (str): Telegram chat ID.
        """
        try:
            orders = self.client.get_orders(settings.CAMPAIGN_ID, "PROCESSING", "STARTED")
            sent_orders = self.db.load_sent_orders()
            logger.info(f"Found {len(orders)} orders in PROCESSING/STARTED status")
            for order_data in orders:
                order_id = str(order_data["id"])
                if order_id not in sent_orders:
                    order = self._parse_order(order_data)
                    await self.notify_order(bot, chat_id, order)
                    self.db.save_sent_order(order_id)
                    NEW_ORDERS_TOTAL.inc()
        except Exception as e:
            logger.error(f"Error checking new orders: {str(e)}")
            API_ERRORS_TOTAL.inc()

    async def notify_order(self, bot: Bot, chat_id: str, order: Order) -> None:
        """Send a notification for a new order.

        Args:
            bot (Bot): Telegram bot instance.
            chat_id (str): Telegram chat ID.
            order (Order): Order object to notify about.
        """
        shop_skus = [item.shop_sku for item in order.items]
        market_sku_mapping = self.client.get_market_sku(settings.BUSINESS_ID, shop_skus)
        items_text = []
        for item in order.items:
            mapping = market_sku_mapping.get(item.shop_sku)
            url = (
                f"{settings.MARKET_URL}{mapping['marketModelId']}?sku={mapping['marketSku']}"
                if mapping else f"https://market.yandex.ru/search?text={quote(item.offer_name)}"
            )
            items_text.append(f"  • [{item.offer_name}]({url}) (x{item.count})")
        items_text = "\n".join(items_text)
        gift_notice = f"\n\n🎁 *{self._translate('no_gift')}*" if order.items_total < 300 else ""
        full_address = ", ".join(filter(None, [
            order.delivery.address.country, order.delivery.address.postcode,
            order.delivery.address.city, order.delivery.address.street,
            order.delivery.address.house, order.delivery.address.block
        ]))
        message = (
            f"📦 *{self._translate('new_order')} #{order.id}*\n\n"
            f"📋 *{self._translate('items')}*\n{items_text}\n\n"
            f"🏠 *{self._translate('delivery_address')}*\n  {full_address}\n"
            f"⏰ *{self._translate('shipment_deadline')}* {order.delivery.shipment_date}"
            f"{gift_notice}"
        )
        label_file = self.client.get_label(settings.CAMPAIGN_ID, order.id)
        pdf_input = BufferedInputFile(label_file, filename=f"label_{order.id}.pdf") if label_file else None
        if not pdf_input:
            message += f"\n\n⚠️ {self._translate('label_error')}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=self._translate("ready_to_ship"), callback_data=f"ready_{order.id}_{settings.CAMPAIGN_ID}")]
        ])
        if pdf_input:
            sent_message = await bot.send_document(
                chat_id, document=pdf_input, caption=message, parse_mode="Markdown",
                reply_markup=keyboard, disable_notification=False
            )
        else:
            sent_message = await bot.send_message(
                chat_id, message, parse_mode="Markdown", reply_markup=keyboard,
                disable_notification=False, disable_web_page_preview=True
            )
        await bot.pin_chat_message(chat_id, sent_message.message_id, disable_notification=False)
        logger.info(f"Notification for order #{order.id} sent and pinned")

    async def check_overdue_orders(self, bot: Bot, chat_id: str) -> None:
        """Check for overdue orders and send notifications.

        Args:
            bot (Bot): Telegram bot instance.
            chat_id (str): Telegram chat ID.
        """
        try:
            orders = self.client.get_orders(settings.CAMPAIGN_ID, "PROCESSING", "READY_TO_SHIP")
            overdue_notified = self.db.load_overdue_notified()
            logger.info(f"Found {len(orders)} orders in READY_TO_SHIP status")
            current_date = datetime.now()
            for order_data in orders:
                order = self._parse_order(order_data)
                try:
                    shipment_date = datetime.strptime(order.delivery.shipment_date, "%d-%m-%Y")
                    if (current_date - shipment_date).days >= 1 and order.id not in overdue_notified:
                        message = (
                            f"⚠️ *{self._translate('order_overdue')} #{order.id}*\n"
                            f"⏰ {self._translate('shipment_deadline')}: {order.delivery.shipment_date}\n"
                            f"{self._translate('status')}: PROCESSING/READY_TO_SHIP"
                        )
                        await bot.send_message(chat_id, message, parse_mode="Markdown", disable_notification=False)
                        logger.warning(f"Sent overdue notification for order #{order.id}")
                        self.db.save_overdue_notified(order.id)
                        OVERDUE_ORDERS_TOTAL.inc()
                except ValueError:
                    logger.error(f"Invalid shipment date format for order #{order.id}: {order.delivery.shipment_date}")
        except Exception as e:
            logger.error(f"Error checking overdue orders: {str(e)}")
            API_ERRORS_TOTAL.inc()

    def set_order_status_ready(self, order_id: str) -> Dict:
        """Set an order status to READY_TO_SHIP.

        Args:
            order_id (str): Order ID.

        Returns:
            Dict: API response or error details.
        """
        try:
            order_data = self.client.get_order_info(settings.CAMPAIGN_ID, order_id)
            if not order_data:
                return {"status": "ERROR", "errors": [{"code": "FETCH_ERROR", "message": "Failed to fetch order data"}]}
            if order_data.get("status") != "PROCESSING" or order_data.get("substatus") != "STARTED":
                return {
                    "status": "ERROR",
                    "errors": [{"code": "INVALID_STATUS", "message": "Cannot transition to READY_TO_SHIP"}]
                }
            items = [{"id": item["id"], "count": item["count"]} for item in order_data.get("items", [])]
            return self.client.set_order_status(settings.CAMPAIGN_ID, order_id, "PROCESSING", "READY_TO_SHIP", items)
        except Exception as e:
            logger.error(f"Error setting order status: {str(e)}")
            API_ERRORS_TOTAL.inc()
            return {"status": "ERROR", "errors": [{"code": "INTERNAL_ERROR", "message": str(e)}]}

    def _parse_order(self, order_data: Dict) -> Order:
        """Parse order data into an Order model.

        Args:
            order_data (Dict): Raw order data from API.

        Returns:
            Order: Parsed order object.
        """
        address = Address(**{k: order_data["delivery"].get("address", {}).get(k, "") for k in Address.__annotations__})
        shipment_date = order_data["delivery"].get("shipments", [{}])[0].get("shipmentDate", "Not specified")
        delivery = Delivery(address=address, shipment_date=shipment_date)
        items = [Item(shop_sku=item["shopSku"], offer_name=item["offerName"], count=item["count"], id=item.get("id")) 
                 for item in order_data["items"]]
        return Order(
            id=str(order_data["id"]), items=items, delivery=delivery, 
            items_total=order_data.get("itemsTotal", 0.0), 
            status=order_data.get("status", ""), substatus=order_data.get("substatus", "")
        )