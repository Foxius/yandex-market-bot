import asyncio
from aiogram import Bot
from src.api.services import OrderService
from src.utils.logging import logger

async def periodic_check(bot: Bot, order_service: OrderService) -> None:
    """Periodically check for new orders.

    Args:
        bot (Bot): Telegram bot instance.
        order_service (OrderService): Order service instance.
    """
    while True:
        try:
            logger.info("Starting new orders check...")
            await order_service.check_new_orders(bot, settings.CHAT_ID)
            logger.info("New orders check completed successfully")
        except Exception as e:
            logger.error(f"Error in periodic check: {str(e)}")
        await asyncio.sleep(300)

async def periodic_overdue_check(bot: Bot, order_service: OrderService) -> None:
    """Periodically check for overdue orders.

    Args:
        bot (Bot): Telegram bot instance.
        order_service (OrderService): Order service instance.
    """
    while True:
        try:
            logger.info("Starting overdue orders check...")
            await order_service.check_overdue_orders(bot, settings.CHAT_ID)
            logger.info("Overdue orders check completed successfully")
        except Exception as e:
            logger.error(f"Error in overdue check: {str(e)}")
        await asyncio.sleep(3600)