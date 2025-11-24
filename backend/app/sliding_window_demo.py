from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import redis_conn
from app.config import settings
from app.rate_limiter.fixed_window import FixedWindowRateLimiter
from app.rate_limiter.atomic_fixed_window import AtomicFixedWindowRateLimiter
from app.rate_limiter.sliding_window import SlidingWindowRateLimiter
import uvicorn
import time
from typing import Optional

# Global rate limiters
fixed_limiter = None
atomic_limiter = None
sliding_limiter = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global fixed_limiter, atomic_limiter, sliding_limiter
    try:
        redis_conn.connect()
        if not redis_conn.health_check():
            raise Exception("Failed to connect to Redis")
        print("✅ Connected to Redis successfully")
        
        fixed_limiter = FixedWindowRateLimiter()
        atomic_limiter = AtomicFixedWindowRateLimiter()
        sliding_limiter = SlidingWindowRateLimiter()
        
        print("✅ All rate limiters initialized")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("📝 To enable Redis: docker run -d -p 6379:6379 redis:latest")
        # Initialize anyway for development
        fixed_limiter = FixedWindowRateLimiter()
        atomic_limiter = AtomicFixedWindowRateLimiter()
        sliding_limiter = SlidingWindowRateLimiter()
    
    yield
    
    # Shutdown
    redis_conn.disconnect()
    print("🔌 Disconnected from Redis")

app = FastAPI(
    title="Rate Limiter Algorithm Comparison",
    description="Compare different rate limiting algorithms: Fixed Window, Atomic Fixed Window, and Sliding Window",
    version="4.0.0",
    lifespan=lifespan
)

# Add CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your dashboard domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_rate_limit_response(is_allowed: bool, metadata: dict, algorithm: str):
    """Create standardized rate limit response"""
    if not is_allowed:
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "algorithm": algorithm,
                "current_count": metadata["current_count"],
                "limit": metadata["limit"],
                "retry_after": metadata["retry_after"],
                "reset_time": metadata["reset_time"],
                "message": f"Rate limited by {algorithm} algorithm"
            }
        )
        response.headers["X-RateLimit-Algorithm"] = algorithm
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["Retry-After"] = str(int(metadata.get("retry_after", 60)))
        return response
    
    response = JSONResponse(
        content={
            "message": f"Request processed with {algorithm} algorithm",
            "algorithm": algorithm,
            "timestamp": time.time(),
            "rate_limit_info": metadata
        }
    )
    
    response.headers["X-RateLimit-Algorithm"] = algorithm
    response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
    response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
    
    return response

@app.get("/")
async def root():
    return {
        "message": "Rate Limiter Algorithm Comparison API",
        "version": "4.0.0",
        "algorithms": [
            "Fixed Window (basic)",
            "Atomic Fixed Window (race condition safe)",
            "Sliding Window (smooth limiting)"
        ],
        "endpoints": {
            "fixed": "/test/fixed - Basic fixed window rate limiting",
            "atomic": "/test/atomic - Atomic fixed window rate limiting", 
            "sliding": "/test/sliding - Sliding window rate limiting",
            "compare": "/compare - Side-by-side algorithm comparison"
        }
    }

@app.get("/health")
async def health_check():
    redis_healthy = redis_conn.health_check()
    return {
        "status": "healthy" if redis_healthy else "unhealthy",
        "redis": "connected" if redis_healthy else "disconnected",
        "limiters": {
            "fixed_window": "active" if fixed_limiter else "inactive",
            "atomic_fixed_window": "active" if atomic_limiter else "inactive",
            "sliding_window": "active" if sliding_limiter else "inactive"
        }
    }

@app.get("/test/fixed")
async def test_fixed_window(request: Request):
    """Test fixed window rate limiting"""
    client_ip = request.client.host
    is_allowed, metadata = fixed_limiter.is_allowed(client_ip)
    return create_rate_limit_response(is_allowed, metadata, "fixed_window")

