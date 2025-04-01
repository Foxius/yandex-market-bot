# src/main.py
import asyncio
from aiogram import Bot, Dispatcher
from src.bot.handlers import router
from src.bot.tasks import periodic_check, periodic_overdue_check
from src.api.yandex_client import YandexAPIClient
from src.api.ozon_client import OzonAPIClient
from src.api.services import OrderService
from src.db.redis_db import RedisDB
from src.config.settings import settings
from src.utils.logging import logger
from babel.support import Translations

async def main() -> None:
    settings.validate()
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

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

    db = RedisDB(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
    order_service = OrderService(clients, db)

    try:
        logger.info("Starting bot...")
        translations = Translations.load('locale', [settings.LOCALE])
        await bot.send_message(
            settings.CHAT_ID,
            translations.gettext("bot_started"),
            parse_mode="Markdown"
        )
        await asyncio.gather(
            periodic_check(bot, order_service),
            periodic_overdue_check(bot, order_service),
            dp.start_polling(bot)
        )
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())