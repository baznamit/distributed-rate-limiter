import requests
import time
import json

def test_rate_limiter():
    """Test the fixed window rate limiter"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Fixed Window Rate Limiter")
    print("=" * 50)
    
    # Test the /test endpoint multiple times
    print("Making 7 requests quickly to test rate limiting...")
    
    for i in range(7):
        try:
            response = requests.get(f"{base_url}/test")
            print(f"Request {i+1}: Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                rate_limit = data.get("rate_limit", {})
                print(f"  Current: {rate_limit.get('current_count', 'N/A')}, "
                      f"Remaining: {rate_limit.get('remaining', 'N/A')}")
            elif response.status_code == 429:
                data = response.json()
                print(f"  RATE LIMITED! Retry after: {data.get('retry_after', 'N/A')} seconds")
                
            # Check headers
            headers = response.headers
            if "X-RateLimit-Limit" in headers:
                print(f"  Headers: Limit={headers['X-RateLimit-Limit']}, "
                      f"Remaining={headers.get('X-RateLimit-Remaining', 'N/A')}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request {i+1}: ERROR - {e}")
        
        # Small delay between requests
        time.sleep(0.1)
    
    print("\n" + "=" * 50)
    print("Test completed! Expected behavior:")
    print("- First 5 requests: Status 200 (allowed)")
    print("- Requests 6-7: Status 429 (rate limited)")

if __name__ == "__main__":
    test_rate_limiter()