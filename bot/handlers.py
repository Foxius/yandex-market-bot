from aiogram import Router, F
from aiogram.types import CallbackQuery
from .api import set_order_status_ready, get_pickup_point_address
from dotenv import load_dotenv
import os
import logging

# Настройка логирования для диагностики
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")

router = Router()

@router.callback_query(F.data.startswith("ready_"))
async def process_ready(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        if len(parts) != 3:
            raise ValueError(f"Неверный формат callback.data: {callback.data}")
        
        _, order_id, campaign_id = parts
        logger.info(f"Обработка заказа #{order_id} для campaign_id: {campaign_id}")

        if not YANDEX_API_TOKEN:
            raise ValueError("YANDEX_API_TOKEN не найден в переменных окружения")

        result = set_order_status_ready(order_id, campaign_id, YANDEX_API_TOKEN)
        logger.info(f"Результат API set_order_status_ready: {result}")

        # Проверяем успешность по наличию 'order' и подстатусу 'READY_TO_SHIP'
        if isinstance(result, dict) and "order" in result and result["order"].get("substatus") == "READY_TO_SHIP":
            pvz_address = get_pickup_point_address(order_id, campaign_id, YANDEX_API_TOKEN)
            logger.info(f"Адрес ПВЗ: {pvz_address}")
            text = f"📦 *Заказ #{order_id} готов к отгрузке!*\n\n📍 *Принести в ПВЗ:*\n  {pvz_address}"
            
            # Проверяем, есть ли документ в сообщении
            if callback.message.document:
                await callback.message.edit_caption(
                    caption=text,
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_text(
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=None
                )
        else:
            # Если есть ошибки в ответе, извлекаем их
            error_message = result.get("errors", "Неизвестная ошибка") if isinstance(result, dict) else str(result)
            logger.error(f"Ошибка API: {error_message}")
            text = f"❌ Ошибка при обновлении статуса:\n{error_message}"
            
            if callback.message.document:
                await callback.message.edit_caption(
                    caption=text,
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_text(
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=None
                )

        await callback.answer()

    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")
        text = f"❌ Произошла ошибка: {str(e)}"
        if callback.message.document:
            await callback.message.edit_caption(
                caption=text,
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=None
            )
        await callback.answer()