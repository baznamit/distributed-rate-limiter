import redis
from app.config import settings
from typing import Optional


class RedisConnection:
    _instance: Optional['RedisConnection'] = None
    _redis_client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConnection, cls).__new__(cls)
        return cls._instance
    
    def connect(self) -> redis.Redis:
        """Connect to Redis server"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        return self._redis_client
    
    def disconnect(self):
        """Disconnect from Redis server"""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
    
    def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            client = self.connect()
            client.ping()
            return True
        except Exception:
            return False


# Global Redis connection instance
redis_conn = RedisConnection()