import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class MiddlewareRateLimitTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
    
    def make_request(self, endpoint, request_id=None):
        """Make a request to specified endpoint"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}")
            
            with self.lock:
                self.results.append({
                    "id": request_id or len(self.results) + 1,
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
                    "timestamp": time.time()
                })
            return response
        except Exception as e:
            with self.lock:
                self.results.append({
                    "id": request_id or len(self.results) + 1,
                    "endpoint": endpoint,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": time.time()
                })
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting on /test endpoint"""
        print("🧪 Testing Basic Rate Limiting (/test)")
        print("-" * 50)
        
        self.results.clear()
        
        # Make multiple requests to /test
        for i in range(7):
            response = self.make_request("/test", i+1)
            print(f"Request {i+1}: Status {response.status_code if response else 'ERROR'}")
            
            if response and response.status_code == 200:
                # Check for rate limit headers
                headers = response.headers
                if "X-RateLimit-Limit" in headers:
                    print(f"  Rate Limit Headers: Limit={headers['X-RateLimit-Limit']}, "
                          f"Remaining={headers.get('X-RateLimit-Remaining', 'N/A')}")
            elif response and response.status_code == 429:
                print(f"  RATE LIMITED! ❌")
                
            time.sleep(0.2)
    
    def test_per_route_limits(self):
        """Test different rate limits for different routes"""
        print("\n🧪 Testing Per-Route Rate Limits")
        print("-" * 50)
        
        routes_to_test = [
            ("/test", "Standard endpoint (5/min)"),
            ("/api/heavy", "Heavy operation (2/min)"),
            ("/api/upload", "Upload endpoint (1/30sec)"),
            ("/api/premium/feature", "Premium feature (50/min)")
        ]
        
        for endpoint, description in routes_to_test:
            print(f"\n📍 Testing {endpoint} - {description}")
            
            # Test each route with multiple requests
            success_count = 0
            for i in range(3):
                response = self.make_request(endpoint)
                if response and response.status_code == 200:
                    success_count += 1
                    print(f"  Request {i+1}: ✅ Success")
                elif response and response.status_code == 429:
                    print(f"  Request {i+1}: ❌ Rate Limited")
                else:
                    print(f"  Request {i+1}: ⚠️  Other ({response.status_code if response else 'ERROR'})")
                
                time.sleep(0.1)
            
            print(f"  Result: {success_count}/3 requests succeeded")
    
    def test_exempt_paths(self):
        """Test that exempt paths are not rate limited"""
        print("\n🧪 Testing Exempt Paths")
        print("-" * 50)
        
        exempt_endpoints = [
            "/",
            "/health", 
            "/api/admin/status"
        ]
        
        for endpoint in exempt_endpoints:
            print(f"\n📍 Testing exempt path: {endpoint}")
            
            # Make many requests to exempt path
            all_success = True
            for i in range(10):
                response = self.make_request(endpoint)
                if not response or response.status_code != 200:
                    all_success = False
                    print(f"  Request {i+1}: ❌ Failed (Status: {response.status_code if response else 'ERROR'})")
                    break
            
            if all_success:
                print(f"  ✅ All 10 requests succeeded - path is exempt")
            else:
                print(f"  ❌ Some requests failed - path may not be exempt")
    
    def test_concurrent_requests(self):
        """Test middleware under concurrent load"""
        print("\n🧪 Testing Concurrent Requests")
        print("-" * 50)
        
        self.results.clear()
        
        def make_concurrent_request(i):
            return self.make_request("/test", i)
        
        # Send 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_concurrent_request, i+1) for i in range(10)]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Analyze results
        success_count = len([r for r in self.results if r["status"] == 200])
        blocked_count = len([r for r in self.results if r["status"] == 429])
        
        print(f"Concurrent test results:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Rate Limited: {blocked_count}")
        print(f"  Total: {len(self.results)}")
        
        if success_count <= 5:
            print("  ✅ Rate limiting working correctly under concurrency")
        else:
            print("  ⚠️  More than 5 requests succeeded - possible race condition")
    
    def test_rate_limit_headers(self):
        """Test that rate limit headers are properly set"""
        print("\n🧪 Testing Rate Limit Headers")
        print("-" * 50)
        
        response = self.make_request("/test")
        
        if response and response.status_code == 200:
            headers = response.headers
            required_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
            
            print("Rate limit headers:")
            for header in required_headers:
                if header in headers:
                    print(f"  ✅ {header}: {headers[header]}")
                else:
                    print(f"  ❌ {header}: Missing")
        else:
            print("❌ Could not test headers - request failed")
    
    def run_all_tests(self):
        """Run comprehensive middleware tests"""
        print("🚀 Starting Comprehensive Middleware Tests")
        print("=" * 60)
        
        try:
            self.test_basic_rate_limiting()
            self.test_per_route_limits()
            self.test_exempt_paths()
            self.test_concurrent_requests()
            self.test_rate_limit_headers()
            
            print("\n" + "=" * 60)
            print("✅ All middleware tests completed!")
            print("\nExpected behavior:")
            print("- Rate limits applied automatically via middleware")
            print("- Different limits for different routes")
            print("- Exempt paths allow unlimited requests")
            print("- Proper headers added to responses")
            print("- Concurrent requests handled correctly")
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            print("Make sure the server is running: python -m app.main_middleware")


if __name__ == "__main__":
    print("🧪 FastAPI Rate Limiting Middleware Tester")
    print("=" * 60)
    print("This tests the middleware-based rate limiting implementation.")
    print("Make sure the middleware server is running on localhost:8000")
    print()
    
    tester = MiddlewareRateLimitTester()
    
    # Check if server is accessible
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is accessible, starting tests...\n")
            tester.run_all_tests()
        else:
            print(f"❌ Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   cd backend")
        print("   python -m app.main_middleware")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")