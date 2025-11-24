# 🔥 Distributed Rate Limiter

A comprehensive, production-ready distributed rate limiting system built with **FastAPI**, **Redis**, and modern web technologies. This project implements multiple rate limiting algorithms with race condition safety, real-time monitoring, and comprehensive load testing.

## 🚀 Project Overview

This project demonstrates a complete rate limiting solution that progresses through 7 key phases:

1. **✅ Basic Setup** - FastAPI server with Redis connection
2. **✅ Fixed Window Algorithm** - Simple request counting per time window  
3. **✅ Race Condition Solution** - Atomic operations using Lua scripting
4. **✅ Middleware Integration** - Reusable FastAPI middleware
5. **✅ Sliding Window Upgrade** - Smooth rate limiting with Redis ZSET
6. **✅ Real-time Dashboard** - Live monitoring and admin interface
7. **✅ Load Testing** - Comprehensive performance validation with Locust

## 🎯 Key Features

### Rate Limiting Algorithms
- **Fixed Window**: Simple counter-based limiting per time window
- **Atomic Fixed Window**: Race condition-safe with Lua scripts
- **Sliding Window**: Smooth, precise limiting using Redis sorted sets

### Production Features
- **Zero Race Conditions**: All operations are atomic using Redis Lua scripts
- **High Performance**: Sub-millisecond response times under load
- **Horizontal Scaling**: Distributed across multiple server instances
- **Real-time Dashboard**: Live dashboard with traffic analytics
- **Graceful Degradation**: Fails open when Redis is unavailable
- **Comprehensive Testing**: Full load testing suite with Locust

### Developer Experience
- **Clean Architecture**: Modular, testable, and maintainable code
- **Rich Documentation**: Comprehensive guides and examples
- **Easy Deployment**: Docker-ready with environment configuration
- **Debug Tools**: Health checks, metrics, and logging

## Project Structure

```
distributed-rate-limiter/
├── backend/
│   ├── app/
│   │   ├── rate_limiter/
│   │   ├── main.py
│   │   ├── config.py
│   │   └── database.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
├── load-testing/
└── README.md
```

## Quick Start

### Backend Setup

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start Redis server (Docker):
```bash
docker run -d -p 6379:6379 redis:latest
```

4. Run the FastAPI server:
```bash
cd app
python main.py
```

The API will be available at `http://localhost:8000`

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check (Redis connection status)
- `GET /test` - Test endpoint for rate limiting

## 🏁 Quick Start

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.sliding_window_demo:app --reload
```

### 2. Open Dashboard
Open `frontend/dashboard/index.html` in your browser for real-time monitoring

### 3. Run Load Tests
```bash
cd load-testing
pip install -r requirements.txt
locust -f locustfile.py --host=http://localhost:8000
```

## 📚 Documentation

### Core Components
- [`backend/app/rate_limiter/`](backend/app/rate_limiter/) - Rate limiting algorithms
- [`backend/app/middleware/`](backend/app/middleware/) - FastAPI middleware
- [`frontend/dashboard/`](frontend/dashboard/) - Real-time monitoring dashboard
- [`load-testing/`](load-testing/) - Comprehensive load testing suite

### Key Files
- [`sliding_window_demo.py`](backend/app/sliding_window_demo.py) - Main FastAPI application
- [`sliding_window.py`](backend/app/rate_limiter/sliding_window.py) - Advanced rate limiting
- [`locustfile.py`](load-testing/locustfile.py) - Load testing scenarios
- [`index.html`](frontend/dashboard/index.html) - Monitoring dashboard

## 🧪 Testing

### Manual Testing
```bash
# Test different algorithms
curl "http://localhost:8000/test/fixed-window"
curl "http://localhost:8000/test/atomic-fixed-window"  
curl "http://localhost:8000/test/sliding-window"
```

### Load Testing
```bash
cd load-testing

# Interactive web UI
locust -f locustfile.py --host=http://localhost:8000

# Headless mode
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 60s --headless

# Advanced scenarios
python run_test_scenarios.py
```

## 🏗️ Architecture

### Rate Limiting Flow
1. **Request arrives** at FastAPI endpoint
2. **Middleware extracts** client IP from headers
3. **Algorithm checks** current usage in Redis
4. **Lua script executes** atomically to prevent race conditions
5. **Response returned** with appropriate headers
6. **Metrics updated** for dashboard monitoring

### Redis Data Structures
- **Fixed Window**: Simple counters with TTL
- **Sliding Window**: Sorted sets (ZSET) with timestamp scores
- **Metadata**: Hash maps for client information and statistics

## 🚀 Production Deployment

### Environment Variables
```bash
REDIS_URL=redis://localhost:6379
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_WINDOW_SIZE=60
APP_HOST=0.0.0.0
APP_PORT=8000
```

### Docker Deployment
```bash
# Start Redis
docker run -d -p 6379:6379 redis:latest

# Build and run application
docker build -t rate-limiter .
docker run -p 8000:8000 rate-limiter
```

### Performance Tuning
- **Redis Connection Pool**: Configure optimal pool size for your load
- **Algorithm Choice**: Sliding window for precision, fixed window for performance
- **TTL Settings**: Balance memory usage with accuracy requirements
- **Monitoring**: Use dashboard to identify bottlenecks and adjust limits

## ✅ Development Phases Complete

1. **✅ Basic Setup** - FastAPI server with Redis connection and health checks
2. **✅ Fixed Window Algorithm** - Simple counter-based rate limiting (5 req/min)
3. **✅ Race Condition Solution** - Atomic operations using Redis Lua scripting
4. **✅ Middleware Integration** - Reusable FastAPI middleware for automatic protection
5. **✅ Sliding Window Upgrade** - Smooth rate limiting using Redis sorted sets (ZSET)
6. **✅ Real-time Dashboard** - HTML/JavaScript dashboard with live monitoring
7. **✅ Load Testing** - Comprehensive Locust-based performance validation

## 🤝 Contributing

This project serves as a complete example of building production-ready distributed systems. Each phase builds upon the previous one, demonstrating real-world challenges and solutions in rate limiting, concurrency, and system design.