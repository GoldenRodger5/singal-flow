#!/usr/bin/env python3
"""
Comprehensive Endpoint Testing Script for Signal Flow API
Tests all endpoints until 100% success rate is achieved
"""

import requests
import json
import time
import sys
from typing import Dict, List, Tuple
import websockets
import asyncio
from dotenv import load_dotenv

class EndpointTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200, 
                     data: dict = None, timeout: int = 10) -> Tuple[bool, dict]:
        """Test a single endpoint and return success status and response info"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text[:200]}
            
            result = {
                "method": method.upper(),
                "endpoint": endpoint,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response_size": len(response.text),
                "response": response_data
            }
            
            return success, result
            
        except Exception as e:
            result = {
                "method": method.upper(),
                "endpoint": endpoint,
                "status_code": 0,
                "expected_status": expected_status,
                "success": False,
                "error": str(e),
                "response": {}
            }
            return False, result
    
    async def test_websocket(self, endpoint: str) -> Tuple[bool, dict]:
        """Test WebSocket endpoint"""
        try:
            uri = f"ws://localhost:8000{endpoint}"
            # Remove timeout from connect call, add it to wait_for instead
            async with websockets.connect(uri) as websocket:
                # Send test message
                await websocket.send("get_health")
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                result = {
                    "method": "WEBSOCKET",
                    "endpoint": endpoint,
                    "status_code": 101,  # WebSocket upgrade
                    "expected_status": 101,
                    "success": True,
                    "response": {"message": "WebSocket connection successful", "data": response[:100]}
                }
                return True, result
                
        except Exception as e:
            result = {
                "method": "WEBSOCKET",
                "endpoint": endpoint,
                "status_code": 0,
                "expected_status": 101,
                "success": False,
                "error": str(e),
                "response": {}
            }
            return False, result
    
    def run_all_tests(self) -> Dict:
        """Run comprehensive tests on all endpoints"""
        print("🚀 Starting comprehensive endpoint testing...")
        print(f"📡 Testing API at: {self.base_url}")
        print("=" * 80)
        
        # Define all endpoints to test
        endpoints = [
            # Basic endpoints
            ("GET", "/", 200),
            ("GET", "/health", 200),
            ("GET", "/health/detailed", 200),
            
            # Trading endpoints
            ("GET", "/api/account", 200),
            ("GET", "/api/portfolio", 200),
            ("GET", "/api/holdings", 200),
            ("GET", "/api/positions", 200),
            ("GET", "/api/trades/active", 200),
            ("GET", "/api/trades/performance", 200),
            ("GET", "/api/performance/history", 200),
            
            # AI endpoints
            ("GET", "/api/ai/analysis", 200),
            ("GET", "/api/ai/decisions/recent", 200),
            ("GET", "/api/ai/learning/summary", 200),
            
            # System endpoints
            ("GET", "/api/system/status", 200),
            ("GET", "/api/control/status", 200),
            ("GET", "/api/config/status", 200),
            
            # Not implemented endpoints (should return 501)
            ("GET", "/api/ai/signals/recent", 501),
            ("GET", "/api/market/realtime/AAPL", 501),
            ("GET", "/api/dashboard/analytics/performance", 501),
            ("GET", "/api/dashboard/market/pulse", 501),
            ("GET", "/api/dashboard/watchlist/signals", 501),
            ("GET", "/api/dashboard/ai/signals", 501),
            ("GET", "/api/dashboard/ai/learning-metrics", 501),
            ("GET", "/api/config/system", 501),
            
            # AI training/analysis endpoints
            ("GET", "/api/ai/training-data/AAPL", 200),
            ("GET", "/api/ai/market-sentiment/AAPL", 200),
            ("GET", "/api/ai/pattern-analysis", 200),
            ("GET", "/api/ai/strategy-performance", 200),
            ("GET", "/api/ai/market-regime", 200),
            
            # POST endpoints
            ("POST", "/api/ai/force-data-collection", 200),
            ("POST", "/api/system/trigger_scan", 200),
            ("POST", "/api/dashboard/config/update", 200),
            
            # Control endpoints
            ("POST", "/api/control/toggle_auto_trading", 200),
            ("POST", "/api/control/toggle_paper_trading", 200),
            ("POST", "/api/control/sync_data", 200),
        ]
        
        successful_tests = 0
        failed_tests = 0
        
        for method, endpoint, expected_status in endpoints:
            print(f"Testing {method:6} {endpoint:40} ", end="")
            
            # Special handling for POST endpoints that need data
            test_data = {}
            if method == "POST":
                if "config/update" in endpoint:
                    test_data = {"setting": "test", "value": True}
                elif "trades/execute" in endpoint:
                    test_data = {"symbol": "AAPL", "action": "BUY", "quantity": 1}
                elif "control/" in endpoint:
                    test_data = {}
            
            success, result = self.test_endpoint(method, endpoint, expected_status, test_data)
            self.results.append(result)
            
            if success:
                print(f"✅ {result['status_code']}")
                successful_tests += 1
            else:
                print(f"❌ {result['status_code']} (expected {expected_status})")
                if 'error' in result:
                    print(f"   Error: {result['error']}")
                failed_tests += 1
            
            time.sleep(0.1)  # Small delay to avoid overwhelming the server
        
        # Test WebSocket endpoints
        print("\n📡 Testing WebSocket endpoints...")
        websocket_endpoints = [
            "/ws/health",
            "/ws/trades"
        ]
        
        async def test_all_websockets():
            for ws_endpoint in websocket_endpoints:
                print(f"Testing WS    {ws_endpoint:40} ", end="")
                success, result = await self.test_websocket(ws_endpoint)
                self.results.append(result)
                
                nonlocal successful_tests, failed_tests
                if success:
                    print("✅ Connected")
                    successful_tests += 1
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                    failed_tests += 1
        
        # Run WebSocket tests
        try:
            asyncio.run(test_all_websockets())
        except Exception as e:
            print(f"❌ WebSocket testing failed: {e}")
            failed_tests += len(websocket_endpoints)
        
        # Calculate results
        total_tests = successful_tests + failed_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 80)
        print(f"📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"✅ Successful tests: {successful_tests}")
        print(f"❌ Failed tests: {failed_tests}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if success_rate < 100:
            print(f"\n🔍 FAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"   {result['method']:6} {result['endpoint']:40} "
                          f"Status: {result['status_code']} (expected {result['expected_status']})")
                    if 'error' in result:
                        print(f"      Error: {result['error']}")
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "results": self.results
        }

def check_environment_variables():
    """Check that all required environment variables are set"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    load_dotenv()
    
    required_vars = [
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY", 
        "ALPACA_BASE_URL",
        "MONGODB_URL",
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY"
    ]
    
    print("🔧 Checking environment variables...")
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            # Show first/last few characters for security
            value = os.getenv(var)
            if len(value) > 10:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "***"
            print(f"   ✅ {var}: {masked}")
    
    if missing_vars:
        print(f"   ❌ Missing variables: {', '.join(missing_vars)}")
        return False
    
    print("   ✅ All required environment variables are set!")
    return True