@app.get("/test/atomic")
async def test_atomic_fixed_window(request: Request):
    """Test atomic fixed window rate limiting"""
    client_ip = request.client.host
    is_allowed, metadata = atomic_limiter.is_allowed(client_ip)
    return create_rate_limit_response(is_allowed, metadata, "atomic_fixed_window")

@app.get("/test/sliding")
async def test_sliding_window(request: Request):
    """Test sliding window rate limiting"""
    client_ip = request.client.host
    is_allowed, metadata = sliding_limiter.is_allowed(client_ip)
    return create_rate_limit_response(is_allowed, metadata, "sliding_window")

@app.get("/compare")
async def compare_algorithms(request: Request):
    """Compare all rate limiting algorithms side by side"""
    client_ip = request.client.host
    
    # Test each algorithm
    fixed_allowed, fixed_meta = fixed_limiter.is_allowed(f"compare_fixed:{client_ip}")
    atomic_allowed, atomic_meta = atomic_limiter.is_allowed(f"compare_atomic:{client_ip}")
    sliding_allowed, sliding_meta = sliding_limiter.is_allowed(f"compare_sliding:{client_ip}")
    
    return {
        "timestamp": time.time(),
        "client_ip": client_ip,
        "comparison": {
            "fixed_window": {
                "allowed": fixed_allowed,
                "algorithm": "fixed_window",
                "metadata": fixed_meta
            },
            "atomic_fixed_window": {
                "allowed": atomic_allowed,
                "algorithm": "atomic_fixed_window", 
                "metadata": atomic_meta
            },
            "sliding_window": {
                "allowed": sliding_allowed,
                "algorithm": "sliding_window",
                "metadata": sliding_meta
            }
        },
        "summary": {
            "total_allowed": sum([fixed_allowed, atomic_allowed, sliding_allowed]),
            "algorithms_that_allowed": [
                alg for alg, allowed in [
                    ("fixed_window", fixed_allowed),
                    ("atomic_fixed_window", atomic_allowed),
                    ("sliding_window", sliding_allowed)
                ] if allowed
            ]
        }
    }

@app.get("/status/fixed/{client_id}")
async def get_fixed_status(client_id: str):
    """Get fixed window status"""
    try:
        remaining = fixed_limiter.get_remaining_requests(client_id)
        return {
            "algorithm": "fixed_window",
            "client_id": client_id,
            "remaining_requests": remaining,
            "limit": fixed_limiter.requests_limit,
            "window_seconds": fixed_limiter.window_seconds
        }
    except Exception as e:
        return {"error": str(e), "algorithm": "fixed_window"}

@app.get("/status/atomic/{client_id}")
async def get_atomic_status(client_id: str):
    """Get atomic fixed window status"""
    status = atomic_limiter.get_status(client_id)
    status["algorithm"] = "atomic_fixed_window"
    return status

@app.get("/status/sliding/{client_id}")
async def get_sliding_status(client_id: str):
    """Get sliding window status with detailed analysis"""
    return sliding_limiter.get_window_analysis(client_id)

@app.get("/demo/burst-test")
async def burst_test_demo(
    request: Request,
    algorithm: str = Query("sliding", description="Algorithm to test: fixed, atomic, or sliding")
):
    """Demonstrate how different algorithms handle burst traffic"""
    client_ip = f"burst_test:{request.client.host}"
    
    # Select algorithm
    limiters = {
        "fixed": fixed_limiter,
        "atomic": atomic_limiter,
        "sliding": sliding_limiter
    }
    
    if algorithm not in limiters:
        return {"error": f"Invalid algorithm. Choose from: {list(limiters.keys())}"}
    
    limiter = limiters[algorithm]
    is_allowed, metadata = limiter.is_allowed(client_ip)
    
    # Add algorithm-specific analysis
    response_data = {
        "algorithm": algorithm,
        "burst_test": True,
        "allowed": is_allowed,
        "metadata": metadata,
        "explanation": {
            "fixed": "Fixed window allows bursts at window boundaries",
            "atomic": "Atomic fixed window prevents race conditions but still allows window boundary bursts",
            "sliding": "Sliding window provides smooth rate limiting without boundary effects"
        }.get(algorithm, "Unknown algorithm")
    }
    
    # Add sliding window specific analysis
    if algorithm == "sliding" and hasattr(limiter, 'get_window_analysis'):
        analysis = limiter.get_window_analysis(client_ip)
        response_data["sliding_analysis"] = {
            "burst_detected": analysis.get("burst_detected", False),
            "recent_requests": analysis.get("recent_requests_count", 0),
            "window_utilization": analysis.get("window_utilization", 0)
        }
    
    if is_allowed:
        return response_data
    else:
        return JSONResponse(status_code=429, content=response_data)

