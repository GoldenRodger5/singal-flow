#!/usr/bin/env python3
import requests
import json
import time

def test_api_endpoints():
    base_url = "http://localhost:8000"
    
    endpoints_to_test = [
        "/",
        "/health",
        "/api/portfolio",
        "/api/holdings", 
        "/api/trades/active",
        "/api/ai/decisions/recent",
        "/api/ai/analysis",
        "/api/system/status"
    ]
    
    print(f"Testing API endpoints on {base_url}...")
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"⚠️  {endpoint} - Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Error: {e}")
    
    print("\nAPI endpoint testing complete!")

if __name__ == "__main__":
    test_api_endpoints()
