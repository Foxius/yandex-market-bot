from aiogram import Router, F
from aiogram.types import CallbackQuery
from src.api.services import OrderService
from src.api.client import YandexAPIClient
from src.db.redis_db import RedisDB
from src.config.settings import settings
from src.utils.logging import logger

router = Router()
order_service = OrderService(
    YandexAPIClient(settings.YANDEX_API_TOKEN, settings.YANDEX_API_URL),
    RedisDB(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
)

@router.callback_query(F.data.startswith("ready_"))
async def process_ready(callback: CallbackQuery) -> None:
    """Handle the 'Ready to Ship' button callback.

    Args:
        callback (CallbackQuery): Telegram callback query object.
    """
    try:
        _, order_id, campaign_id = callback.data.split("_")
        result = order_service.set_order_status_ready(order_id)
        if "order" in result and result["order"].get("substatus") == "READY_TO_SHIP":
            pvz_address = order_service.client.get_pickup_point_address(campaign_id, order_id)
            text = (
                f"📦 *{order_service._translate('order_ready')} #{order_id}*\n\n"
                f"📍 *{order_service._translate('bring_to_pvz')}*\n  {pvz_address}"
            )
        else:
            error_message = result.get("errors", "Unknown error")
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