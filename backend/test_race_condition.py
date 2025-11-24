import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
import threading


class RaceConditionTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
    
    async def make_request(self, session, request_id):
        """Make a single request and record the result"""
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}/test") as response:
                data = await response.json()
                end_time = time.time()
                
                with self.lock:
                    self.results.append({
                        "id": request_id,
                        "status": response.status,
                        "duration": end_time - start_time,
                        "count": data.get("rate_limit", {}).get("current_count", "N/A"),
                        "timestamp": start_time
                    })
        except Exception as e:
            end_time = time.time()
            with self.lock:
                self.results.append({
                    "id": request_id,
                    "status": "ERROR",
                    "duration": end_time - start_time,
                    "count": "ERROR",
                    "error": str(e),
                    "timestamp": start_time
                })
    
    async def concurrent_test(self, num_requests=10):
        """Send multiple requests concurrently to test for race conditions"""
        print(f"🏃‍♀️ Sending {num_requests} concurrent requests...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_requests):
                task = asyncio.create_task(self.make_request(session, i+1))
                tasks.append(task)
            
            # Send all requests at once
            await asyncio.gather(*tasks)
        
        return self.results
    
    def analyze_results(self):
        """Analyze the results for race condition issues"""
        print("\n📊 Race Condition Analysis:")
        print("=" * 60)
        
        success_count = len([r for r in self.results if r["status"] == 200])
        blocked_count = len([r for r in self.results if r["status"] == 429])
        error_count = len([r for r in self.results if r["status"] == "ERROR"])
        
        print(f"✅ Successful requests: {success_count}")
        print(f"🚫 Rate limited requests: {blocked_count}")
        print(f"❌ Error requests: {error_count}")
        
        # Check for race condition indicators
        successful_results = [r for r in self.results if r["status"] == 200]
        if successful_results:
            counts = [r["count"] for r in successful_results if r["count"] != "N/A"]
            max_count = max(counts) if counts else 0
            
            print(f"\n🔍 Race Condition Check:")
            print(f"Maximum counter reached: {max_count}")
            
            if max_count > 5:
                print("⚠️  RACE CONDITION DETECTED! More than 5 requests succeeded.")
                print("   This should not happen with proper atomic operations.")
            else:
                print("✅ No race condition detected. Atomic operations working correctly.")
        
        print("\n📝 Detailed Results:")
        for result in sorted(self.results, key=lambda x: x["timestamp"]):
            status_emoji = "✅" if result["status"] == 200 else "🚫" if result["status"] == 429 else "❌"
            print(f"{status_emoji} Request {result['id']}: Status {result['status']}, Count: {result['count']}")


async def main():
    print("🧪 Testing Atomic Rate Limiter for Race Conditions")
    print("=" * 60)
    print("This test sends multiple concurrent requests to check if the atomic")
    print("implementation prevents race conditions that could allow more than")
    print("the allowed number of requests to pass through.")
    print()
    
    tester = RaceConditionTester()
    
    try:
        # Test with many concurrent requests
        await tester.concurrent_test(num_requests=15)
        tester.analyze_results()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure the server is running: python -m app.main_atomic")


if __name__ == "__main__":
    # Install required package if not present
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp for async testing...")
        import subprocess
        subprocess.check_call(["pip", "install", "aiohttp"])
        import aiohttp
    
    asyncio.run(main())