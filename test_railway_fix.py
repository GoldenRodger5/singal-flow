#!/usr/bin/env python3
"""
Railway Deployment Test Script
Tests the new Railway entry point to ensure it works correctly
"""
import requests
import time
import subprocess
import sys
from pathlib import Path

def test_railway_deployment():
    """Test the Railway deployment entry point"""
    print("🧪 Testing Railway Deployment Fix")
    print("=" * 50)
    
    # Start the server
    backend_path = Path(__file__).parent / "backend"
    process = subprocess.Popen(
        [sys.executable, "railway_api.py"],
        cwd=backend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    print("⏳ Starting server...")
    time.sleep(10)
    
    try:
        base_url = "http://localhost:8000"
        
        # Test endpoints
        endpoints_to_test = [
            ("/", "Root endpoint"),
            ("/health", "Health check"),
            ("/api/account", "Account info"),
            ("/api/holdings", "Holdings"),
            ("/api/portfolio", "Portfolio"),
            ("/api/trades/active", "Active trades")
        ]
        
        results = []
        for endpoint, description in endpoints_to_test:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    results.append(f"✅ {endpoint} ({description}): OK")
                else:
                    results.append(f"⚠️ {endpoint} ({description}): Status {response.status_code}")
            except requests.exceptions.RequestException as e:
                results.append(f"❌ {endpoint} ({description}): {e}")
        
        # Print results
        print("\n📊 Test Results:")
        for result in results:
            print(result)
        
        # Calculate success rate
        successful = len([r for r in results if r.startswith("✅")])
        total = len(results)
        success_rate = (successful / total) * 100
        
        print(f"\n🎯 Success Rate: {success_rate:.1f}% ({successful}/{total})")
        
        if success_rate >= 80:
            print("🎉 Railway deployment fix is working!")
            return True
        else:
            print("❌ Railway deployment needs more fixes")
            return False
            
    finally:
        # Clean up
        process.terminate()
        process.wait()
        print("🧹 Server stopped")

if __name__ == "__main__":
    success = test_railway_deployment()
    sys.exit(0 if success else 1)
