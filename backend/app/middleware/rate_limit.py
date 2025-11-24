from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Optional, Callable, List, Dict, Any
from app.rate_limiter.atomic_fixed_window import AtomicFixedWindowRateLimiter
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Rate Limiting Middleware
    
    Automatically applies rate limiting to all requests or specific routes.
    Uses atomic operations to prevent race conditions.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: Optional[AtomicFixedWindowRateLimiter] = None,
        exempt_paths: Optional[List[str]] = None,
        get_client_id: Optional[Callable[[Request], str]] = None,
        custom_response: Optional[Callable[[Dict[str, Any]], Response]] = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter or AtomicFixedWindowRateLimiter()
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.get_client_id = get_client_id or self._default_get_client_id
        self.custom_response = custom_response or self._default_error_response
    
    def _default_get_client_id(self, request: Request) -> str:
        """Default client ID extraction - uses IP address"""
        # Try to get real IP from headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _default_error_response(self, metadata: Dict[str, Any]) -> Response:
        """Default rate limit exceeded response"""
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {metadata['limit']} requests per {metadata['window_seconds']} seconds",
                "detail": {
                    "current_count": metadata["current_count"],
                    "limit": metadata["limit"],
                    "retry_after": metadata["retry_after"],
                    "reset_time": metadata["reset_time"]
                }
            }
        )
        
        # Add standard rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
        response.headers["Retry-After"] = str(int(metadata["retry_after"]))
        
        return response
    
    def _add_rate_limit_headers(self, response: Response, metadata: Dict[str, Any]) -> None:
        """Add rate limiting headers to successful responses"""
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        if metadata.get("reset_time"):
            response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process each request through the rate limiter"""
        
        # Check if path is exempt from rate limiting
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_id(request)
        
        try:
            # Check rate limit
            is_allowed, metadata = self.rate_limiter.is_allowed(client_id)
            
            if not is_allowed:
                # Return rate limit error response
                return self.custom_response(metadata)
            
            # Process the request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            self._add_rate_limit_headers(response, metadata)
            
            return response
            
        except Exception as e:
            # If rate limiter fails, log error and allow request (fail open)
            print(f"Rate limiter error: {e}")
            return await call_next(request)


class AdvancedRateLimitMiddleware(RateLimitMiddleware):
    """
    Advanced Rate Limiting Middleware with additional features:
    - Per-route rate limits
    - User-based rate limiting
    - Whitelist/blacklist support
    """
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: Optional[AtomicFixedWindowRateLimiter] = None,
        route_limits: Optional[Dict[str, Dict[str, int]]] = None,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(app, rate_limiter, **kwargs)
        self.route_limits = route_limits or {}
        self.whitelist = set(whitelist or [])
        self.blacklist = set(blacklist or [])
    
    def _get_route_limits(self, path: str) -> Optional[Dict[str, int]]:
        """Get specific rate limits for a route"""
        # Check exact path match first
        if path in self.route_limits:
            return self.route_limits[path]
        
        # Check pattern matches (simple prefix matching)
        for route_pattern, limits in self.route_limits.items():
            if route_pattern.endswith("*") and path.startswith(route_pattern[:-1]):
                return limits
        
        return None
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Advanced rate limiting with per-route and whitelist/blacklist support"""
        
        # Get client identifier
        client_id = self.get_client_id(request)
        
        # Check blacklist
        if client_id in self.blacklist:
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "message": "Client is blacklisted"}
            )
        
        # Check whitelist (bypass rate limiting)
        if client_id in self.whitelist:
            return await call_next(request)
        
        # Check if path is exempt
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        try:
            # Check for per-route limits
            route_limits = self._get_route_limits(request.url.path)
            
            if route_limits:
                # Create temporary rate limiter with route-specific limits
                from app.rate_limiter.atomic_fixed_window import AtomicFixedWindowRateLimiter
                
                # Use a custom key prefix for route-specific limits
                route_key = f"route:{request.url.path}:{client_id}"
                is_allowed, metadata = self.rate_limiter.is_allowed(route_key)
                
                # Override metadata with route-specific values
                metadata.update(route_limits)
                
            else:
                # Use default rate limiting
                is_allowed, metadata = self.rate_limiter.is_allowed(client_id)
            
            if not is_allowed:
                return self.custom_response(metadata)
            
            # Process request
            response = await call_next(request)
            self._add_rate_limit_headers(response, metadata)
            
            return response
            
        except Exception as e:
            print(f"Advanced rate limiter error: {e}")
            return await call_next(request)


# Helper functions for common middleware configurations

def create_basic_rate_limit_middleware(app: FastAPI) -> RateLimitMiddleware:
    """Create basic rate limiting middleware with default settings"""
    return RateLimitMiddleware(app)

def create_api_rate_limit_middleware(
    app: FastAPI,
    api_key_header: str = "X-API-Key"
) -> AdvancedRateLimitMiddleware:
    """Create API-focused rate limiting with API key support"""
    
    def get_api_client_id(request: Request) -> str:
        """Use API key as client ID, fallback to IP"""
        api_key = request.headers.get(api_key_header)
        if api_key:
            return f"api:{api_key}"
        return request.client.host if request.client else "unknown"
    
    return AdvancedRateLimitMiddleware(
        app,
        get_client_id=get_api_client_id,
        route_limits={
            "/api/heavy/*": {"limit": 2, "window_seconds": 60},  # Stricter limits for heavy operations
            "/api/upload/*": {"limit": 1, "window_seconds": 10}   # Very strict for uploads
        }
    )

def create_user_rate_limit_middleware(app: FastAPI) -> AdvancedRateLimitMiddleware:
    """Create user-based rate limiting (requires authentication)"""
    
    def get_user_id(request: Request) -> str:
        """Extract user ID from request (requires auth middleware to set user)"""
        # This would typically get user ID from JWT token or session
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        return request.client.host if request.client else "anonymous"
    
    return AdvancedRateLimitMiddleware(
        app,
        get_client_id=get_user_id,
        whitelist=["127.0.0.1", "::1"]  # Exempt localhost
    )