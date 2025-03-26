import redis
from typing import List
from src.utils.logging import logger

class RedisDB:
    """Redis database handler for storing order data."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize the Redis connection.

        Args:
            host (str): Redis host address. Defaults to "localhost".
            port (int): Redis port number. Defaults to 6379.
            db (int): Redis database number. Defaults to 0.
        """
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.sent_orders_key = "sent_orders"
        self.overdue_notified_key = "overdue_notified"

    def load_sent_orders(self) -> List[str]:
        """Load list of sent order IDs from Redis.

        Returns:
            List[str]: List of order IDs.
        """
        try:
            return list(self.client.smembers(self.sent_orders_key))
        except redis.RedisError as e:
            logger.error(f"Error loading sent orders from Redis: {str(e)}")
            return []

    def save_sent_order(self, order_id: str) -> None:
        """Save an order ID to the sent_orders set in Redis.

        Args:
            order_id (str): The order ID to save.
        """
        try:
            self.client.sadd(self.sent_orders_key, order_id)
        except redis.RedisError as e:
            logger.error(f"Error saving sent order {order_id} to Redis: {str(e)}")

    def load_overdue_notified(self) -> List[str]:
        """Load list of overdue notified order IDs from Redis.

        Returns:
            List[str]: List of order IDs.
        """
        try:
            return list(self.client.smembers(self.overdue_notified_key))
        except redis.RedisError as e:
            logger.error(f"Error loading overdue notified orders from Redis: {str(e)}")
            return []

    def save_overdue_notified(self, order_id: str) -> None:
        """Save an order ID to the overdue_notified set in Redis.

        Args:
            order_id (str): The order ID to save.
        """
        try:
            self.client.sadd(self.overdue_notified_key, order_id)
        except redis.RedisError as e:
            logger.error(f"Error saving overdue notified order {order_id} to Redis: {str(e)}")

    def close(self) -> None:
        """Close the Redis connection."""
        self.client.close()