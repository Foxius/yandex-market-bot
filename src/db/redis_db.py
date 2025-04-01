# src/db/redis_db.py
import redis
from typing import List
from src.utils.logging import logger

class RedisDB:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def load_sent_orders(self, platform: str) -> List[str]:
        key = f"sent_orders_{platform}"
        try:
            return list(self.client.smembers(key))
        except redis.RedisError as e:
            logger.error(f"[{platform}] Error loading sent orders from Redis: {str(e)}")
            return []

    def save_sent_order(self, order_id: str, platform: str) -> None:
        key = f"sent_orders_{platform}"
        try:
            self.client.sadd(key, order_id)
        except redis.RedisError as e:
            logger.error(f"[{platform}] Error saving sent order {order_id} to Redis: {str(e)}")

    def load_overdue_notified(self, platform: str) -> List[str]:
        key = f"overdue_notified_{platform}"
        try:
            return list(self.client.smembers(key))
        except redis.RedisError as e:
            logger.error(f"[{platform}] Error loading overdue notified orders from Redis: {str(e)}")
            return []

    def save_overdue_notified(self, order_id: str, platform: str) -> None:
        key = f"overdue_notified_{platform}"
        try:
            self.client.sadd(key, order_id)
        except redis.RedisError as e:
            logger.error(f"[{platform}] Error saving overdue notified order {order_id} to Redis: {str(e)}")

    def close(self) -> None:
        self.client.close()