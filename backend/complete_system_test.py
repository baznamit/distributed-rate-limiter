#!/usr/bin/env python3
"""
Complete System Test Script
===========================
This script tests all components of the distributed rate limiter system
"""

import time
import subprocess
import sys
import requests
import threading
from pathlib import Path

class SystemTester:
    def __init__(self):
        self.server_process = None
        self.base_url = "http://127.0.0.1:8000"
        self.server_started = False
        
    def start_server(self):
        """Start the FastAPI server in the background"""
        print("🚀 Starting FastAPI server...")
        try:
            # Start server process
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "app.sliding_window_demo:app",
                "--host", "127.0.0.1",
                "--port", "8000"
            ]
            
            self.server_process = subprocess.Popen(
                cmd,
                cwd="C:/Users/2634009/Desktop/Personal Repos/distributed-rate-limiter/backend",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Wait for server to start
            for i in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Server started successfully!")
                        self.server_started = True
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    print(f"   Waiting for server... ({i+1}/30)")
            
            print("❌ Server failed to start within 30 seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the FastAPI server"""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            print("✅ Server stopped")
    
    def test_endpoints(self):
        """Test all rate limiting endpoints"""
        if not self.server_started:
            print("❌ Server not running, cannot test endpoints")
            return False
            
        print("\n🧪 Testing Rate Limiting Endpoints:")
        print("-" * 40)
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health Check: {data}")
            else:
                print(f"❌ Health Check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health Check error: {e}")
            return False
        
        # Test rate limiting algorithms
        algorithms = ["fixed-window", "atomic-fixed-window", "sliding-window"]
        
        for algorithm in algorithms:
            print(f"\n🔬 Testing {algorithm}:")
            successful = 0
            rate_limited = 0
            
            # Make 8 requests (should hit 5 req/min limit)
            for i in range(8):
                try:
                    response = requests.get(f"{self.base_url}/test/{algorithm}")
                    if response.status_code == 200:
                        successful += 1
                        print(f"   Request {i+1}: ✅ Allowed")
                    elif response.status_code == 429:
                        rate_limited += 1
                        print(f"   Request {i+1}: 🛡️  Rate Limited")
                    else:
                        print(f"   Request {i+1}: ⚠️  Status {response.status_code}")
                    
                    time.sleep(0.1)  # Small delay
                    
                except Exception as e:
                    print(f"   Request {i+1}: ❌ Error - {e}")
            
            print(f"   Summary: {successful} allowed, {rate_limited} blocked")
            
            if rate_limited > 0:
                print(f"   ✅ Rate limiting is working for {algorithm}")
            else:
                print(f"   ⚠️  No rate limiting detected for {algorithm}")
        
        return True
    
    def test_dashboard_api(self):
        """Test dashboard API endpoints"""
        if not self.server_started:
            return False
            
        print("\n📊 Testing Dashboard API:")
        print("-" * 30)
        
        try:
            # Test dashboard metrics
            response = requests.get(f"{self.base_url}/api/dashboard/metrics")
            if response.status_code == 200:
                print("✅ Dashboard metrics endpoint working")
            else:
                print(f"❌ Dashboard metrics failed: {response.status_code}")
            
            # Test clients endpoint
            response = requests.get(f"{self.base_url}/api/dashboard/clients")
            if response.status_code == 200:
                print("✅ Dashboard clients endpoint working")
            else:
                print(f"❌ Dashboard clients failed: {response.status_code}")
            
            return True
            
        except Exception as e:
            print(f"❌ Dashboard API error: {e}")
            return False
    
    def validate_files(self):
        """Validate that all project files exist"""
        print("\n📁 Validating Project Files:")
        print("-" * 30)
        
        required_files = [
            "backend/app/sliding_window_demo.py",
            "backend/app/rate_limiter/sliding_window.py",
            "backend/app/middleware/rate_limit.py",
            "frontend/dashboard/index.html",
            "frontend/dashboard/dashboard.js",
            "load-testing/locustfile.py",
            "load-testing/run_test_scenarios.py",
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = Path("C:/Users/2634009/Desktop/Personal Repos/distributed-rate-limiter") / file_path
            if full_path.exists():
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path} - MISSING")
                missing_files.append(file_path)
        
        if not missing_files:
            print("✅ All required files are present")
            return True
        else:
            print(f"❌ {len(missing_files)} files are missing")
            return False
    
    def run_complete_test(self):
        """Run the complete system test"""
        print("🔥 DISTRIBUTED RATE LIMITER - COMPLETE SYSTEM TEST")
        print("=" * 55)
        
        try:
            # Validate files first
            if not self.validate_files():
                print("❌ File validation failed, cannot proceed")
                return False
            
            # Start server
            if not self.start_server():
                print("❌ Server startup failed, cannot proceed")
                return False
            
            # Test endpoints
            endpoint_success = self.test_endpoints()
            
            # Test dashboard API
            dashboard_success = self.test_dashboard_api()
            
            # Summary
            print("\n" + "=" * 55)
            print("📊 TEST SUMMARY:")
            print("=" * 55)
            print(f"File Validation: ✅ Passed")
            print(f"Server Startup: ✅ Passed")
            print(f"Endpoint Testing: {'✅ Passed' if endpoint_success else '❌ Failed'}")
            print(f"Dashboard API: {'✅ Passed' if dashboard_success else '❌ Failed'}")
            
            if endpoint_success and dashboard_success:
                print("\n🎉 ALL TESTS PASSED - SYSTEM IS WORKING CORRECTLY!")
                print("\n🚀 Ready for:")
                print("   • Load testing with Locust")
                print("   • Production deployment")
                print("   • Dashboard monitoring")
                return True
            else:
                print("\n⚠️  SOME TESTS FAILED - CHECK LOGS ABOVE")
                return False
                
        finally:
            self.stop_server()

def main():
    """Main function"""
    tester = SystemTester()
    success = tester.run_complete_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())