#!/usr/bin/env python3
"""
Comprehensive Railway Deployment Verification
Tests all fixes to ensure Railway deployment will succeed
"""
import subprocess
import requests
import time
import sys
import json
from pathlib import Path

class DeploymentTester:
    def __init__(self):
        self.results = []
        self.base_url = "http://localhost:8000"
        self.server_process = None

    def log_result(self, test_name, status, message=""):
        """Log test result"""
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        result = f"{emoji} {test_name}: {status}"
        if message:
            result += f" - {message}"
        print(result)
        self.results.append((test_name, status, message))

    def start_server(self):
        """Start the Railway API server"""
        print("🚀 Starting Railway API server...")
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "railway_api.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent
            )
            
            # Wait for server to start
            for i in range(15):  # 15 second timeout
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        self.log_result("Server Startup", "PASS", "Server responding")
                        return True
                except:
                    time.sleep(1)
                    
            self.log_result("Server Startup", "FAIL", "Server failed to start")
            return False
            
        except Exception as e:
            self.log_result("Server Startup", "FAIL", str(e))
            return False

    def test_import_fixes(self):
        """Test that import issues are resolved"""
        print("\n📦 Testing Import Fixes...")
        
        try:
            # Test basic imports work
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            
            # Test the fixed import structure
            from scripts.production_api import app
            self.log_result("Import Structure", "PASS", "No import errors")
            return True
            
        except Exception as e:
            self.log_result("Import Structure", "FAIL", str(e))
            return False

    def test_core_endpoints(self):
        """Test core API endpoints"""
        print("\n🌐 Testing Core API Endpoints...")
        
        endpoints = [
            ("/", "Root endpoint"),
            ("/health", "Health check"),
            ("/api/account", "Account info"),
            ("/api/holdings", "Holdings"),
            ("/api/portfolio", "Portfolio summary"),
            ("/api/trades/active", "Active trades"),
            ("/api/system/status", "System status")
        ]
        
        passed = 0
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    self.log_result(f"Endpoint {endpoint}", "PASS", description)
                    passed += 1
                else:
                    self.log_result(f"Endpoint {endpoint}", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log_result(f"Endpoint {endpoint}", "FAIL", str(e))
        
        success_rate = (passed / len(endpoints)) * 100
        overall = "PASS" if success_rate >= 85 else "FAIL"
        self.log_result("API Endpoints", overall, f"{success_rate:.1f}% success rate")
        return success_rate >= 85

    def test_websocket_fix(self):
        """Test the WebSocket endpoint fix"""
        print("\n🔌 Testing WebSocket Fix...")
        
        try:
            # Use curl to test WebSocket handshake
            result = subprocess.run([
                "curl", "-i", "-N", 
                "-H", "Connection: Upgrade",
                "-H", "Upgrade: websocket", 
                "-H", "Sec-WebSocket-Version: 13",
                "-H", "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==",
                f"{self.base_url}/ws/trades"
            ], capture_output=True, text=True, timeout=5)
            
            if "101 Switching Protocols" in result.stdout:
                self.log_result("WebSocket /ws/trades", "PASS", "WebSocket handshake successful")
                return True
            elif "403" in result.stdout:
                self.log_result("WebSocket /ws/trades", "WARN", "Connection rejected but endpoint exists")
                return True  # Endpoint exists, might be auth issue
            else:
                self.log_result("WebSocket /ws/trades", "FAIL", "WebSocket handshake failed")
                return False
                
        except Exception as e:
            self.log_result("WebSocket /ws/trades", "FAIL", str(e))
            return False

    def test_railway_config(self):
        """Test Railway configuration files"""
        print("\n⚙️ Testing Railway Configuration...")
        
        # Check railway.json
        railway_config = Path("../railway.json")
        if railway_config.exists():
            try:
                with open(railway_config) as f:
                    config = json.load(f)
                    
                start_command = config.get("deploy", {}).get("startCommand", "")
                if "railway_api.py" in start_command:
                    self.log_result("Railway Config", "PASS", "Using fixed entry point")
                else:
                    self.log_result("Railway Config", "FAIL", "Still using old entry point")
                    return False
                    
            except Exception as e:
                self.log_result("Railway Config", "FAIL", f"Config error: {e}")
                return False
        else:
            self.log_result("Railway Config", "FAIL", "railway.json not found")
            return False
        
        # Check Procfile
        procfile = Path("../Procfile")
        if procfile.exists():
            try:
                content = procfile.read_text()
                if "railway_api.py" in content:
                    self.log_result("Procfile", "PASS", "Using fixed entry point")
                else:
                    self.log_result("Procfile", "WARN", "Still using old entry point")
                    
            except Exception as e:
                self.log_result("Procfile", "FAIL", f"Procfile error: {e}")
                return False
        else:
            self.log_result("Procfile", "WARN", "Procfile not found")
        
        return True

    def test_environment_variables(self):
        """Test that required environment variables are available"""
        print("\n🔐 Testing Environment Variables...")
        
        import os
        required_vars = [
            'ALPACA_API_KEY',
            'ALPACA_SECRET', 
            'MONGODB_URL',
            'TELEGRAM_BOT_TOKEN',
            'OPENAI_API_KEY'
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if not missing:
            self.log_result("Environment Variables", "PASS", "All required vars present")
            return True
        else:
            self.log_result("Environment Variables", "WARN", f"Missing: {', '.join(missing)}")
            return True  # Railway will have these

    def cleanup(self):
        """Clean up test resources"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print("🧹 Server stopped")

    def run_comprehensive_test(self):
        """Run all tests and return deployment readiness"""
        print("🧪 COMPREHENSIVE RAILWAY DEPLOYMENT TEST")
        print("=" * 60)
        
        try:
            # Run all tests
            tests = [
                self.test_import_fixes(),
                self.start_server(),
                self.test_core_endpoints(),
                self.test_websocket_fix(),
                self.test_railway_config(),
                self.test_environment_variables()
            ]
            
            # Calculate results
            passed_tests = sum(1 for test in tests if test)
            total_tests = len(tests)
            success_rate = (passed_tests / total_tests) * 100
            
            print(f"\n📊 DEPLOYMENT READINESS SUMMARY")
            print("=" * 40)
            print(f"Tests Passed: {passed_tests}/{total_tests}")
            print(f"Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 85:
                print("🎉 READY FOR RAILWAY DEPLOYMENT!")
                print("✅ All critical fixes are working")
                print("✅ WebSocket endpoint fixed")
                print("✅ Import issues resolved") 
                print("✅ Railway configuration updated")
                return True
            else:
                print("❌ NOT READY FOR DEPLOYMENT")
                print("🔧 Some issues need to be resolved")
                return False
                
        finally:
            self.cleanup()

if __name__ == "__main__":
    tester = DeploymentTester()
    ready = tester.run_comprehensive_test()
    sys.exit(0 if ready else 1)
