"""
Basic Rate Limiter Usage Examples
================================
Demonstrates core functionality with real scenarios
"""

import asyncio
import aiohttp
import requests
import time
from datetime import datetime

def demo_basic_rate_limiting():
    """Show basic rate limiting in action"""
    print("🚀 Basic Rate Limiting Demo")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    for i in range(8):
        try:
            start_time = time.time()
            response = requests.get(f'{base_url}/')
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                remaining = data.get('requests_remaining', 'unknown')
                print(f"Request {i+1}: ✅ Success | Latency: {latency:.2f}ms | Remaining: {remaining}")
            elif response.status_code == 429:
                print(f"Request {i+1}: 🛡️  Rate Limited | Latency: {latency:.2f}ms")
                print("   ⚠️  Rate limit exceeded - working as expected!")
            else:
                print(f"Request {i+1}: ❓ Status {response.status_code}")
                
        except Exception as e:
            print(f"Request {i+1}: ❌ Error - {e}")
        
        time.sleep(0.5)

async def demo_concurrent_requests():
    """Demonstrate concurrent request handling"""
    print("\n🔄 Concurrent Requests Demo")
    print("=" * 40)
    
    async def make_request(session, url, request_id):
        start_time = time.time()
        try:
            async with session.get(url) as response:
                end_time = time.time()
                return {
                    'id': request_id,
                    'status': response.status,
                    'response_time': (end_time - start_time) * 1000,
                    'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3]
                }
        except Exception as e:
            return {'id': request_id, 'error': str(e)}

    url = "http://localhost:8000/sliding"
    concurrent_requests = 10
    
    async with aiohttp.ClientSession() as session:
        print(f"Launching {concurrent_requests} concurrent requests...")
        
        tasks = [make_request(session, url, i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        print("\nResults:")
        success_count = 0
        blocked_count = 0
        
        for result in results:
            status = result.get('status', 'ERROR')
            response_time = result.get('response_time', 0)
            timestamp = result.get('timestamp', 'unknown')
            
            if status == 200:
                success_count += 1
                print(f"  Request {result['id']}: ✅ {status} | {response_time:.1f}ms | {timestamp}")
            elif status == 429:
                blocked_count += 1
                print(f"  Request {result['id']}: 🛡️  {status} | {response_time:.1f}ms | {timestamp}")
            else:
                print(f"  Request {result['id']}: ❌ {result.get('error', status)}")
        
        print(f"\n📊 Summary: {success_count} successful, {blocked_count} blocked")
        if blocked_count > 0:
            print("✅ Rate limiting is working correctly!")

def demo_algorithm_comparison():
    """Compare different rate limiting algorithms"""
    print("\n🔬 Algorithm Comparison Demo")
    print("=" * 40)
    
    algorithms = {
        'fixed-window': 'Fixed Window (Simple Counter)',
        'atomic-fixed-window': 'Atomic Fixed Window (Race-Safe)',
        'sliding-window': 'Sliding Window (Smooth Limiting)'
    }
    
    base_url = "http://localhost:8000"
    
    for algo_endpoint, algo_name in algorithms.items():
        print(f"\n🧪 Testing {algo_name}:")
        
        success_count = 0
        blocked_count = 0
        total_latency = 0
        
        for i in range(7):  # Try 7 requests (limit is 5)
            try:
                start_time = time.time()
                response = requests.get(f'{base_url}/test/{algo_endpoint}')
                end_time = time.time()
                
                latency = (end_time - start_time) * 1000
                total_latency += latency
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"   Request {i+1}: ✅ OK ({latency:.1f}ms)")
                elif response.status_code == 429:
                    blocked_count += 1
                    print(f"   Request {i+1}: 🛡️  Blocked ({latency:.1f}ms)")
                    
                time.sleep(0.2)
                
            except Exception as e:
                print(f"   Request {i+1}: ❌ Error: {e}")
        
        avg_latency = total_latency / (success_count + blocked_count) if (success_count + blocked_count) > 0 else 0
        effectiveness = (blocked_count / (success_count + blocked_count)) * 100 if (success_count + blocked_count) > 0 else 0
        
        print(f"   📊 Results: {success_count} allowed, {blocked_count} blocked")
        print(f"   ⚡ Avg Latency: {avg_latency:.1f}ms")
        print(f"   🎯 Effectiveness: {effectiveness:.1f}%")

def demo_admin_features():
    """Demonstrate admin and monitoring features"""
    print("\n🔧 Admin Features Demo")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    try:
        # Check system health
        response = requests.get(f'{base_url}/health')
        if response.status_code == 200:
            health_data = response.json()
            print("✅ System Health:")
            print(f"   Redis Connected: {health_data.get('redis_connected', False)}")
            print(f"   Timestamp: {health_data.get('timestamp', 'unknown')}")
        
        # Get admin stats
        response = requests.get(f'{base_url}/admin/stats')
        if response.status_code == 200:
            stats = response.json()
            print("\n📊 System Statistics:")
            print(f"   Total Requests: {stats.get('total_requests', 0)}")
            print(f"   Blocked Requests: {stats.get('blocked_requests', 0)}")
            print(f"   Active Limits: {len(stats.get('active_limits', {}))}")
        
        # Check blocked IPs
        response = requests.get(f'{base_url}/admin/blocked-ips')
        if response.status_code == 200:
            blocked_ips = response.json()
            print(f"\n🚫 Blocked IPs: {len(blocked_ips.get('blocked_ips', []))}")
            
    except Exception as e:
        print(f"❌ Admin API Error: {e}")

def main():
    """Run all demo scenarios"""
    print("🎪 Rate Limiter Demo Suite")
    print("=" * 50)
    print("Make sure the rate limiter server is running:")
    print("cd backend && python -m uvicorn app.sliding_window_demo:app --reload")
    print("=" * 50)
    
    try:
        # Basic functionality
        demo_basic_rate_limiting()
        
        # Wait a moment for rate limits to reset
        print("\n⏳ Waiting for rate limits to reset...")
        time.sleep(3)
        
        # Algorithm comparison
        demo_algorithm_comparison()
        
        # Admin features
        demo_admin_features()
        
        # Concurrent requests (requires aiohttp)
        try:
            asyncio.run(demo_concurrent_requests())
        except ImportError:
            print("\n⚠️  Skipping concurrent demo (aiohttp not installed)")
            print("   Install with: pip install aiohttp")
        
        print("\n🎉 Demo Complete!")
        print("📊 Check the dashboard at: frontend/dashboard/index.html")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure the server is running on http://localhost:8000")

if __name__ == "__main__":
    main()