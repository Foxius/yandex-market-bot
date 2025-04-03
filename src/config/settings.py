# src/config/settings.py
from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    """Application configuration settings."""
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID: str = os.getenv("CHAT_ID")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", 8000))
    LOCALE: str = os.getenv("LOCALE", "ru")

    GIFT_THRESHOLD: float = float(os.getenv("GIFT_THRESHOLD", 300.0))  # Порог для подарка


    # Yandex Market settings
    YANDEX_API_TOKEN: str = os.getenv("YANDEX_API_TOKEN")
    YANDEX_API_URL: str = "https://api.partner.market.yandex.ru"
    YANDEX_MARKET_URL: str = "https://market.yandex.ru/product/"
    YANDEX_CAMPAIGN_ID: str = os.getenv("YANDEX_CAMPAIGN_ID")
    YANDEX_BUSINESS_ID: str = os.getenv("YANDEX_BUSINESS_ID")
    # Проверяем, что все данные для Яндекса есть
    YANDEX_ENABLED: bool = (
        os.getenv("YANDEX_ENABLED", "false").lower() == "true" and
        bool(YANDEX_API_TOKEN) and
        bool(YANDEX_CAMPAIGN_ID) and
        bool(YANDEX_BUSINESS_ID)
    )

    # Ozon settings (с учетом официальной документации Ozon API)
    OZON_API_KEY: str = os.getenv("OZON_API_KEY")
    OZON_CLIENT_ID: str = os.getenv("OZON_CLIENT_ID")
    OZON_API_URL: str = "https://api-seller.ozon.ru"
    OZON_MARKET_URL: str = "https://www.ozon.ru/product/"
    # Проверяем, что все данные для Ozon есть
    OZON_ENABLED: bool = (
        os.getenv("OZON_ENABLED", "false").lower() == "true" and
        bool(OZON_API_KEY) and
        bool(OZON_CLIENT_ID)
    )

    def validate(self) -> None:
        """Validate that all required environment variables are set."""
        required_general = {
            "TELEGRAM_TOKEN": self.TELEGRAM_TOKEN,
            "CHAT_ID": self.CHAT_ID
        }
        for name, value in required_general.items():
            if not value:
                raise ValueError(f"Environment variable {name} is not set!")
        if self.GIFT_THRESHOLD < 0:
            raise ValueError("GIFT_THRESHOLD must be non-negative!")
        if self.YANDEX_ENABLED:
            required_yandex = {
                "YANDEX_API_TOKEN": self.YANDEX_API_TOKEN,
                "YANDEX_CAMPAIGN_ID": self.YANDEX_CAMPAIGN_ID,
                "YANDEX_BUSINESS_ID": self.YANDEX_BUSINESS_ID
            }
            for name, value in required_yandex.items():
                if not value:
                    raise ValueError(f"Yandex enabled but {name} is not set!")

        if self.OZON_ENABLED:
            required_ozon = {
                "OZON_API_KEY": self.OZON_API_KEY,
                "OZON_CLIENT_ID": self.OZON_CLIENT_ID
            }
            for name, value in required_ozon.items():
                if not value:
                    raise ValueError(f"Ozon enabled but {name} is not set!")

settings = Settings()