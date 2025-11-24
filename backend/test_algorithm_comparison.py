import requests
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np


class AlgorithmComparisonTester:
    """Test suite to compare rate limiting algorithms"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {"fixed": [], "atomic": [], "sliding": []}
        self.lock = threading.Lock()
    
    def make_request(self, algorithm, request_id=None):
        """Make a request to specific algorithm endpoint"""
        endpoints = {
            "fixed": "/test/fixed",
            "atomic": "/test/atomic", 
            "sliding": "/test/sliding"
        }
        
        if algorithm not in endpoints:
            return None
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}{endpoints[algorithm]}")
            end_time = time.time()
            
            result = {
                "id": request_id or len(self.results[algorithm]) + 1,
                "algorithm": algorithm,
                "status": response.status_code,
                "duration": end_time - start_time,
                "timestamp": start_time,
                "allowed": response.status_code == 200
            }
            
            if response.headers.get("content-type", "").startswith("application/json"):
                result["data"] = response.json()
            
            with self.lock:
                self.results[algorithm].append(result)
            
            return result
            
        except Exception as e:
            result = {
                "id": request_id or len(self.results[algorithm]) + 1,
                "algorithm": algorithm,
                "status": "ERROR",
                "error": str(e),
                "timestamp": time.time(),
                "allowed": False
            }
            
            with self.lock:
                self.results[algorithm].append(result)
            
            return result
    
    def test_burst_behavior(self, num_requests=10, delay=0.1):
        """Test how algorithms handle burst traffic"""
        print(f"🚀 Testing Burst Behavior ({num_requests} requests)")
        print("=" * 60)
        
        algorithms = ["fixed", "atomic", "sliding"]
        
        for algorithm in algorithms:
            print(f"\n📊 Testing {algorithm.upper()} algorithm...")
            
            # Clear previous results
            self.results[algorithm].clear()
            
            # Send burst of requests
            start_time = time.time()
            for i in range(num_requests):
                result = self.make_request(algorithm, i + 1)
                if result:
                    status_emoji = "✅" if result["allowed"] else "❌"
                    print(f"  {status_emoji} Request {i+1}: {result['status']}")
                time.sleep(delay)
            
            # Analyze results
            allowed_count = sum(1 for r in self.results[algorithm] if r["allowed"])
            blocked_count = num_requests - allowed_count
            
            print(f"  📈 Results: {allowed_count} allowed, {blocked_count} blocked")
        
        self._analyze_burst_results()
    
    def test_window_boundary_behavior(self):
        """Test behavior at window boundaries (where fixed window issues occur)"""
        print("\n🕐 Testing Window Boundary Behavior")
        print("=" * 60)
        print("This test shows the 'burst at boundary' problem with fixed windows")
        
        # Reset all rate limiters first
        for algorithm in ["fixed", "atomic", "sliding"]:
            try:
                response = requests.post(f"{self.base_url}/admin/reset/{algorithm}/boundary_test")
                print(f"Reset {algorithm}: {response.json().get('reset_successful', False)}")
            except:
                pass
        
        time.sleep(1)  # Wait for reset to take effect
        
        # Test each algorithm at window boundary
        for algorithm in ["fixed", "atomic", "sliding"]:
            print(f"\n📊 Testing {algorithm} at window boundary...")
            
            # Make requests to fill up the limit
            allowed_in_window_1 = 0
            for i in range(6):  # Try to exceed limit
                result = self.make_request(algorithm, f"window1_{i+1}")
                if result and result["allowed"]:
                    allowed_in_window_1 += 1
                time.sleep(0.2)
            
            print(f"  Window 1: {allowed_in_window_1} requests allowed")
            
            # Wait for next window (fixed window algorithms) or continue (sliding window)
            if algorithm in ["fixed", "atomic"]:
                print("  Waiting for next fixed window...")
                time.sleep(61)  # Wait for new window
            else:
                print("  Sliding window - no boundary wait needed")
                time.sleep(2)
            
            # Try burst requests in new window/period
            allowed_in_window_2 = 0
            for i in range(6):
                result = self.make_request(algorithm, f"window2_{i+1}")
                if result and result["allowed"]:
                    allowed_in_window_2 += 1
                time.sleep(0.2)
            
            print(f"  Window 2: {allowed_in_window_2} requests allowed")
            
            # Analyze boundary behavior
            total_allowed = allowed_in_window_1 + allowed_in_window_2
            if algorithm in ["fixed", "atomic"] and total_allowed > 5:
                print(f"  ⚠️  Boundary burst detected! {total_allowed} total requests allowed")
            elif algorithm == "sliding" and total_allowed <= 5:
                print(f"  ✅ Smooth limiting - {total_allowed} total requests allowed")
    
    def test_concurrent_requests(self, num_threads=10):
        """Test algorithms under concurrent load"""
        print(f"\n⚡ Testing Concurrent Requests ({num_threads} threads)")
        print("=" * 60)
        
        for algorithm in ["fixed", "atomic", "sliding"]:
            print(f"\n📊 Testing {algorithm} with {num_threads} concurrent requests...")
            
            self.results[algorithm].clear()
            
            def make_concurrent_request(thread_id):
                return self.make_request(algorithm, f"thread_{thread_id}")
            
            # Execute concurrent requests
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(make_concurrent_request, i) for i in range(num_threads)]
                
                for future in as_completed(futures):
                    future.result()  # Wait for completion
            
            end_time = time.time()
            
            # Analyze concurrent results
            allowed = sum(1 for r in self.results[algorithm] if r["allowed"])
            blocked = num_threads - allowed
            
            print(f"  📈 Results: {allowed} allowed, {blocked} blocked")
            print(f"  ⏱️  Duration: {end_time - start_time:.2f} seconds")
            
            # Check for race condition issues
            if algorithm == "fixed" and allowed > 5:
                print(f"  ⚠️  Possible race condition! Expected ≤5, got {allowed}")
            elif algorithm in ["atomic", "sliding"] and allowed <= 5:
                print(f"  ✅ Race condition safe - {allowed} requests allowed")
    
    def test_sliding_window_smoothness(self):
        """Test sliding window's smooth rate limiting"""
        print("\n🌊 Testing Sliding Window Smoothness")
        print("=" * 60)
        
        # Reset sliding window
        try:
            requests.post(f"{self.base_url}/admin/reset/sliding/smoothness_test")
        except:
            pass
        
        # Make requests over time and track when they're allowed
        request_times = []
        allowed_times = []
        
        print("Making requests over 2 minutes to test smoothness...")
        
        for i in range(20):  # 20 requests over 2 minutes
            start_time = time.time()
            result = self.make_request("sliding", f"smooth_{i+1}")
            
            request_times.append(start_time)
            
            if result and result["allowed"]:
                allowed_times.append(start_time)
                print(f"  ✅ Request {i+1}: Allowed")
            else:
                print(f"  ❌ Request {i+1}: Blocked")
            
            time.sleep(6)  # 6 seconds between requests
        
        # Analyze smoothness
        if allowed_times:
            intervals = [allowed_times[i] - allowed_times[i-1] for i in range(1, len(allowed_times))]
            avg_interval = sum(intervals) / len(intervals) if intervals else 0
            
            print(f"\n📊 Smoothness Analysis:")
            print(f"  Total requests: {len(request_times)}")
            print(f"  Allowed requests: {len(allowed_times)}")
            print(f"  Average interval between allowed requests: {avg_interval:.2f} seconds")
            print(f"  Expected interval for 5 req/min: 12 seconds")
            
            if abs(avg_interval - 12) < 3:
                print(f"  ✅ Smooth rate limiting achieved!")
            else:
                print(f"  ⚠️  Rate limiting may not be perfectly smooth")
    
    def _analyze_burst_results(self):
        """Analyze and compare burst test results"""
        print(f"\n📊 Burst Test Analysis")
        print("-" * 40)
        
        for algorithm in ["fixed", "atomic", "sliding"]:
            if self.results[algorithm]:
                allowed = sum(1 for r in self.results[algorithm] if r["allowed"])
                total = len(self.results[algorithm])
                percentage = (allowed / total) * 100 if total > 0 else 0
                
                print(f"{algorithm.upper()}: {allowed}/{total} allowed ({percentage:.1f}%)")
        
        print(f"\n💡 Expected Behavior:")
        print(f"  - All algorithms should allow ≤5 requests")
        print(f"  - Fixed window may have race conditions under high concurrency")
        print(f"  - Sliding window provides smoothest limiting")
    
    def generate_comparison_report(self):
        """Generate a comprehensive comparison report"""
        try:
            response = requests.get(f"{self.base_url}/demo/algorithm-explanation")
            if response.status_code == 200:
                explanation = response.json()
                
                print(f"\n📋 Algorithm Comparison Report")
                print("=" * 60)
                
                for alg_name, details in explanation["algorithms"].items():
                    print(f"\n🔧 {alg_name.upper().replace('_', ' ')}")
                    print(f"   Description: {details['description']}")
                    print(f"   Complexity: {details['complexity']}")
                    print(f"   Pros: {', '.join(details['pros'])}")
                    print(f"   Cons: {', '.join(details['cons'])}")
                
                print(f"\n📊 Comparison Matrix:")
                matrix = explanation["comparison_matrix"]
                for metric, values in matrix.items():
                    print(f"   {metric.replace('_', ' ').title()}:")
                    for alg, value in values.items():
                        print(f"     {alg}: {value}")
        
        except Exception as e:
            print(f"Could not generate comparison report: {e}")
    
    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🧪 Comprehensive Rate Limiting Algorithm Comparison")
        print("=" * 80)
        print("This test suite compares Fixed Window, Atomic Fixed Window, and Sliding Window algorithms")
        print()
        
        try:
            # Quick connectivity test
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print("❌ Server health check failed")
                return
            
            print("✅ Server is healthy, starting tests...\n")
            
            # Run test suite
            self.test_burst_behavior(num_requests=7, delay=0.2)
            self.test_concurrent_requests(num_threads=8)
            
            # Note: Window boundary and smoothness tests take longer
            print(f"\n⏳ Running extended tests (this may take a few minutes)...")
            # self.test_window_boundary_behavior()  # Uncomment for full test
            # self.test_sliding_window_smoothness()  # Uncomment for full test
            
            self.generate_comparison_report()
            
            print(f"\n" + "=" * 80)
            print("✅ Comprehensive testing completed!")
            
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Please start the server first:")
            print("   cd backend")
            print("   python -m app.sliding_window_demo")
        except Exception as e:
            print(f"❌ Test suite failed: {e}")


if __name__ == "__main__":
    tester = AlgorithmComparisonTester()
    tester.run_comprehensive_test()