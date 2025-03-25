import asyncio
from aiogram import Bot, Dispatcher
from bot.api import check_new_orders, check_overdue_orders
from bot.handlers import router
from dotenv import load_dotenv
import os
import logging
import colorlog

# Настройка цветных логов
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")
CAMPAIGN_ID = os.getenv("CAMPAIGN_ID")
BUSINESS_ID = os.getenv("BUSINESS_ID")

required_vars = {
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "CHAT_ID": CHAT_ID,
    "YANDEX_API_TOKEN": YANDEX_API_TOKEN,
    "CAMPAIGN_ID": CAMPAIGN_ID,
    "BUSINESS_ID": BUSINESS_ID
}

for var_name, var_value in required_vars.items():
    if not var_value:
        logger.error(f"Переменная окружения {var_name} не найдена!")
        raise ValueError(f"Переменная окружения {var_name} не найдена!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def periodic_check():
    while True:
        try:
            logger.info("Начинаем проверку новых заказов...")
            await check_new_orders(bot, CHAT_ID, YANDEX_API_TOKEN, CAMPAIGN_ID, BUSINESS_ID)
            logger.info("Проверка новых заказов завершена успешно")
        except Exception as e:
            logger.error(f"Ошибка при проверке заказов: {str(e)}")
        await asyncio.sleep(300)  # Проверка каждые 5 минут

async def periodic_overdue_check():
    while True:
        try:
            logger.info("Начинаем проверку просроченных заказов...")
            await check_overdue_orders(bot, CHAT_ID, YANDEX_API_TOKEN, CAMPAIGN_ID, BUSINESS_ID)
            logger.info("Проверка просроченных заказов завершена успешно")
        except Exception as e:
            logger.error(f"Ошибка при проверке просроченных заказов: {str(e)}")
        await asyncio.sleep(3600)  # Проверка каждый час

async def main():
    try:
        logger.info("Запуск бота...")
        await asyncio.gather(
            periodic_check(),
            periodic_overdue_check(),
            dp.start_polling(bot)
        )
    except Exception as e:
        logger.error(f"Ошибка в main: {str(e)}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())