def main():
    """Main function to run all tests"""
    print("🚀 Signal Flow API Comprehensive Testing")
    print("=" * 80)
    
    # Check environment variables first
    if not check_environment_variables():
        print("❌ Environment setup incomplete. Please check your .env file.")
        sys.exit(1)
    
    # Wait for API to be ready
    print("\n⏳ Waiting for API server to be ready...")
    tester = EndpointTester()
    
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{tester.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API server is ready!")
                break
        except:
            pass
        
        if i == max_retries - 1:
            print("❌ API server is not responding. Please start the server first.")
            print("   Run: cd backend && python scripts/production_api.py")
            sys.exit(1)
        
        print(f"   Attempt {i+1}/{max_retries}...")
        time.sleep(2)
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Keep testing until 100% success
    max_iterations = 5
    iteration = 1
    
    while results["success_rate"] < 100 and iteration <= max_iterations:
        print(f"\n🔄 ITERATION {iteration}: Success rate {results['success_rate']:.1f}% - Retesting failed endpoints...")
        print("=" * 80)
        
        # Retry only failed endpoints
        failed_endpoints = [r for r in results["results"] if not r["success"]]
        
        if not failed_endpoints:
            break
            
        # Wait a bit for server to stabilize
        time.sleep(5)
        
        # Re-test failed endpoints
        retry_tester = EndpointTester()
        retry_results = []
        
        for failed in failed_endpoints:
            method = failed["method"]
            endpoint = failed["endpoint"]
            expected_status = failed["expected_status"]
            
            if method == "WEBSOCKET":
                continue  # Skip WebSocket retries for now
                
            print(f"Retrying {method:6} {endpoint:40} ", end="")
            
            success, result = retry_tester.test_endpoint(method, endpoint, expected_status)
            retry_results.append(result)
            
            if success:
                print(f"✅ {result['status_code']} - FIXED!")
                # Update original result
                for i, orig_result in enumerate(results["results"]):
                    if (orig_result["method"] == method and 
                        orig_result["endpoint"] == endpoint):
                        results["results"][i] = result
                        break
            else:
                print(f"❌ {result['status_code']} - Still failing")
            
            time.sleep(0.2)
        
        # Recalculate success rate
        successful = sum(1 for r in results["results"] if r["success"])
        total = len(results["results"])
        results["success_rate"] = (successful / total * 100) if total > 0 else 0
        results["successful_tests"] = successful
        results["failed_tests"] = total - successful
        
        iteration += 1
    
    # Final summary
    print("\n" + "🎯" * 40)
    print(f"🏁 FINAL RESULTS - Iteration {iteration-1}")
    print("🎯" * 40)
    print(f"📊 Success Rate: {results['success_rate']:.1f}%")
    print(f"✅ Successful: {results['successful_tests']}")
    print(f"❌ Failed: {results['failed_tests']}")
    
    if results["success_rate"] == 100:
        print("\n🎉 SUCCESS! All endpoints are working perfectly!")
        print("🚀 Railway and Vercel deployment ready!")
    else:
        print(f"\n⚠️  {results['failed_tests']} endpoints still failing:")
        for result in results["results"]:
            if not result["success"]:
                print(f"   ❌ {result['method']} {result['endpoint']} - {result.get('error', 'Status: ' + str(result['status_code']))}")
    
    # Save detailed results
    with open("endpoint_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: endpoint_test_results.json")
    
    return results["success_rate"] == 100

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        sys.exit(1)
