import time
import redis
from typing import Tuple
from app.config import settings
from app.database import redis_conn


class AtomicFixedWindowRateLimiter:
    """
    Atomic Fixed Window Rate Limiter using Redis Lua Scripts
    
    This implementation fixes the race condition issue by using Lua scripts
    to perform get, increment, and check operations atomically in Redis.
    Redis guarantees that Lua scripts execute atomically - no other command
    can run while the script is executing.
    """
    
    def __init__(self):
        self.redis_client = redis_conn.connect()
        self.requests_limit = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds
        
        # Pre-load Lua scripts for better performance
        self._load_lua_scripts()
    
    def _load_lua_scripts(self):
        """Load Lua scripts into Redis"""
        
        # Atomic rate limit check and increment script
        self.rate_limit_script = self.redis_client.register_script("""
            -- KEYS[1]: rate limit key
            -- ARGV[1]: limit (max requests)
            -- ARGV[2]: window duration in seconds
            -- ARGV[3]: current timestamp
            
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window_seconds = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            
            -- Get current count
            local current_count = redis.call('GET', key)
            if current_count == false then
                current_count = 0
            else
                current_count = tonumber(current_count)
            end
            
            -- Calculate window end time
            local window_start = math.floor(current_time / window_seconds) * window_seconds
            local window_end = window_start + window_seconds
            
            -- Check if limit exceeded
            if current_count >= limit then
                -- Return rate limit exceeded
                return {
                    0,  -- not allowed
                    current_count,
                    limit,
                    window_end,
                    window_end - current_time  -- retry_after
                }
            end
            
            -- Increment counter
            local new_count = redis.call('INCR', key)
            
            -- Set expiry if this is the first request in the window
            if new_count == 1 then
                redis.call('EXPIRE', key, window_seconds)
            end
            
            -- Return success
            return {
                1,  -- allowed
                new_count,
                limit,
                window_end,
                0  -- no retry_after needed
            }
        """)
        
        # Get current status script (non-modifying)
        self.get_status_script = self.redis_client.register_script("""
            -- KEYS[1]: rate limit key
            -- ARGV[1]: limit (max requests)
            -- ARGV[2]: window duration in seconds
            -- ARGV[3]: current timestamp
            
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window_seconds = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            
            -- Get current count
            local current_count = redis.call('GET', key)
            if current_count == false then
                current_count = 0
            else
                current_count = tonumber(current_count)
            end
            
            -- Calculate window end time
            local window_start = math.floor(current_time / window_seconds) * window_seconds
            local window_end = window_start + window_seconds
            
            return {
                current_count,
                limit,
                window_end,
                math.max(0, limit - current_count)  -- remaining
            }
        """)
    
    def _get_window_key(self, client_id: str) -> str:
        """Generate a unique Redis key for the current window"""
        current_window = int(time.time()) // self.window_seconds
        return f"rate_limit_atomic:{client_id}:{current_window}"
    
    def is_allowed(self, client_id: str) -> Tuple[bool, dict]:
        """
        Atomically check if a request from client_id is allowed
        
        Args:
            client_id: Unique identifier for the client (usually IP address)
            
        Returns:
            Tuple of (is_allowed, metadata)
        """
        key = self._get_window_key(client_id)
        current_time = time.time()
        
        try:
            # Execute atomic Lua script
            result = self.rate_limit_script(
                keys=[key],
                args=[self.requests_limit, self.window_seconds, current_time]
            )
            
            is_allowed = bool(result[0])
            current_count = result[1]
            limit = result[2]
            reset_time = result[3]
            retry_after = result[4] if not is_allowed else None
            
            return is_allowed, {
                "current_count": current_count,
                "limit": limit,
                "window_seconds": self.window_seconds,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "remaining": max(0, limit - current_count) if is_allowed else 0
            }
            
        except Exception as e:
            # If Redis is unavailable, allow the request (fail open)
            print(f"Redis error in atomic rate limiter: {e}")
            return True, {
                "current_count": 0,
                "limit": self.requests_limit,
                "window_seconds": self.window_seconds,
                "reset_time": None,
                "retry_after": None,
                "remaining": self.requests_limit,
                "error": "Redis unavailable - failing open"
            }
    
    def get_status(self, client_id: str) -> dict:
        """Get current rate limit status without modifying counters"""
        key = self._get_window_key(client_id)
        current_time = time.time()
        
        try:
            result = self.get_status_script(
                keys=[key],
                args=[self.requests_limit, self.window_seconds, current_time]
            )
            
            current_count = result[0]
            limit = result[1]
            reset_time = result[2]
            remaining = result[3]
            
            return {
                "current_count": current_count,
                "limit": limit,
                "remaining": remaining,
                "window_seconds": self.window_seconds,
                "reset_time": reset_time,
                "is_blocked": current_count >= limit
            }
            
        except Exception as e:
            print(f"Redis error getting status: {e}")
            return {
                "current_count": 0,
                "limit": self.requests_limit,
                "remaining": self.requests_limit,
                "window_seconds": self.window_seconds,
                "reset_time": None,
                "is_blocked": False,
                "error": str(e)
            }
    
    def reset_client(self, client_id: str) -> bool:
        """Reset the rate limit counter for a client (admin function)"""
        key = self._get_window_key(client_id)
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error resetting client {client_id}: {e}")
            return False