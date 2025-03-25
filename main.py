import asyncio
from aiogram import Bot, Dispatcher
from bot.api import check_new_orders
from bot.handlers import router  # Импорт роутера из handlers.py
from dotenv import load_dotenv
import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Получение переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")
CAMPAIGN_ID = os.getenv("CAMPAIGN_ID")
BUSINESS_ID = os.getenv("BUSINESS_ID")

# Проверка наличия всех необходимых переменных
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

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Подключение роутера
dp.include_router(router)

async def periodic_check():
    """Периодическая проверка новых заказов"""
    while True:
        try:
            logger.info("Проверка новых заказов...")
            await check_new_orders(bot, CHAT_ID, YANDEX_API_TOKEN, CAMPAIGN_ID, BUSINESS_ID)
            logger.info("Проверка завершена успешно")
        except Exception as e:
            logger.error(f"Ошибка при проверке заказов: {str(e)}")
        await asyncio.sleep(300)  # Проверка каждые 5 минут

async def main():
    """Основная функция запуска"""
    try:
        logger.info("Запуск бота...")
        # Запуск периодической проверки и обработки обновлений параллельно
        await asyncio.gather(
            periodic_check(),
            dp.start_polling(bot)  # Запуск обработки обновлений от Telegram
        )
    except Exception as e:
        logger.error(f"Ошибка в main: {str(e)}")
    finally:
        await bot.session.close()  # Закрытие сессии бота

if __name__ == "__main__":
    asyncio.run(main())