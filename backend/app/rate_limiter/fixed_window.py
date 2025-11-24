import time
import redis
from typing import Tuple
from app.config import settings
from app.database import redis_conn


class FixedWindowRateLimiter:
    """
    Fixed Window Rate Limiter implementation using Redis
    
    This implementation has a known race condition issue where multiple
    requests at the exact same time might both see the same counter value
    and both be allowed through, potentially exceeding the limit.
    
    This will be fixed in the next version using Lua scripting.
    """
    
    def __init__(self):
        self.redis_client = redis_conn.connect()
        self.requests_limit = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds
    
    def _get_window_key(self, client_id: str) -> str:
        """Generate a unique Redis key for the current window"""
        current_window = int(time.time()) // self.window_seconds
        return f"rate_limit:{client_id}:{current_window}"
    
    def is_allowed(self, client_id: str) -> Tuple[bool, dict]:
        """
        Check if a request from client_id is allowed
        
        Args:
            client_id: Unique identifier for the client (usually IP address)
            
        Returns:
            Tuple of (is_allowed, metadata)
            - is_allowed: Boolean indicating if request is allowed
            - metadata: Dict with current_count, limit, window_seconds, reset_time
        """
        key = self._get_window_key(client_id)
        
        try:
            # Get current count for this window
            current_count = self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Calculate reset time (end of current window)
            current_window = int(time.time()) // self.window_seconds
            reset_time = (current_window + 1) * self.window_seconds
            
            # Check if limit exceeded
            if current_count >= self.requests_limit:
                return False, {
                    "current_count": current_count,
                    "limit": self.requests_limit,
                    "window_seconds": self.window_seconds,
                    "reset_time": reset_time,
                    "retry_after": reset_time - time.time()
                }
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            
            # Set expiry if this is the first request in the window
            if current_count == 0:
                pipe.expire(key, self.window_seconds)
            
            pipe.execute()
            
            return True, {
                "current_count": current_count + 1,
                "limit": self.requests_limit,
                "window_seconds": self.window_seconds,
                "reset_time": reset_time,
                "retry_after": None
            }
            
        except Exception as e:
            # If Redis is unavailable, allow the request (fail open)
            print(f"Redis error in rate limiter: {e}")
            return True, {
                "current_count": 0,
                "limit": self.requests_limit,
                "window_seconds": self.window_seconds,
                "reset_time": None,
                "retry_after": None,
                "error": "Redis unavailable - failing open"
            }
    
    def get_remaining_requests(self, client_id: str) -> int:
        """Get the number of remaining requests for a client"""
        key = self._get_window_key(client_id)
        try:
            current_count = self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            return max(0, self.requests_limit - current_count)
        except Exception:
            return self.requests_limit
    
    def reset_client(self, client_id: str) -> bool:
        """Reset the rate limit counter for a client (admin function)"""
        key = self._get_window_key(client_id)
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error resetting client {client_id}: {e}")
            return False