@app.post("/admin/reset/{algorithm}/{client_id}")
async def reset_client_limits(algorithm: str, client_id: str):
    """Reset rate limits for a specific client and algorithm"""
    limiters = {
        "fixed": fixed_limiter,
        "atomic": atomic_limiter,
        "sliding": sliding_limiter
    }
    
    if algorithm not in limiters:
        return {"error": f"Invalid algorithm. Choose from: {list(limiters.keys())}"}
    
    success = limiters[algorithm].reset_client(client_id)
    return {
        "algorithm": algorithm,
        "client_id": client_id,
        "reset_successful": success,
        "message": f"Rate limit reset for {client_id} using {algorithm} algorithm"
    }

@app.get("/demo/algorithm-explanation")
async def algorithm_explanation():
    """Detailed explanation of each algorithm"""
    return {
        "algorithms": {
            "fixed_window": {
                "description": "Divides time into fixed windows and counts requests per window",
                "pros": ["Simple to implement", "Memory efficient", "Predictable behavior"],
                "cons": ["Allows burst traffic at window boundaries", "Potential race conditions"],
                "use_cases": ["Basic rate limiting", "Low traffic applications"],
                "complexity": "Low"
            },
            "atomic_fixed_window": {
                "description": "Fixed window with atomic operations to prevent race conditions",
                "pros": ["Race condition safe", "Memory efficient", "Accurate under high concurrency"],
                "cons": ["Still allows burst traffic at window boundaries"],
                "use_cases": ["High concurrency applications", "Production systems"],
                "complexity": "Medium"
            },
            "sliding_window": {
                "description": "Tracks individual request timestamps in a sliding time window",
                "pros": ["Smooth rate limiting", "No burst allowance", "Most accurate"],
                "cons": ["Higher memory usage", "More complex implementation"],
                "use_cases": ["Premium APIs", "Critical systems", "Smooth user experience"],
                "complexity": "High"
            }
        },
        "comparison_matrix": {
            "memory_usage": {"fixed": "Low", "atomic": "Low", "sliding": "High"},
            "accuracy": {"fixed": "Medium", "atomic": "High", "sliding": "Highest"},
            "burst_handling": {"fixed": "Poor", "atomic": "Poor", "sliding": "Excellent"},
            "race_condition_safety": {"fixed": "No", "atomic": "Yes", "sliding": "Yes"},
            "implementation_complexity": {"fixed": "Low", "atomic": "Medium", "sliding": "High"}
        }
    }

@app.get("/api/dashboard/clients")
async def get_all_clients():
    """Get all active clients across algorithms"""
    clients = {}
    
    # This is a simplified version - in production you'd track this in Redis
    return {
        "clients": clients,
        "total_count": len(clients),
        "timestamp": time.time()
    }

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """Get overall system metrics for dashboard"""
    return {
        "system_status": "healthy" if redis_conn.health_check() else "unhealthy",
        "active_algorithms": ["fixed_window", "atomic_fixed_window", "sliding_window"],
        "redis_connected": redis_conn.health_check(),
        "uptime_seconds": time.time(),  # Simplified
        "timestamp": time.time()
    }

@app.post("/api/dashboard/ban/{client_id}")
async def ban_client(client_id: str):
    """Ban a client IP (add to blacklist)"""
    # In production, you'd store this in Redis
    return {
        "client_id": client_id,
        "banned": True,
        "message": f"Client {client_id} has been banned",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.sliding_window_demo:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload
    )