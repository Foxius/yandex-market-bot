import asyncio
from aiogram import Bot
from src.api.services import OrderService
from src.utils.logging import logger
from src.config.settings import settings
import pytz
from datetime import datetime, timedelta

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

async def daily_plan(bot: Bot, order_service: OrderService) -> None:
    """Send daily plan at 8 AM UTC+5.

    Args:
        bot (Bot): Telegram bot instance.
        order_service (OrderService): Order service instance.
    """
    tz = pytz.timezone('Asia/Yekaterinburg')  # UTC+5 соответствует Екатеринбургу
    while True:
        try:
            now = datetime.now(tz)
            # Проверяем, 8 утра ли сейчас (с погрешностью в минуту для точности)
            target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now.hour == 8 and now.minute == 0:
                logger.info("Generating daily plan...")
                await send_daily_plan(bot, order_service, settings.CHAT_ID)
                # Ждем сутки перед следующей проверкой
                await asyncio.sleep(24 * 3600)
            else:
                # Вычисляем, сколько секунд осталось до 8 утра следующего дня
                if now > target_time:
                    next_day = now + timedelta(days=1)
                    target_time = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
                seconds_until_target = (target_time - now).total_seconds()
                logger.debug(f"Waiting {seconds_until_target} seconds until 8 AM UTC+5")
                await asyncio.sleep(seconds_until_target)
        except Exception as e:
            logger.error(f"Error in daily plan task: {str(e)}")
            await asyncio.sleep(60)  # Ждем минуту перед повторной попыткой в случае ошибки

async def send_daily_plan(bot: Bot, order_service: OrderService, chat_id: str) -> None:
    """Generate and send the daily plan based on current orders."""
    message_lines = [f"📅 *{order_service._translate('daily_plan')}*"]
    has_tasks = False

    for platform, client in order_service.clients.items():
        try:
            status = "PROCESSING" if platform == "yandex" else "awaiting_deliver"
            substatus = "READY_TO_SHIP" if platform == "yandex" else None
            orders = client.get_orders(status, substatus)
            parser = order_service.get_parser(platform)

            if orders:
                has_tasks = True
                message_lines.append(f"\n*{platform.capitalize()} {order_service._translate('orders')}:*")
                for order_data in orders:
                    order = parser.parse(order_data)
                    order_id = order.id
                    
                    if platform == "yandex":
                        pvz_address = client.get_pickup_point_address(order_id)
                        message_lines.append(
                            f"  • {order_service._translate('bring_to_pvz_order')} #{order_id} "
                            f"{order_service._translate('to_address')}: {pvz_address}"
                        )
                    elif platform == "ozon":
                        message_lines.append(
                            f"  • {order_service._translate('give_to_courier')} #{order_id}"
                        )
        except Exception as e:
            logger.error(f"[{platform}] Error fetching orders for daily plan: {str(e)}")
            message_lines.append(f"\n⚠️ {order_service._translate('fetch_orders_error')} {platform}: {str(e)}")

    if not has_tasks:
        message_lines.append(f"\n📌 {order_service._translate('no_tasks_today')}")

    message = "\n".join(message_lines)
    await bot.send_message(chat_id, message, parse_mode="Markdown", disable_notification=False)
    logger.info("Daily plan sent successfully")