"""
Advanced Load Testing Scenarios for Rate Limiter
===============================================
This script runs predefined test scenarios to validate different aspects
of the rate limiter system.
"""

import subprocess
import time
import sys
import json
import requests
from datetime import datetime

class RateLimiterTestRunner:
    def __init__(self, host="http://localhost:8000"):
        self.host = host
        self.results = {}
    
    def check_server_health(self):
        """Check if the rate limiter server is running"""
        try:
            response = requests.get(f"{self.host}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def run_scenario(self, name, users, spawn_rate, run_time, description):
        """Run a specific load test scenario"""
        print(f"\n🚀 Running Scenario: {name}")
        print(f"📄 Description: {description}")
        print(f"👥 Users: {users}, Spawn Rate: {spawn_rate}/s, Duration: {run_time}s")
        print("-" * 60)
        
        cmd = [
            "locust", 
            "-f", "locustfile.py",
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", f"{run_time}s",
            "--headless",
            "--html", f"results_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=run_time + 30)
            duration = time.time() - start_time
            
            self.results[name] = {
                "duration": duration,
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
            
            if result.returncode == 0:
                print(f"✅ Scenario '{name}' completed successfully in {duration:.1f}s")
            else:
                print(f"❌ Scenario '{name}' failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            print(f"⏰ Scenario '{name}' timed out")
            self.results[name] = {"duration": run_time, "success": False, "error": "timeout"}
    
    def run_all_scenarios(self):
        """Run all predefined test scenarios"""
        print("🔥 Starting Comprehensive Rate Limiter Load Testing")
        print(f"🎯 Target Host: {self.host}")
        print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.check_server_health():
            print(f"❌ Server health check failed! Make sure {self.host} is running.")
            return False
        
        scenarios = [
            {
                "name": "light_load",
                "users": 10,
                "spawn_rate": 2,
                "run_time": 60,
                "description": "Light load to establish baseline performance"
            },
            {
                "name": "moderate_load", 
                "users": 50,
                "spawn_rate": 5,
                "run_time": 120,
                "description": "Moderate load to test normal operating conditions"
            },
            {
                "name": "burst_traffic",
                "users": 100,
                "spawn_rate": 20,
                "run_time": 60,
                "description": "Burst traffic to test rapid scaling and rate limiting"
            },
            {
                "name": "sustained_high_load",
                "users": 200,
                "spawn_rate": 10,
                "run_time": 180,
                "description": "Sustained high load to test system stability"
            },
            {
                "name": "stress_test",
                "users": 500,
                "spawn_rate": 25,
                "run_time": 120,
                "description": "Stress test to find breaking point"
            }
        ]
        
        for scenario in scenarios:
            self.run_scenario(**scenario)
            
            # Cool down between scenarios
            if scenario != scenarios[-1]:  # Don't wait after the last scenario
                print("⏱️  Cooling down for 30 seconds...")
                time.time.sleep(30)
        
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print summary of all test results"""
        print("\n" + "="*80)
        print("📊 LOAD TESTING SUMMARY")
        print("="*80)
        
        successful_scenarios = 0
        total_scenarios = len(self.results)
        
        for name, result in self.results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            duration = result.get("duration", 0)
            print(f"{status} | {name.ljust(20)} | Duration: {duration:.1f}s")
            
            if result["success"]:
                successful_scenarios += 1
        
        print("-" * 80)
        success_rate = (successful_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0
        print(f"Success Rate: {success_rate:.1f}% ({successful_scenarios}/{total_scenarios})")
        
        if success_rate >= 80:
            print("🎉 Overall Result: EXCELLENT - Rate limiter performed well under load!")
        elif success_rate >= 60:
            print("⚠️  Overall Result: GOOD - Some scenarios failed, investigate further")
        else:
            print("🚨 Overall Result: POOR - Multiple failures, system needs attention")
        
        print("="*80)

def main():
    """Main function to run test scenarios"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run rate limiter load test scenarios")
    parser.add_argument("--host", default="http://localhost:8000", help="Rate limiter host URL")
    parser.add_argument("--scenario", help="Run specific scenario only")
    
    args = parser.parse_args()
    
    runner = RateLimiterTestRunner(args.host)
    
    if args.scenario:
        # Run specific scenario (you'd implement this)
        print(f"Running specific scenario: {args.scenario}")
    else:
        # Run all scenarios
        success = runner.run_all_scenarios()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()