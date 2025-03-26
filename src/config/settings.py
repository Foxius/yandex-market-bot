from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    """Application configuration settings."""
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID: str = os.getenv("CHAT_ID")
    YANDEX_API_TOKEN: str = os.getenv("YANDEX_API_TOKEN")
    CAMPAIGN_ID: str = os.getenv("CAMPAIGN_ID")
    BUSINESS_ID: str = os.getenv("BUSINESS_ID")
    YANDEX_API_URL: str = "https://api.partner.market.yandex.ru"
    MARKET_URL: str = "https://market.yandex.ru/product/"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", 8000))
    LOCALE: str = os.getenv("LOCALE", "ru")

    def validate(self) -> None:
        """Validate that all required environment variables are set.

        Raises:
            ValueError: If any required variable is missing.
        """
        required = {
            "TELEGRAM_TOKEN": self.TELEGRAM_TOKEN,
            "CHAT_ID": self.CHAT_ID,
            "YANDEX_API_TOKEN": self.YANDEX_API_TOKEN,
            "CAMPAIGN_ID": self.CAMPAIGN_ID,
            "BUSINESS_ID": self.BUSINESS_ID
        }
        for name, value in required.items():
            if not value:
                raise ValueError(f"Environment variable {name} is not set!")

settings = Settings()