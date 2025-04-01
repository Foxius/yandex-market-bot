# src/api/services.py
from datetime import datetime
from typing import Dict, List
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import quote
import requests
from babel.support import Translations
from src.api.models import Order
from src.api.base_client import MarketplaceClient
from src.api.parsers import get_parser
from src.config.settings import settings
from src.db.redis_db import RedisDB
from src.utils.logging import logger
from prometheus_client import Counter

# Prometheus metrics
NEW_ORDERS_TOTAL = Counter('new_orders_total', 'Total number of new orders processed')
OVERDUE_ORDERS_TOTAL = Counter('overdue_orders_total', 'Total number of overdue orders notified')
API_ERRORS_TOTAL = Counter('api_errors_total', 'Total number of API errors')

class OrderService:
    """Service for managing marketplace orders."""

    def __init__(self, clients: Dict[str, MarketplaceClient], db: RedisDB):
        """Initialize the order service."""
        self.clients = clients
        self.db = db
        self.translations = Translations.load('locale', [settings.LOCALE])

    def get_parser(self, platform: str):
        """Get the appropriate parser for the platform."""
        return get_parser(platform)  # Добавляем метод для доступа к парсеру

    def _translate(self, message: str) -> str:
        """Translate a message using the current locale."""
        return self.translations.gettext(message)

    async def check_new_orders(self, bot: Bot, chat_id: str) -> None:
        """Check for new orders in awaiting_packaging and send notifications."""
        for platform, client in self.clients.items():
            try:
                status = "PROCESSING" if platform == "yandex" else "awaiting_packaging"
                substatus = "STARTED" if platform == "yandex" else None
                logger.debug(f"[{platform}] Attempting to fetch orders with status={status}, substatus={substatus}")
                orders = client.get_orders(status, substatus)
                sent_orders = self.db.load_sent_orders(platform)
                logger.info(f"[{platform}] Found {len(orders)} orders in new status")
                parser = get_parser(platform)
                for order_data in orders:
                    order_id = str(order_data["id" if platform == "yandex" else "posting_number"])
                    if order_id not in sent_orders:
                        order = parser.parse(order_data)
                        await self.notify_order(bot, chat_id, order, platform, client)
                        self.db.save_sent_order(order_id, platform)
                        NEW_ORDERS_TOTAL.inc()
            except requests.exceptions.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"[{platform}] Error checking new orders: HTTP {e.response.status_code} - {e.response.text}")
                else:
                    logger.error(f"[{platform}] Error checking new orders (no response): {str(e)}")
                API_ERRORS_TOTAL.inc()
            except Exception as e:
                logger.error(f"[{platform}] Unexpected error checking new orders: {str(e)}")
                API_ERRORS_TOTAL.inc()

    async def notify_order(self, bot: Bot, chat_id: str, order: Order, platform: str, client: MarketplaceClient) -> None:
        """Send a notification for a new order with label."""
        shop_skus = [item.shop_sku for item in order.items]
        market_sku_mapping = client.get_market_sku(shop_skus)
        items_text = []
        market_url = settings.YANDEX_MARKET_URL if platform == "yandex" else settings.OZON_MARKET_URL
        for item in order.items:
            mapping = market_sku_mapping.get(item.shop_sku)
            url = (
                f"{market_url}{mapping['marketModelId']}?sku={mapping['marketSku']}"
                if mapping else f"https://{platform}.ru/search?text={quote(item.offer_name)}"
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
            f"📦 *{self._translate('new_order')} #{order.id} ({platform})*\n\n"
            f"📋 *{self._translate('items')}*\n{items_text}\n\n"
            f"🏠 *{self._translate('delivery_address')}*\n  {full_address}\n"
            f"⏰ *{self._translate('shipment_deadline')}* {order.delivery.shipment_date}"
            f"{gift_notice}"
        )
        label_file = client.get_label(order.id)
        pdf_input = BufferedInputFile(label_file, filename=f"label_{order.id}.pdf") if label_file else None
        if not pdf_input:
            message += f"\n\n⚠️ {self._translate('label_error')}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=self._translate("ready_to_ship"), callback_data=f"ready_{order.id}_{platform}")]
        ])
        try:
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
            logger.info(f"[{platform}] Notification for order #{order.id} sent and pinned")
        except Exception as e:
            logger.error(f"[{platform}] Error sending notification for order #{order.id}: {str(e)}")

    async def check_overdue_orders(self, bot: Bot, chat_id: str) -> None:
        """Check for overdue orders and send notifications."""
        for platform, client in self.clients.items():
            try:
                status = "PROCESSING" if platform == "yandex" else "awaiting_deliver"
                substatus = "READY_TO_SHIP" if platform == "yandex" else None
                logger.debug(f"[{platform}] Attempting to fetch overdue orders with status={status}, substatus={substatus}")
                orders = client.get_orders(status, substatus)
                overdue_notified = self.db.load_overdue_notified(platform)
                logger.info(f"[{platform}] Found {len(orders)} orders in overdue status")
                parser = get_parser(platform)
                current_date = datetime.now()
                for order_data in orders:
                    order = parser.parse(order_data)
                    try:
                        shipment_date = datetime.strptime(order.delivery.shipment_date, "%Y-%m-%dT%H:%M:%SZ")
                        if (current_date - shipment_date).days >= 1 and order.id not in overdue_notified:
                            message = (
                                f"⚠️ *{self._translate('order_overdue')} #{order.id} ({platform})*\n"
                                f"⏰ {self._translate('shipment_deadline')}: {order.delivery.shipment_date}\n"
                                f"{self._translate('status')}: {status}"
                            )
                            await bot.send_message(chat_id, message, parse_mode="Markdown", disable_notification=False)
                            logger.warning(f"[{platform}] Sent overdue notification for order #{order.id}")
                            self.db.save_overdue_notified(order.id, platform)
                            OVERDUE_ORDERS_TOTAL.inc()
                    except ValueError:
                        logger.error(f"[{platform}] Invalid shipment date format for order #{order.id}: {order.delivery.shipment_date}")
            except requests.exceptions.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"[{platform}] Error checking overdue orders: HTTP {e.response.status_code} - {e.response.text}")
                else:
                    logger.error(f"[{platform}] Error checking overdue orders (no response): {str(e)}")
                API_ERRORS_TOTAL.inc()
            except Exception as e:
                logger.error(f"[{platform}] Unexpected error checking overdue orders: {str(e)}")
                API_ERRORS_TOTAL.inc()

    async def set_order_status_ready(self, bot: Bot, chat_id: str, order_id: str, platform: str) -> Dict:
        """Set an order status to READY_TO_SHIP (or equivalent) and create carriage for Ozon."""
        client = self.clients.get(platform)
        if not client:
            return {"status": "ERROR", "errors": [{"code": "INVALID_PLATFORM", "message": f"Platform {platform} not supported"}]}

        try:
            order_data = client.get_order_info(order_id)
            if not order_data:
                return {"status": "ERROR", "errors": [{"code": "FETCH_ERROR", "message": "Failed to fetch order data"}]}

            current_status = order_data.get("status")
            if platform == "yandex" and (current_status != "PROCESSING" or order_data.get("substatus") != "STARTED"):
                return {
                    "status": "ERROR",
                    "errors": [{"code": "INVALID_STATUS", "message": "Cannot transition to READY_TO_SHIP"}]
                }
            elif platform == "ozon" and current_status != "awaiting_packaging":
                return {
                    "status": "ERROR",
                    "errors": [{"code": "INVALID_STATUS", "message": "Cannot transition to awaiting_deliver"}]
                }

            items = [{"id": item["id"], "count": item["count"]} for item in order_data.get("items", [])] if platform == "yandex" else []
            status = "PROCESSING" if platform == "yandex" else "awaiting_deliver"
            substatus = "READY_TO_SHIP" if platform == "yandex" else None
            client.set_order_status(order_id, status, substatus, items)
            logger.info(f"[{platform}] Order #{order_id} status set to {status}")

            if platform == "ozon":
                try:
                    delivery_method_id = order_data["delivery_method"]["id"]
                    departure_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                    carriage_id = client.create_carriage(delivery_method_id=delivery_method_id, departure_date=departure_date)
                    logger.info(f"[ozon] Created carriage with ID {carriage_id} for delivery_method_id {delivery_method_id}")
                    client.approve_carriage(carriage_id, containers_count=1)
                    logger.info(f"[ozon] Approved carriage with ID {carriage_id}")

                    label_file = client.get_carriage_label(carriage_id)
                    if label_file:
                        pdf_input = BufferedInputFile(label_file, filename=f"carriage_{carriage_id}.pdf")
                        await bot.send_document(
                            chat_id,
                            document=pdf_input,
                            caption=f"📤 *Отгрузка #{carriage_id} сформирована для Ozon*\nВключает заказ: {order_id}",
                            parse_mode="Markdown",
                            disable_notification=False
                        )
                        logger.info(f"[ozon] Sent carriage label for carriage #{carriage_id} to chat")
                    else:
                        await bot.send_message(
                            chat_id,
                            f"⚠️ *Не удалось получить этикетку для отгрузки #{carriage_id}*",
                            parse_mode="Markdown"
                        )
                except requests.exceptions.HTTPError as e:
                    logger.error(f"[ozon] Failed to create/approve carriage for order #{order_id}: {str(e)}")
                    await bot.send_message(chat_id, f"⚠️ *Ошибка при создании/подтверждении отгрузки для #{order_id}: {str(e)}*", parse_mode="Markdown")
                    return {"status": "ERROR", "errors": [{"code": "CARRIAGE_ERROR", "message": str(e)}]}

            return {"status": "SUCCESS"}
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[{platform}] Error setting order status for #{order_id}: HTTP {e.response.status_code} - {e.response.text}")
            else:
                logger.error(f"[{platform}] Error setting order status for #{order_id} (no response): {str(e)}")
            API_ERRORS_TOTAL.inc()
            return {"status": "ERROR", "errors": [{"code": "HTTP_ERROR", "message": f"HTTP error: {str(e)}"}]}
        except Exception as e:
            logger.error(f"[{platform}] Error setting order status for #{order_id}: {str(e)}")
            API_ERRORS_TOTAL.inc()
            return {"status": "ERROR", "errors": [{"code": "INTERNAL_ERROR", "message": str(e)}]}