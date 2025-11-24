import time
import redis
from typing import Tuple, Dict, Any
from app.config import settings
from app.database import redis_conn


class SlidingWindowRateLimiter:
    """
    Sliding Window Rate Limiter using Redis Sorted Sets (ZSET)
    
    This implementation provides smoother rate limiting by tracking individual
    request timestamps and maintaining a sliding time window. Unlike fixed windows,
    this approach doesn't allow burst traffic at window boundaries.
    
    Key benefits:
    - No burst allowance at window boundaries
    - More accurate rate limiting
    - Smoother user experience
    - Better traffic distribution
    """
    
    def __init__(self):
        self.redis_client = redis_conn.connect()
        self.requests_limit = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds
        
        # Load Lua scripts for atomic operations
        self._load_lua_scripts()
    
    def _load_lua_scripts(self):
        """Load optimized Lua scripts for sliding window operations"""
        
        # Atomic sliding window check and add script
        self.sliding_window_script = self.redis_client.register_script("""
            -- KEYS[1]: sliding window key (ZSET)
            -- ARGV[1]: current timestamp
            -- ARGV[2]: window size in seconds
            -- ARGV[3]: request limit
            -- ARGV[4]: request identifier (unique for this request)
            
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_seconds = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            local request_id = ARGV[4]
            
            -- Calculate window start time
            local window_start = now - window_seconds
            
            -- Remove expired entries (older than window)
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
            
            -- Count current requests in the window
            local current_count = redis.call('ZCARD', key)
            
            -- Check if limit would be exceeded
            if current_count >= limit then
                -- Calculate time until oldest request expires
                local oldest_scores = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                local retry_after = 0
                if #oldest_scores >= 2 then
                    local oldest_time = tonumber(oldest_scores[2])
                    retry_after = math.max(0, (oldest_time + window_seconds) - now)
                end
                
                return {
                    0,  -- not allowed
                    current_count,
                    limit,
                    retry_after,
                    now + retry_after  -- reset_time
                }
            end
            
            -- Add current request to the window
            redis.call('ZADD', key, now, request_id)
            
            -- Set expiry for the key (cleanup)
            redis.call('EXPIRE', key, window_seconds + 60)
            
            -- Calculate when the window will reset (when oldest request expires)
            local oldest_scores = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local reset_time = now + window_seconds
            if #oldest_scores >= 2 then
                local oldest_time = tonumber(oldest_scores[2])
                reset_time = oldest_time + window_seconds
            end
            
            return {
                1,  -- allowed
                current_count + 1,
                limit,
                0,  -- no retry_after needed
                reset_time
            }
        """)
        
        # Get current status without modifying the window
        self.get_sliding_status_script = self.redis_client.register_script("""
            -- KEYS[1]: sliding window key (ZSET)
            -- ARGV[1]: current timestamp
            -- ARGV[2]: window size in seconds
            -- ARGV[3]: request limit
            
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_seconds = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            
            -- Calculate window start time
            local window_start = now - window_seconds
            
            -- Remove expired entries
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
            
            -- Count current requests
            local current_count = redis.call('ZCARD', key)
            
            -- Get request timestamps for analysis
            local requests = redis.call('ZRANGE', key, 0, -1, 'WITHSCORES')
            
            -- Calculate reset time (when oldest request expires)
            local reset_time = now + window_seconds
            if #requests >= 2 then
                local oldest_time = tonumber(requests[2])
                reset_time = oldest_time + window_seconds
            end
            
            return {
                current_count,
                limit,
                math.max(0, limit - current_count),  -- remaining
                reset_time,
                requests  -- all request timestamps
            }
        """)
    
    def _get_window_key(self, client_id: str) -> str:
        """Generate Redis key for sliding window"""
        return f"sliding_window:{client_id}"
    
    def _generate_request_id(self, client_id: str) -> str:
        """Generate unique request identifier"""
        return f"{client_id}:{time.time()}:{id(object())}"
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed using sliding window algorithm
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Tuple of (is_allowed, metadata)
        """
        key = self._get_window_key(client_id)
        current_time = time.time()
        request_id = self._generate_request_id(client_id)
        
        try:
            result = self.sliding_window_script(
                keys=[key],
                args=[current_time, self.window_seconds, self.requests_limit, request_id]
            )
            
            is_allowed = bool(result[0])
            current_count = result[1]
            limit = result[2]
            retry_after = result[3]
            reset_time = result[4]
            
            return is_allowed, {
                "current_count": current_count,
                "limit": limit,
                "window_seconds": self.window_seconds,
                "retry_after": retry_after if not is_allowed else None,
                "reset_time": reset_time,
                "remaining": max(0, limit - current_count) if is_allowed else 0,
                "algorithm": "sliding_window"
            }
            
        except Exception as e:
            print(f"Redis error in sliding window rate limiter: {e}")
            # Fail open - allow request if Redis is unavailable
            return True, {
                "current_count": 0,
                "limit": self.requests_limit,
                "window_seconds": self.window_seconds,
                "retry_after": None,
                "reset_time": current_time + self.window_seconds,
                "remaining": self.requests_limit,
                "algorithm": "sliding_window",
                "error": "Redis unavailable - failing open"
            }
    
    def get_status(self, client_id: str) -> Dict[str, Any]:
        """Get current sliding window status without consuming a request"""
        key = self._get_window_key(client_id)
        current_time = time.time()
        
        try:
            result = self.get_sliding_status_script(
                keys=[key],
                args=[current_time, self.window_seconds, self.requests_limit]
            )
            
            current_count = result[0]
            limit = result[1]
            remaining = result[2]
            reset_time = result[3]
            request_timestamps = result[4] if len(result) > 4 else []
            
            # Parse request timestamps for detailed analysis
            requests = []
            for i in range(0, len(request_timestamps), 2):
                if i + 1 < len(request_timestamps):
                    timestamp = float(request_timestamps[i + 1])
                    requests.append({
                        "timestamp": timestamp,
                        "age_seconds": current_time - timestamp
                    })
            
            return {
                "client_id": client_id,
                "current_count": current_count,
                "limit": limit,
                "remaining": remaining,
                "window_seconds": self.window_seconds,
                "reset_time": reset_time,
                "is_blocked": current_count >= limit,
                "algorithm": "sliding_window",
                "requests": requests,
                "window_utilization": (current_count / limit) * 100 if limit > 0 else 0
            }
            
        except Exception as e:
            print(f"Error getting sliding window status: {e}")
            return {
                "client_id": client_id,
                "current_count": 0,
                "limit": self.requests_limit,
                "remaining": self.requests_limit,
                "window_seconds": self.window_seconds,
                "reset_time": current_time + self.window_seconds,
                "is_blocked": False,
                "algorithm": "sliding_window",
                "error": str(e),
                "requests": []
            }
    
    def reset_client(self, client_id: str) -> bool:
        """Reset sliding window for a client"""
        key = self._get_window_key(client_id)
        try:
            deleted = self.redis_client.delete(key)
            return deleted > 0
        except Exception as e:
            print(f"Error resetting sliding window for {client_id}: {e}")
            return False
    
    def get_window_analysis(self, client_id: str) -> Dict[str, Any]:
        """Get detailed analysis of the sliding window"""
        status = self.get_status(client_id)
        
        if not status["requests"]:
            return {
                **status,
                "request_distribution": [],
                "average_interval": 0,
                "burst_detected": False
            }
        
        requests = status["requests"]
        current_time = time.time()
        
        # Calculate request distribution over time
        distribution = []
        if len(requests) > 1:
            for i in range(len(requests) - 1):
                interval = requests[i]["timestamp"] - requests[i + 1]["timestamp"]
                distribution.append(interval)
        
        # Calculate average interval between requests
        avg_interval = sum(distribution) / len(distribution) if distribution else 0
        
        # Detect burst behavior (multiple requests in quick succession)
        burst_threshold = 5.0  # seconds
        recent_requests = [r for r in requests if r["age_seconds"] < burst_threshold]
        burst_detected = len(recent_requests) > (self.requests_limit * 0.5)
        
        return {
            **status,
            "request_distribution": distribution,
            "average_interval": avg_interval,
            "burst_detected": burst_detected,
            "recent_requests_count": len(recent_requests)
        }