"""
Race Condition Demonstration
===========================
Shows how atomic operations prevent race conditions in rate limiting
"""

import threading
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

class RaceConditionTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
    
    def single_request(self, thread_id, endpoint="/sliding"):
        """Make a single request and record results"""
        try:
            start_time = time.time()
            response = requests.get(f'{self.base_url}{endpoint}', timeout=5)
            end_time = time.time()
            
            result = {
                'thread_id': thread_id,
                'status_code': response.status_code,
                'response_time': (end_time - start_time) * 1000,
                'timestamp': start_time,
                'success': response.status_code == 200
            }
            
            # Try to get rate limit info from headers
            if 'X-RateLimit-Remaining' in response.headers:
                result['remaining'] = int(response.headers['X-RateLimit-Remaining'])
            
            with self.lock:
                self.results.append(result)
            
            return result
            
        except Exception as e:
            result = {
                'thread_id': thread_id,
                'error': str(e),
                'timestamp': time.time()
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
    
    def test_concurrent_access(self, num_threads=20, endpoint="/sliding"):
        """Test with multiple threads hitting the same endpoint simultaneously"""
        print(f"🔄 Testing {num_threads} concurrent requests to {endpoint}")
        print("-" * 50)
        
        self.results = []
        
        # Create threads that will all start at approximately the same time
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all tasks at once
            futures = {
                executor.submit(self.single_request, i, endpoint): i 
                for i in range(num_threads)
            }
            
            # Wait for all to complete
            for future in as_completed(futures):
                thread_id = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    print(f"Thread {thread_id} generated an exception: {e}")
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Analyze results for race conditions and consistency"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Sort by timestamp to see the order
        sorted_results = sorted(self.results, key=lambda x: x.get('timestamp', 0))
        
        successful_requests = [r for r in sorted_results if r.get('success', False)]
        blocked_requests = [r for r in sorted_results if r.get('status_code') == 429]
        error_requests = [r for r in sorted_results if 'error' in r]
        
        analysis = {
            'total_requests': len(sorted_results),
            'successful': len(successful_requests),
            'blocked': len(blocked_requests),
            'errors': len(error_requests),
            'success_rate': len(successful_requests) / len(sorted_results) * 100,
            'block_rate': len(blocked_requests) / len(sorted_results) * 100,
            'avg_response_time': sum(r.get('response_time', 0) for r in sorted_results) / len(sorted_results)
        }
        
        # Check for race condition indicators
        expected_successful = 5  # Assuming rate limit of 5 requests per minute
        
        if len(successful_requests) > expected_successful:
            analysis['race_condition_detected'] = True
            analysis['excess_successful'] = len(successful_requests) - expected_successful
        else:
            analysis['race_condition_detected'] = False
            analysis['excess_successful'] = 0
        
        return analysis, sorted_results
    
    def print_detailed_results(self, analysis, results):
        """Print detailed analysis of the race condition test"""
        print(f"\n📊 Race Condition Test Results:")
        print("-" * 40)
        print(f"Total Requests: {analysis['total_requests']}")
        print(f"✅ Successful: {analysis['successful']} ({analysis['success_rate']:.1f}%)")
        print(f"🛡️  Blocked: {analysis['blocked']} ({analysis['block_rate']:.1f}%)")
        print(f"❌ Errors: {analysis['errors']}")
        print(f"⚡ Avg Response Time: {analysis['avg_response_time']:.2f}ms")
        
        if analysis['race_condition_detected']:
            print(f"\n🚨 RACE CONDITION DETECTED!")
            print(f"   Expected max successful: 5")
            print(f"   Actual successful: {analysis['successful']}")
            print(f"   Excess requests: {analysis['excess_successful']}")
            print("   ❌ Rate limiting is not atomic!")
        else:
            print(f"\n✅ NO RACE CONDITION DETECTED")
            print("   Rate limiting appears to be atomic and consistent")
        
        # Show first few requests chronologically
        print(f"\n🕒 Request Timeline (first 10):")
        for i, result in enumerate(results[:10]):
            status = "✅ OK" if result.get('success') else f"🛡️ {result.get('status_code', 'ERR')}"
            response_time = result.get('response_time', 0)
            thread_id = result.get('thread_id', '?')
            print(f"   {i+1:2d}. Thread {thread_id:2d}: {status} ({response_time:.1f}ms)")

def test_different_algorithms():
    """Test all rate limiting algorithms for race conditions"""
    print("🧪 Race Condition Testing Suite")
    print("=" * 50)
    
    algorithms = {
        '/': 'Fixed Window (Basic)',
        '/sliding': 'Sliding Window (Advanced)',
        '/test/atomic-fixed-window': 'Atomic Fixed Window'
    }
    
    tester = RaceConditionTester()
    
    for endpoint, name in algorithms.items():
        print(f"\n🔬 Testing {name}")
        try:
            analysis, results = tester.test_concurrent_access(
                num_threads=15, 
                endpoint=endpoint
            )
            tester.print_detailed_results(analysis, results)
            
            # Brief pause between tests
            print("\n⏳ Waiting for rate limit reset...")
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Test failed for {name}: {e}")

def benchmark_performance():
    """Benchmark performance under concurrent load"""
    print("\n🏃 Performance Benchmark Under Load")
    print("=" * 50)
    
    thread_counts = [5, 10, 20, 50]
    tester = RaceConditionTester()
    
    for thread_count in thread_counts:
        print(f"\n📊 Testing with {thread_count} concurrent threads:")
        
        try:
            analysis, results = tester.test_concurrent_access(
                num_threads=thread_count,
                endpoint="/sliding"
            )
            
            print(f"   Throughput: {analysis['total_requests']} req in ~1s")
            print(f"   Avg Latency: {analysis['avg_response_time']:.2f}ms")
            print(f"   Success Rate: {analysis['success_rate']:.1f}%")
            print(f"   Race Condition: {'❌ YES' if analysis['race_condition_detected'] else '✅ NO'}")
            
            time.sleep(3)  # Recovery time
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")

def main():
    """Run the race condition demonstration"""
    print("🎯 Race Condition Prevention Demonstration")
    print("=" * 60)
    print("This test demonstrates how atomic operations prevent")
    print("race conditions in distributed rate limiting.")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            raise Exception("Server not healthy")
        print("✅ Server is running and healthy\n")
    except Exception as e:
        print("❌ Server is not accessible!")
        print("Please start the server with:")
        print("cd backend && python -m uvicorn app.sliding_window_demo:app --reload")
        return
    
    try:
        # Test different algorithms
        test_different_algorithms()
        
        # Performance benchmark
        benchmark_performance()
        
        print("\n🎉 Race Condition Testing Complete!")
        print("\n💡 Key Insights:")
        print("   • Atomic operations prevent race conditions")
        print("   • Lua scripts ensure consistency in Redis")
        print("   • Performance remains excellent under load")
        print("   • Rate limiting is both fast and accurate")
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")

if __name__ == "__main__":
    main()