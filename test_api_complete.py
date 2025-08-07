#!/usr/bin/env python3
"""
Test API Endpoints - Verify all new endpoints work correctly
"""
import requests
import json
import time
import sys
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, data=None, expected_fields=None):
    """Test an API endpoint."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        print(f"\n🧪 Testing {method} {endpoint}")
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"   Success: {json_data.get('success', 'N/A')}")
                
                if expected_fields:
                    for field in expected_fields:
                        if field in json_data:
                            print(f"   ✅ {field}: Found")
                        else:
                            print(f"   ❌ {field}: Missing")
                
                # Show data summary
                if 'predictions' in json_data:
                    print(f"   📊 Predictions: {len(json_data.get('predictions', []))}")
                elif 'holdings' in json_data:
                    print(f"   💼 Holdings: {len(json_data.get('holdings', []))}")
                elif 'message' in json_data:
                    print(f"   💬 Message: {json_data['message']}")
                
                return True
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response")
                return False
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Error: {response.text[:100]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False

def main():
    """Run all API tests."""
    print("🚀 Testing Signal Flow API Endpoints")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server health check failed")
            return
    except:
        print("❌ Server is not running. Start with: python backend/scripts/production_api.py")
        return
    
    # Test AI Predictions endpoints
    print("\n📊 AI PREDICTIONS ENDPOINTS")
    print("-" * 30)
    
    test_endpoint("GET", "/api/ai/predictions", 
                 expected_fields=["success", "predictions", "summary", "performance"])
    
    test_endpoint("GET", "/api/ai/predictions/top?limit=5",
                 expected_fields=["success", "predictions", "count"])
    
    test_endpoint("GET", "/api/ai/predictions/AAPL",
                 expected_fields=["success"])
    
    test_endpoint("GET", "/api/ai/predictions/signals/high-confidence?min_confidence=7.0",
                 expected_fields=["success", "signals", "count"])
    
    # Test Portfolio endpoints
    print("\n💼 PORTFOLIO ENDPOINTS")
    print("-" * 30)
    
    test_endpoint("GET", "/api/portfolio/holdings",
                 expected_fields=["success", "holdings", "summary"])
    
    test_endpoint("GET", "/api/portfolio/summary",
                 expected_fields=["success", "summary"])
    
    test_endpoint("GET", "/api/portfolio/allocation",
                 expected_fields=["success", "allocation"])
    
    test_endpoint("GET", "/api/portfolio/position/AAPL",
                 expected_fields=["success"])
    
    # Test Account endpoints
    print("\n💰 ACCOUNT ENDPOINTS")
    print("-" * 30)
    
    test_endpoint("GET", "/api/account/summary",
                 expected_fields=["success", "account"])
    
    # Test Trading Control endpoints (non-destructive)
    print("\n🎛️ TRADING CONTROL ENDPOINTS")
    print("-" * 30)
    
    # Test pause/resume (should work even if already paused/resumed)
    test_endpoint("POST", "/api/trading/pause",
                 expected_fields=["success", "message"])
    
    time.sleep(1)  # Brief pause
    
    test_endpoint("POST", "/api/trading/resume",
                 expected_fields=["success", "message"])
    
    # Test market scan trigger
    test_endpoint("POST", "/api/trading/scan",
                 expected_fields=["success", "message"])
    
    # Test notification
    test_endpoint("POST", "/api/notifications/test",
                 expected_fields=["success", "message"])
    
    # Test buy order (with small amount)
    print("\n⚠️  TESTING BUY ORDER (SMALL AMOUNT)")
    test_endpoint("POST", "/api/trading/buy",
                 data={"ticker": "AAPL", "amount": 100},
                 expected_fields=["success"])
    
    print("\n" + "=" * 50)
    print("🏁 API Testing Complete")
    print("\nNext Steps:")
    print("1. Check any failed endpoints")
    print("2. Update frontend to use these endpoints")
    print("3. Test WebSocket connections")
    print("4. Deploy to production")

if __name__ == "__main__":
    main()
