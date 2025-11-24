from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from app.database import redis_conn
from app.config import settings
from app.rate_limiter.atomic_fixed_window import AtomicFixedWindowRateLimiter
import uvicorn
import time

# Global rate limiter (will be initialized in lifespan)
rate_limiter = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global rate_limiter
    try:
        redis_conn.connect()
        if not redis_conn.health_check():
            raise Exception("Failed to connect to Redis")
        print("✅ Connected to Redis successfully")
        rate_limiter = AtomicFixedWindowRateLimiter()
        print("✅ Atomic rate limiter initialized")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("📝 To enable Redis: docker run -d -p 6379:6379 redis:latest")
        # Initialize rate limiter anyway for development
        rate_limiter = AtomicFixedWindowRateLimiter()
    
    yield
    
    # Shutdown
    redis_conn.disconnect()
    print("🔌 Disconnected from Redis")

app = FastAPI(
    title="Distributed Rate Limiter - Atomic Version",
    description="A distributed rate limiting service using FastAPI, Redis, and Lua scripts for atomic operations",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "message": "Distributed Rate Limiter API - Atomic Version",
        "status": "running",
        "version": "2.0.0",
        "features": [
            "Atomic Fixed Window Rate Limiting",
            "Redis Lua Scripts",
            "Race Condition Safe"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_healthy = redis_conn.health_check()
    return {
        "status": "healthy" if redis_healthy else "unhealthy",
        "redis": "connected" if redis_healthy else "disconnected",
        "rate_limiter": "atomic" if rate_limiter else "not_initialized"
    }

@app.get("/test")
async def test_endpoint(request: Request):
    """Test endpoint with atomic rate limiting"""
    client_ip = request.client.host
    
    # Check rate limit atomically
    is_allowed, metadata = rate_limiter.is_allowed(client_ip)
    
    if not is_allowed:
        # Return 429 Too Many Requests
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {metadata['limit']} requests per {metadata['window_seconds']} seconds",
                "current_count": metadata["current_count"],
                "limit": metadata["limit"],
                "retry_after": metadata["retry_after"],
                "reset_time": metadata["reset_time"],
                "algorithm": "atomic_fixed_window"
            }
        )
        # Add rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
        response.headers["Retry-After"] = str(int(metadata["retry_after"]))
        return response
    
    # Request allowed
    response = JSONResponse(
        content={
            "message": "This is an atomic test endpoint",
            "your_ip": client_ip,
            "timestamp": time.time(),
            "rate_limit": {
                "current_count": metadata["current_count"],
                "limit": metadata["limit"],
                "remaining": metadata["remaining"],
                "reset_time": metadata["reset_time"],
                "algorithm": "atomic_fixed_window"
            }
        }
    )
    
    # Add rate limiting headers
    response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
    response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
    response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
    
    return response

@app.get("/api/rate-limit-status/{client_id}")
async def get_rate_limit_status(client_id: str):
    """Get current rate limit status for a client (atomic)"""
    status = rate_limiter.get_status(client_id)
    status["client_id"] = client_id
    status["algorithm"] = "atomic_fixed_window"
    return status

@app.post("/api/admin/reset/{client_id}")
async def reset_rate_limit(client_id: str):
    """Admin endpoint to reset rate limit for a client"""
    success = rate_limiter.reset_client(client_id)
    return {
        "client_id": client_id,
        "reset_successful": success,
        "message": f"Rate limit reset for {client_id}" if success else f"Failed to reset rate limit for {client_id}",
        "algorithm": "atomic_fixed_window"
    }

@app.get("/api/demo/race-condition")
async def demo_race_condition_protection():
    """Demonstration endpoint showing race condition protection"""
    return {
        "message": "This endpoint uses atomic Lua scripts to prevent race conditions",
        "explanation": [
            "Multiple simultaneous requests are processed atomically",
            "Redis Lua scripts guarantee no interruption during execution",
            "Counter increment and limit checking happen in single atomic operation",
            "No race condition possible even under high concurrency"
        ],
        "benefits": [
            "Accurate rate limiting under high load",
            "No over-limit requests due to timing issues",
            "Consistent behavior across multiple server instances"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main_atomic:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload
    )