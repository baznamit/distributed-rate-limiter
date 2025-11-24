from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from app.database import redis_conn
from app.config import settings
from app.rate_limiter.fixed_window import FixedWindowRateLimiter
import uvicorn
import time


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global rate_limiter
    try:
        redis_conn.connect()
        if not redis_conn.health_check():
            raise Exception("Failed to connect to Redis")
        print("✅ Connected to Redis successfully")
        rate_limiter = FixedWindowRateLimiter()
        print("✅ Rate limiter initialized")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("📝 To enable Redis: docker run -d -p 6379:6379 redis:latest")
        # Initialize a dummy rate limiter for development without Redis
        rate_limiter = FixedWindowRateLimiter()
    
    yield
    
    # Shutdown
    redis_conn.disconnect()
    print("🔌 Disconnected from Redis")


app = FastAPI(
    title="Distributed Rate Limiter",
    description="A distributed rate limiting service using FastAPI and Redis",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize rate limiter (will be set in lifespan)
rate_limiter = None


@app.get("/")
async def root():
    return {"message": "Distributed Rate Limiter API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_healthy = redis_conn.health_check()
    return {
        "status": "healthy" if redis_healthy else "unhealthy",
        "redis": "connected" if redis_healthy else "disconnected"
    }


@app.get("/test")
async def test_endpoint(request: Request):
    """Test endpoint for rate limiting"""
    client_ip = request.client.host
    
    # Check rate limit
    is_allowed, metadata = rate_limiter.is_allowed(client_ip)
    
    if not is_allowed:
        # Return 429 Too Many Requests with rate limit info
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {metadata['limit']} requests per {metadata['window_seconds']} seconds",
                "current_count": metadata["current_count"],
                "limit": metadata["limit"],
                "retry_after": metadata["retry_after"],
                "reset_time": metadata["reset_time"]
            }
        )
        # Add standard rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
        response.headers["Retry-After"] = str(int(metadata["retry_after"]))
        return response
    
    # Request allowed, return success with rate limit info
    remaining = metadata["limit"] - metadata["current_count"]
    response = JSONResponse(
        content={
            "message": "This is a test endpoint",
            "your_ip": client_ip,
            "timestamp": time.time(),
            "rate_limit": {
                "current_count": metadata["current_count"],
                "limit": metadata["limit"],
                "remaining": remaining,
                "reset_time": metadata["reset_time"]
            }
        }
    )
    
    # Add rate limiting headers
    response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
    
    return response


@app.get("/api/rate-limit-status/{client_id}")
async def get_rate_limit_status(client_id: str):
    """Get current rate limit status for a client"""
    key = rate_limiter._get_window_key(client_id)
    try:
        current_count = rate_limiter.redis_client.get(key)
        current_count = int(current_count) if current_count else 0
        remaining = rate_limiter.requests_limit - current_count
        
        # Calculate reset time
        current_window = int(time.time()) // rate_limiter.window_seconds
        reset_time = (current_window + 1) * rate_limiter.window_seconds
        
        return {
            "client_id": client_id,
            "current_count": current_count,
            "limit": rate_limiter.requests_limit,
            "remaining": max(0, remaining),
            "window_seconds": rate_limiter.window_seconds,
            "reset_time": reset_time,
            "is_blocked": current_count >= rate_limiter.requests_limit
        }
    except Exception as e:
        return {
            "client_id": client_id,
            "error": str(e),
            "limit": rate_limiter.requests_limit,
            "window_seconds": rate_limiter.window_seconds
        }


@app.post("/api/admin/reset/{client_id}")
async def reset_rate_limit(client_id: str):
    """Admin endpoint to reset rate limit for a client"""
    success = rate_limiter.reset_client(client_id)
    return {
        "client_id": client_id,
        "reset_successful": success,
        "message": f"Rate limit reset for {client_id}" if success else f"Failed to reset rate limit for {client_id}"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload
    )