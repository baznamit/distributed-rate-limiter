# FastAPI Rate Limiting Middleware

## Overview
The middleware approach provides automatic rate limiting for all FastAPI endpoints without requiring code changes to individual route handlers. This creates a clean separation of concerns and makes rate limiting reusable across your entire application.

## Benefits of Middleware Approach

### 🔄 Automatic Application
- No need to add rate limiting code to each endpoint
- Consistent behavior across all routes
- Easy to enable/disable globally

### ⚙️ Flexible Configuration
- Per-route rate limits
- Exempt specific paths
- Custom client ID extraction
- Whitelist/blacklist support

### 🏗️ Clean Architecture
- Separation of concerns
- Reusable across projects
- Easy to test and maintain

## Implementation Comparison

| Approach | Manual Implementation | Middleware Implementation |
|----------|---------------------|--------------------------|
| **Code per endpoint** | Required | Not required |
| **Consistency** | Manual effort | Automatic |
| **Maintenance** | High | Low |
| **Flexibility** | Per-endpoint | Global + per-route |
| **Reusability** | Low | High |

## Basic Usage

### Simple Rate Limiting
```python
from app.middleware.rate_limit import RateLimitMiddleware

app = FastAPI()
app.add_middleware(RateLimitMiddleware)

@app.get("/api/data")  # Automatically rate limited!
async def get_data():
    return {"data": "This endpoint is automatically protected"}
```

### Advanced Configuration
```python
from app.middleware.rate_limit import AdvancedRateLimitMiddleware

app.add_middleware(
    AdvancedRateLimitMiddleware,
    exempt_paths=["/health", "/docs"],
    route_limits={
        "/api/heavy": {"limit": 2, "window_seconds": 60},
        "/api/upload": {"limit": 1, "window_seconds": 30}
    },
    whitelist=["127.0.0.1"],
    blacklist=["192.168.1.100"]
)
```

## Middleware Features

### 1. Automatic Rate Limiting
```python
# Before: Manual implementation needed in each endpoint
@app.get("/api/data")
async def get_data(request: Request):
    # Manual rate limiting code...
    is_allowed, metadata = rate_limiter.is_allowed(request.client.host)
    if not is_allowed:
        return JSONResponse(status_code=429, content={"error": "Rate limited"})
    
    return {"data": "response"}

# After: Automatic via middleware
@app.get("/api/data")  # Just implement business logic!
async def get_data():
    return {"data": "response"}
```

### 2. Per-Route Rate Limits
```python
route_limits = {
    "/api/search": {"limit": 10, "window_seconds": 60},    # Search: 10/min
    "/api/upload": {"limit": 2, "window_seconds": 300},    # Upload: 2/5min
    "/api/premium/*": {"limit": 100, "window_seconds": 60} # Premium: 100/min
}
```

### 3. Custom Client ID Extraction
```python
def get_api_key_client_id(request: Request) -> str:
    """Use API key as client identifier"""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api:{api_key}"
    return request.client.host

app.add_middleware(
    RateLimitMiddleware,
    get_client_id=get_api_key_client_id
)
```

### 4. Whitelist/Blacklist Support
```python
app.add_middleware(
    AdvancedRateLimitMiddleware,
    whitelist=["127.0.0.1", "::1"],          # Localhost exempt
    blacklist=["192.168.1.100", "10.0.0.5"] # Block these IPs
)
```

## Configuration Options

### RateLimitMiddleware Parameters
- `rate_limiter`: Rate limiter instance (default: AtomicFixedWindowRateLimiter)
- `exempt_paths`: List of paths to exempt from rate limiting
- `get_client_id`: Function to extract client ID from request
- `custom_response`: Function to create custom error responses

### AdvancedRateLimitMiddleware Additional Parameters
- `route_limits`: Per-route rate limit configuration
- `whitelist`: IPs/clients exempt from all rate limiting
- `blacklist`: IPs/clients to block completely

## Response Headers

The middleware automatically adds standard rate limiting headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1640995200

HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
Retry-After: 45
```

## Error Handling

### Fail Open Strategy
If Redis is unavailable, the middleware allows requests to proceed (fail open):

```python
try:
    is_allowed, metadata = self.rate_limiter.is_allowed(client_id)
except Exception as e:
    print(f"Rate limiter error: {e}")
    return await call_next(request)  # Allow request
```

### Custom Error Responses
```python
def custom_rate_limit_response(metadata: dict) -> Response:
    return JSONResponse(
        status_code=429,
        content={
            "error": "Custom rate limit message",
            "retry_after": metadata["retry_after"]
        }
    )

app.add_middleware(
    RateLimitMiddleware,
    custom_response=custom_rate_limit_response
)
```

## Testing the Middleware

### Basic Test
```bash
cd backend
python -m app.main_middleware  # Start server
python test_middleware.py     # Run tests
```

### Manual Testing
```bash
# Test basic rate limiting
curl -w "%{http_code}" http://localhost:8000/test

# Test per-route limits
curl -w "%{http_code}" http://localhost:8000/api/heavy

# Test exempt paths
curl -w "%{http_code}" http://localhost:8000/health
```

## Common Patterns

### API Key Rate Limiting
```python
def create_api_key_middleware(app: FastAPI):
    def get_api_client_id(request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        return f"api:{api_key}" if api_key else request.client.host
    
    return AdvancedRateLimitMiddleware(
        app,
        get_client_id=get_api_client_id,
        route_limits={
            "/api/v1/*": {"limit": 1000, "window_seconds": 3600},  # 1000/hour for v1
            "/api/v2/*": {"limit": 5000, "window_seconds": 3600}   # 5000/hour for v2
        }
    )
```

### User-Based Rate Limiting
```python
def create_user_middleware(app: FastAPI):
    def get_user_id(request: Request) -> str:
        # Extract from JWT token, session, etc.
        user_id = extract_user_from_token(request)
        return f"user:{user_id}" if user_id else "anonymous"
    
    return AdvancedRateLimitMiddleware(
        app,
        get_client_id=get_user_id,
        route_limits={
            "/api/user/*": {"limit": 100, "window_seconds": 3600}  # Per-user limits
        }
    )
```

## Next Steps
The middleware implementation provides a solid foundation for:
- Sliding window rate limiting
- Advanced algorithms (token bucket, etc.)
- Integration with authentication systems
- Monitoring and analytics
- Load balancer integration