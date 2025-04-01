# src/bot/handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from src.api.services import OrderService
from src.api.yandex_client import YandexAPIClient
from src.api.ozon_client import OzonAPIClient
from src.db.redis_db import RedisDB
from src.config.settings import settings
from src.utils.logging import logger

router = Router()

clients = {}
if settings.YANDEX_ENABLED:
    clients["yandex"] = YandexAPIClient(
        settings.YANDEX_API_TOKEN, settings.YANDEX_API_URL,
        settings.YANDEX_CAMPAIGN_ID, settings.YANDEX_BUSINESS_ID
    )
if settings.OZON_ENABLED:
    clients["ozon"] = OzonAPIClient(
        settings.OZON_API_KEY, settings.OZON_CLIENT_ID, settings.OZON_API_URL
    )

order_service = OrderService(
    clients,
    RedisDB(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
)

@router.callback_query(F.data.startswith("ready_"))
async def process_ready(callback: CallbackQuery) -> None:
    try:
        _, order_id, platform = callback.data.split("_")
        chat_id = callback.message.chat.id
        result = await order_service.set_order_status_ready(callback.bot, chat_id, order_id, platform)
        
        if result["status"] == "SUCCESS":
            if platform == "yandex":
                pvz_address = order_service.clients[platform].get_pickup_point_address(order_id)
                text = (
                    f"📦 *{order_service._translate('order_ready')} #{order_id} ({platform})*\n\n"
                    f"📍 *{order_service._translate('bring_to_pvz')}*\n  {pvz_address}"
                )
            else:  # Ozon уже отправляет сообщение с этикеткой в set_order_status_ready
                text = f"✅ Заказ #{order_id} готов к отгрузке!"
        else:
            error_message = result["errors"][0]["message"]
            text = f"❌ {order_service._translate('status_update_error')}:\n{error_message}"
        
        if callback.message.document:
            await callback.message.edit_caption(caption=text, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=None)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error processing ready callback: {str(e)}")
        text = f"❌ {order_service._translate('internal_error')}: {str(e)}"
        if callback.message.document:
            await callback.message.edit_caption(caption=text, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=None)
        await callback.answer()