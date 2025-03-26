import asyncio
from aiogram import Bot, Dispatcher
from src.bot.handlers import router
from src.bot.tasks import periodic_check, periodic_overdue_check
from src.api.client import YandexAPIClient
from src.api.services import OrderService
from src.db.redis_db import RedisDB
from src.config.settings import settings
from src.utils.logging import logger

async def main() -> None:
    """Application entry point."""
    settings.validate()
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    client = YandexAPIClient(settings.YANDEX_API_TOKEN, settings.YANDEX_API_URL)
    db = RedisDB(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
    order_service = OrderService(client, db)
    try:
        logger.info("Starting bot...")
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