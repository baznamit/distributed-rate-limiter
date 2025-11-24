# Load Testing Scripts for Distributed Rate Limiter

## Overview
This directory contains comprehensive load testing scripts using **Locust** to validate the performance and effectiveness of our distributed rate limiter.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Rate Limiter Server
```bash
cd ../backend
python -m uvicorn app.sliding_window_demo:app --reload
```

### 3. Run Load Tests
```bash
# Basic load test with web UI
locust -f locustfile.py --host=http://localhost:8000

# Headless mode (no web UI)
locust -f locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 60s --headless

# Advanced test scenarios
python run_test_scenarios.py
```

## Test Scenarios

### 1. Normal Load (locustfile.py)
- **Users**: 2 types - Normal and Aggressive
- **Duration**: Continuous until stopped
- **Purpose**: Test rate limiter under typical conditions
- **Expected**: Rate limits should be enforced, ~10-30% requests blocked

### 2. Stress Test Scenarios (run_test_scenarios.py)
- **Burst Traffic**: Sudden spike in requests
- **Sustained Load**: Continuous high traffic
- **Mixed Algorithms**: Test all three rate limiting algorithms
- **Geographic Simulation**: Different IP ranges

## Key Metrics to Monitor

### Rate Limiter Effectiveness
- **Rate Limited Requests**: Should be 10-30% under normal load
- **Response Times**: Should remain consistent even under load
- **Algorithm Performance**: Compare fixed window vs sliding window

### System Performance
- **Memory Usage**: Redis memory consumption
- **CPU Usage**: Server resource utilization
- **Throughput**: Requests per second handled

## Interpreting Results

### ✅ Good Results
- Rate limits are enforced (10-30% blocked requests)
- Response times remain low (< 100ms)
- No server errors or crashes
- Consistent performance across algorithms

### ⚠️ Warning Signs
- Very few requests blocked (< 5%)
- High response times (> 500ms)
- Memory leaks in Redis
- Inconsistent behavior

### 🚨 Critical Issues
- No rate limiting (0% blocked)
- Server crashes under load
- Data inconsistencies
- Race conditions detected

## Advanced Usage

### Custom Test Scenarios
```python
# Create custom user behavior
class CustomUser(HttpUser):
    @task
    def custom_behavior(self):
        # Your custom test logic
        pass
```

### Distributed Testing
```bash
# Run distributed load tests across multiple machines
locust -f locustfile.py --master --host=http://localhost:8000
locust -f locustfile.py --worker --master-host=192.168.1.100
```

## Troubleshooting

### Common Issues
1. **Connection Refused**: Make sure the FastAPI server is running on port 8000
2. **Redis Connection Failed**: Ensure Redis is running and accessible
3. **Rate Limits Not Working**: Check algorithm configuration and Redis connectivity

### Debug Mode
```bash
# Run with verbose logging
locust -f locustfile.py --host=http://localhost:8000 --loglevel DEBUG
```

## Integration with CI/CD

### Automated Performance Tests
```bash
# Example GitHub Actions or CI script
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 120s --headless --html=results.html
```

This ensures your rate limiter maintains performance standards with each deployment.