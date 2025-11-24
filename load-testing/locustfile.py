"""
Load Testing for Distributed Rate Limiter
=========================================
This script uses Locust to test the rate limiter under various load conditions.

Run with:
    locust -f locustfile.py --host=http://localhost:8000

Key Features:
- Tests all three algorithms (fixed, atomic, sliding window)
- Simulates different client IPs  
- Measures response times and rate limit effectiveness
- Validates that rate limits are properly enforced
"""

import random
import time
from locust import HttpUser, task, between, events

class RateLimiterUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Wait between 0.1 to 0.5 seconds between requests
    
    def on_start(self):
        """Called when a user starts - simulate different client IPs"""
        self.client_ip = f"192.168.1.{random.randint(1, 100)}"
        self.headers = {
            "X-Forwarded-For": self.client_ip,
            "User-Agent": f"LoadTester-{self.client_ip}"
        }
    
    @task(3)
    def test_fixed_window(self):
        """Test fixed window rate limiter - most common scenario"""
        response = self.client.get(
            "/test/fixed-window",
            headers=self.headers,
            catch_response=True
        )
        
        if response.status_code == 200:
            response.success()
        elif response.status_code == 429:
            # Rate limited - this is expected behavior
            response.success()
            print(f"✓ Rate limit enforced for {self.client_ip} (Fixed Window)")
        else:
            response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def test_atomic_fixed_window(self):
        """Test atomic fixed window rate limiter"""
        response = self.client.get(
            "/test/atomic-fixed-window", 
            headers=self.headers,
            catch_response=True
        )
        
        if response.status_code == 200:
            response.success()
        elif response.status_code == 429:
            response.success()
            print(f"✓ Rate limit enforced for {self.client_ip} (Atomic Fixed Window)")
        else:
            response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(4)
    def test_sliding_window(self):
        """Test sliding window rate limiter - preferred algorithm"""
        response = self.client.get(
            "/test/sliding-window",
            headers=self.headers,
            catch_response=True
        )
        
        if response.status_code == 200:
            response.success()
        elif response.status_code == 429:
            response.success()
            print(f"✓ Rate limit enforced for {self.client_ip} (Sliding Window)")
        else:
            response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def test_health_check(self):
        """Test health endpoint - should never be rate limited"""
        response = self.client.get("/health")
        if response.status_code != 200:
            response.failure("Health check failed")

class AggressiveRateLimiterUser(HttpUser):
    """More aggressive user that tries to exceed rate limits quickly"""
    wait_time = between(0.01, 0.05)  # Very fast requests
    weight = 2  # Spawn 2x more of these users
    
    def on_start(self):
        self.client_ip = f"10.0.0.{random.randint(1, 50)}"
        self.headers = {
            "X-Forwarded-For": self.client_ip,
            "User-Agent": f"AggressiveBot-{self.client_ip}"
        }
    
    @task
    def rapid_fire_requests(self):
        """Make rapid requests to test rate limiting effectiveness"""
        algorithm = random.choice(["fixed-window", "atomic-fixed-window", "sliding-window"])
        
        response = self.client.get(
            f"/test/{algorithm}",
            headers=self.headers,
            catch_response=True
        )
        
        if response.status_code in [200, 429]:
            response.success()
            if response.status_code == 429:
                print(f"🛡️  Aggressive user blocked: {self.client_ip} ({algorithm})")
        else:
            response.failure(f"Unexpected status: {response.status_code}")

# Statistics tracking
rate_limited_requests = 0
successful_requests = 0

@events.request.add_listener
def track_rate_limits(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track rate limiting statistics"""
    global rate_limited_requests, successful_requests
    
    if response and hasattr(response, 'status_code'):
        if response.status_code == 429:
            rate_limited_requests += 1
        elif response.status_code == 200:
            successful_requests += 1

@events.test_stop.add_listener
def print_stats(environment, **kwargs):
    """Print final statistics"""
    total_requests = successful_requests + rate_limited_requests
    if total_requests > 0:
        rate_limit_percentage = (rate_limited_requests / total_requests) * 100
        print("\n" + "="*60)
        print("🔥 LOAD TEST RESULTS")
        print("="*60)
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {successful_requests}")
        print(f"Rate Limited Requests: {rate_limited_requests}")
        print(f"Rate Limit Effectiveness: {rate_limit_percentage:.1f}%")
        print("="*60)
        
        if rate_limit_percentage > 10:
            print("✅ Rate limiting is working effectively!")
        else:
            print("⚠️  Rate limiting may need tuning - very few requests blocked")