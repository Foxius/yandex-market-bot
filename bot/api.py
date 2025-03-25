import requests
import json
import os
from urllib.parse import quote
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

YANDEX_API_URL = "https://api.partner.market.yandex.ru"
MARKET_URL = "https://market.yandex.ru/product/"  # Новый базовый URL
SENT_ORDERS_FILE = "sent_orders.json"

# Загрузка отправленных заказов из файла
def load_sent_orders():
    if os.path.exists(SENT_ORDERS_FILE):
        with open(SENT_ORDERS_FILE, "r") as f:
            return json.load(f)
    return []

# Сохранение отправленных заказов в файл
def save_sent_order(order_id: str):
    sent_orders = load_sent_orders()
    if order_id not in sent_orders:
        sent_orders.append(order_id)
        with open(SENT_ORDERS_FILE, "w") as f:
            json.dump(sent_orders, f)

# Получение marketSku и marketModelId по shopSku
def get_market_sku(business_id: str, api_token: str, shop_skus: list) -> dict:
    headers = {
        "Api-Key": f"{api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "offerIds": shop_skus
    }
    response = requests.post(
        f"{YANDEX_API_URL}/businesses/{business_id}/offer-mappings",
        headers=headers,
        json=payload
    )
    if response.status_code == 200:
        mappings = response.json().get("result", {}).get("offerMappings", [])
        sku_mapping = {}
        for mapping in mappings:
            shop_sku = mapping["offer"]["offerId"]
            mapping_data = mapping.get("mapping", {})
            market_sku = mapping_data.get("marketSku")
            market_model_id = mapping_data.get("marketModelId")
            if market_sku and market_model_id:
                sku_mapping[shop_sku] = {
                    "marketSku": str(market_sku),
                    "marketModelId": str(market_model_id)
                }
            print(f"shopSku: {shop_sku} -> marketSku: {market_sku}, marketModelId: {market_model_id}")
        return sku_mapping
    print(f"Ошибка получения marketSku: {response.status_code}, {response.text}")
    return {}

async def check_new_orders(bot: Bot, chat_id: str, api_token: str, campaign_id: str, business_id: str):
    headers = {
        "Api-Key": f"{api_token}",
        "Accept": "application/json"
    }
    response = requests.get(
        f"{YANDEX_API_URL}/campaigns/{campaign_id}/orders?status=PROCESSING",
        headers=headers
    )
    
    if response.status_code == 200:
        orders = response.json().get("orders", [])
        sent_orders = load_sent_orders()
        for order in orders:
            order_id = str(order["id"])
            if order_id not in sent_orders:
                await notify_order(bot, chat_id, order, campaign_id, api_token, business_id)
                save_sent_order(order_id)
    else:
        print(f"Ошибка получения заказов: {response.status_code}")

async def notify_order(bot: Bot, chat_id: str, order: dict, campaign_id: str, api_token: str, business_id: str):
    order_id = order["id"]
    items = order["items"]
    delivery = order["delivery"]
    address = delivery.get("address", {})
    items_total = order.get("itemsTotal", 0.0)
    
    full_address = (
        f"{address.get('country', '')}, "
        f"{address.get('postcode', '')}, "
        f"{address.get('city', '')}, "
        f"{address.get('street', '')}, "
        f"{address.get('house', '')}, "
        f"{address.get('block', '')}".strip(", ")
    )
    
    # Получаем marketSku и marketModelId для всех shopSku
    shop_skus = [item["shopSku"] for item in items]
    market_sku_mapping = get_market_sku(business_id, api_token, shop_skus)
    
    # Формирование списка товаров с корректными ссылками
    items_text = []
    for item in items:
        shop_sku = item["shopSku"]
        mapping = market_sku_mapping.get(shop_sku)
        if mapping and "marketSku" in mapping and "marketModelId" in mapping:
            url = f"{MARKET_URL}{mapping['marketModelId']}?sku={mapping['marketSku']}"
        else:
            url = f"https://market.yandex.ru/search?text={quote(item['offerName'])}"
        items_text.append(f"  • [{item['offerName']}]({url}) (x{item['count']})")
    items_text = "\n".join(items_text)
    
    gift_notice = "\n\n🎁 *Подарок не полагается* (сумма менее 300 ₽)" if items_total < 300 else ""
    
    message = (
        f"📦 *Новый заказ #{order_id}*\n\n"
        f"📋 *Товары:*\n{items_text}\n\n"
        f"🏠 *Адрес доставки:*\n  {full_address}"
        f"{gift_notice}"
    )
    
    headers = {"Api-Key": f"{api_token}"}
    label_response = requests.get(
        f"{YANDEX_API_URL}/campaigns/{campaign_id}/orders/{order_id}/delivery/labels",
        headers=headers,
        params={"format": "A9"}
    )
    
    pdf_input = None
    if label_response.status_code == 200:
        label_file = label_response.content
        pdf_input = BufferedInputFile(label_file, filename=f"label_{order_id}.pdf")
    else:
        print(f"Ошибка получения ярлыка для заказа #{order_id}: {label_response.status_code}")
        message += "\n\n⚠️ Не удалось получить этикетку"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Готов к отгрузке", callback_data=f"ready_{order_id}_{campaign_id}")]
    ])
    
    if pdf_input:
        sent_message = await bot.send_document(
            chat_id,
            document=pdf_input,
            caption=message,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_notification=False
        )
    else:
        sent_message = await bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_notification=False,
            disable_web_page_preview=True
        )
    
    await bot.pin_chat_message(chat_id, sent_message.message_id, disable_notification=False)

