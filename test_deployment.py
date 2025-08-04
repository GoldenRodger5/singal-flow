#!/usr/bin/env python3
"""
Quick deployment test script
"""
import requests
import time
import json

# Railway URL
RAILWAY_URL = "https://web-production-3e19d.up.railway.app"

def test_deployment():
    """Test the Railway deployment"""
    print("🧪 Testing Signal Flow Railway Deployment...")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check: PASS")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check: FAIL ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Health check: ERROR - {e}")
        return False
    
    # Test 2: System status
    print("\n2. Testing system status...")
    try:
        response = requests.get(f"{RAILWAY_URL}/api/system/status", timeout=15)
        if response.status_code == 200:
            print("✅ System status: PASS")
            data = response.json()
            print(f"   Health: {data.get('health', {}).get('status', 'unknown')}")
            print(f"   Active trades: {data.get('active_trades_count', 0)}")
        else:
            print(f"❌ System status: FAIL ({response.status_code})")
            if response.status_code == 404:
                print("   This might indicate old deployment is still running")
    except Exception as e:
        print(f"❌ System status: ERROR - {e}")
    
    # Test 3: Manual scan trigger
    print("\n3. Testing manual market scan trigger...")
    try:
        response = requests.post(f"{RAILWAY_URL}/api/system/trigger_scan", timeout=15)
        if response.status_code == 200:
            print("✅ Manual scan trigger: PASS")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Manual scan trigger: FAIL ({response.status_code})")
            if response.status_code == 404:
                print("   This indicates the new API endpoints are not available yet")
    except Exception as e:
        print(f"❌ Manual scan trigger: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print("Test completed. If you see failures, the deployment needs to be updated.")
    return True

if __name__ == "__main__":
    test_deployment()
