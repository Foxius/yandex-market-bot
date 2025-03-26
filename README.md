# Yandex Market Order Bot

A Telegram bot for monitoring Yandex Market orders with advanced features.

## Features
- **New Order Monitoring**: Checks for new orders every 5 minutes.
- **Overdue Notifications**: Notifies about overdue orders the day after the deadline.
- **Status Updates**: Updates order status to "Ready to Ship" via Telegram.
- **Retry Logic**: Handles API failures with exponential backoff.
- **Redis Storage**: Uses Redis for fast and scalable data storage.
- **Testing**: Includes unit tests with pytest.
- **Metrics**: Exports Prometheus metrics on port 8000.
- **Localization**: Supports Russian and English via Babel.
- **Containerization**: Runs in Docker with Redis.

## Requirements
- Python 3.9+
- Docker & Docker Compose

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd project
   ```
2. Install dependencies:
    ```bash
    poetry install
    ```
3. Set up .env:
    ```
    TELEGRAM_TOKEN=your_telegram_token
    CHAT_ID=your_chat_id
    YANDEX_API_TOKEN=your_yandex_token
    CAMPAIGN_ID=your_campaign_id
    BUSINESS_ID=your_business_id
    REDIS_HOST=redis
    REDIS_PORT=6379
    REDIS_DB=0
    LOCALE=ru  # or en
    PROMETHEUS_PORT=8000
    ```
4. Run with Docker:
    ```bash
    docker-compose up --build
    ```

## Testing
Run tests with:
    ```bash
    pytest tests/
    ```

## Metrics
Access Prometheus metrics at http://localhost:8000.

## Localization
Switch languages by setting LOCALE in .env to ru or en.

## License
MIT