def get_pickup_point_address(order_id: str, campaign_id: str, api_token: str) -> str:
    headers = {"Api-Key": f"{api_token}"}
    response = requests.get(
        f"{YANDEX_API_URL}/campaigns/{campaign_id}/first-mile/shipments",
        headers=headers
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
                f"{YANDEX_API_URL}/campaigns/{campaign_id}/first-mile/shipments/{shipment_id}",
                headers=headers
            )
            if shipment_response.status_code == 200:
                shipment_data = shipment_response.json()
                if "delivery" in shipment_data and "address" in shipment_data["delivery"]:
                    addr = shipment_data["delivery"]["address"]
                    return f"{addr.get('city', '')}, {addr.get('street', '')}, {addr.get('house', '')}"
    return "Адрес ПВЗ не найден"

def set_order_status_ready(order_id: str, campaign_id: str, api_token: str) -> dict:
    headers = {
        "Api-Key": f"{api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Получаем текущую информацию о заказе
    order_info_response = requests.get(
        f"{YANDEX_API_URL}/campaigns/{campaign_id}/orders/{order_id}",
        headers=headers
    )
    
    if order_info_response.status_code != 200:
        return {
            "status": "ERROR",
            "errors": [{"code": "FETCH_ERROR", "message": f"Не удалось получить данные заказа: {order_info_response.text}"}]
        }
    
    order_data = order_info_response.json().get("order", {})
    current_status = order_data.get("status")
    current_substatus = order_data.get("substatus")
    print(f"Текущий статус заказа #{order_id}: {current_status}, подстатус: {current_substatus}")

    # Проверяем текущий статус
    if current_status != "PROCESSING" or current_substatus != "STARTED":
        return {
            "status": "ERROR",
            "errors": [{"code": "INVALID_STATUS", "message": f"Нельзя перевести заказ из статуса {current_status}/{current_substatus} в READY_TO_SHIP"}]
        }

    # Формируем данные о товарах
    items = [
        {
            "id": item.get("id"),
            "count": item.get("count")
        } for item in order_data.get("items", [])
    ]

    # Переводим заказ в PROCESSING/READY_TO_SHIP
    payload = {
        "order": {
            "status": "PROCESSING",
            "substatus": "READY_TO_SHIP",
            "items": items  # Подтверждаем состав заказа
        }
    }
    
    response = requests.put(
        f"{YANDEX_API_URL}/campaigns/{campaign_id}/orders/{order_id}/status",
        headers=headers,
        json=payload
    )
    
    response_json = response.json()
    print(f"Ответ API для READY_TO_SHIP: {response_json}")
    
    if response.status_code == 200 and response_json.get("status") == "OK":
        updated_order_response = requests.get(
            f"{YANDEX_API_URL}/campaigns/{campaign_id}/orders/{order_id}",
            headers=headers
        )
        updated_status = updated_order_response.json().get("order", {}).get("status")
        updated_substatus = updated_order_response.json().get("order", {}).get("substatus")
        print(f"Обновленный статус заказа #{order_id}: {updated_status}/{updated_substatus}")
    
    return response_json