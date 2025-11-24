from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.database import redis_conn
from app.config import settings
from app.rate_limiter.atomic_fixed_window import AtomicFixedWindowRateLimiter
from app.middleware.rate_limit import (
    RateLimitMiddleware,
    AdvancedRateLimitMiddleware,
    create_basic_rate_limit_middleware,
    create_api_rate_limit_middleware
)
import uvicorn
import time
import random

# Global rate limiter
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
        print("✅ Rate limiter initialized")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("📝 To enable Redis: docker run -d -p 6379:6379 redis:latest")
        rate_limiter = AtomicFixedWindowRateLimiter()
    
    yield
    
    # Shutdown
    redis_conn.disconnect()
    print("🔌 Disconnected from Redis")

app = FastAPI(
    title="Distributed Rate Limiter - Middleware Version",
    description="Rate limiting using reusable FastAPI middleware",
    version="3.0.0",
    lifespan=lifespan
)

# Add rate limiting middleware
app.add_middleware(
    AdvancedRateLimitMiddleware,
    rate_limiter=rate_limiter,
    exempt_paths=["/", "/health", "/docs", "/redoc", "/openapi.json", "/api/admin/status"],
    route_limits={
        "/api/heavy": {"limit": 2, "window_seconds": 60},
        "/api/upload": {"limit": 1, "window_seconds": 30},
        "/api/premium/*": {"limit": 50, "window_seconds": 60}
    },
    whitelist=["127.0.0.1"],  # Localhost is exempt
    blacklist=["192.168.1.100"]  # Example blocked IP
)

@app.get("/")
async def root():
    return {
        "message": "Distributed Rate Limiter API - Middleware Version",
        "status": "running",
        "version": "3.0.0",
        "features": [
            "FastAPI Middleware Integration",
            "Automatic Rate Limiting",
            "Per-Route Limits",
            "Whitelist/Blacklist Support",
            "Race Condition Safe"
        ],
        "middleware": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint (exempt from rate limiting)"""
    redis_healthy = redis_conn.health_check()
    return {
        "status": "healthy" if redis_healthy else "unhealthy",
        "redis": "connected" if redis_healthy else "disconnected",
        "rate_limiter": "middleware_enabled",
        "middleware": "active"
    }

@app.get("/test")
async def test_endpoint(request: Request):
    """Standard test endpoint with default rate limiting (5 req/min)"""
    return {
        "message": "This endpoint uses middleware-based rate limiting",
        "your_ip": request.client.host,
        "timestamp": time.time(),
        "rate_limit": "5 requests per 60 seconds (via middleware)",
        "middleware": True
    }

@app.get("/api/heavy")
async def heavy_operation():
    """Heavy operation with stricter rate limiting (2 req/min)"""
    # Simulate heavy operation
    await asyncio.sleep(0.5)
    return {
        "message": "Heavy operation completed",
        "rate_limit": "2 requests per 60 seconds",
        "processing_time": "500ms",
        "middleware": True
    }

@app.post("/api/upload")
async def upload_endpoint():
    """Upload endpoint with very strict rate limiting (1 req/30sec)"""
    return {
        "message": "File upload processed",
        "rate_limit": "1 request per 30 seconds",
        "status": "success",
        "middleware": True
    }

@app.get("/api/premium/feature")
async def premium_feature():
    """Premium feature with higher rate limits (50 req/min)"""
    return {
        "message": "Premium feature accessed",
        "rate_limit": "50 requests per 60 seconds",
        "tier": "premium",
        "middleware": True
    }

@app.get("/api/no-limit")
async def no_limit_test():
    """Endpoint to test without any manual rate limiting"""
    return {
        "message": "This endpoint only has middleware rate limiting",
        "automatic": True,
        "middleware": True,
        "timestamp": time.time()
    }

@app.get("/api/admin/status")
async def admin_status():
    """Admin endpoint (exempt from rate limiting)"""
    return {
        "message": "Admin endpoint - no rate limits",
        "exempt": True,
        "middleware": "bypassed",
        "timestamp": time.time()
    }

@app.get("/api/simulate-load")
async def simulate_load():
    """Endpoint to simulate varying load times"""
    delay = random.uniform(0.1, 1.0)
    await asyncio.sleep(delay)
    return {
        "message": "Load simulation complete",
        "delay_seconds": round(delay, 2),
        "middleware": True
    }

# Manual rate limiting example (for comparison)
@app.get("/api/manual-rate-limit")
async def manual_rate_limit_example(request: Request):
    """Example of manual rate limiting (not recommended with middleware)"""
    client_ip = request.client.host
    is_allowed, metadata = rate_limiter.is_allowed(f"manual:{client_ip}")
    
    if not is_allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Manual rate limit exceeded",
                "message": "This is manually implemented rate limiting",
                "middleware": False,
                **metadata
            }
        )
    
    return {
        "message": "Manual rate limiting example",
        "middleware": False,
        "manual_implementation": True,
        "rate_limit_info": metadata
    }

# Demonstration endpoints for different middleware configurations
@app.get("/api/demo/basic")
async def demo_basic_middleware():
    """Demonstrates basic middleware usage"""
    return {
        "message": "Basic middleware demonstration",
        "description": "Uses default IP-based rate limiting",
        "implementation": "RateLimitMiddleware",
        "middleware": True
    }

@app.get("/api/demo/advanced") 
async def demo_advanced_middleware():
    """Demonstrates advanced middleware features"""
    return {
        "message": "Advanced middleware demonstration", 
        "features": [
            "Per-route limits",
            "Whitelist/blacklist support",
            "Custom client ID extraction",
            "Flexible configuration"
        ],
        "implementation": "AdvancedRateLimitMiddleware",
        "middleware": True
    }

import asyncio

if __name__ == "__main__":
    uvicorn.run(
        "app.main_middleware:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload
    )