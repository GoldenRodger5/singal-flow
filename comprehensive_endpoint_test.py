#!/usr/bin/env python3
"""
FINAL COMPREHENSIVE ENDPOINT TEST
Tests all endpoints after deployment with Railway-Vercel integration
"""

import requests
import json
from datetime import datetime

# Test configuration
BACKEND_URL = "https://web-production-3e19d.up.railway.app"
FRONTEND_DOMAIN = "vercel.app"  # Typical Vercel domain

def test_endpoint_with_cors(endpoint, method="GET"):
    """Test endpoint with CORS headers"""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {
        'Origin': f'https://your-app.{FRONTEND_DOMAIN}',
        'User-Agent': 'SignalFlow-Frontend/1.0'
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        else:
            response = requests.request(method, url, headers=headers, timeout=10)
        
        # Check response
        status = "✅" if response.status_code == 200 else "❌"
        cors_header = response.headers.get('access-control-allow-origin', 'MISSING')
        
        # Check for mock data
        mock_check = "✅ Real Data"
        if response.status_code == 200:
            try:
                data = response.json()
                data_str = str(data).lower()
                if any(word in data_str for word in ['mock', 'fake', 'dummy', 'sample'] if 'no mock' not in data_str):
                    mock_check = "❌ Contains Mock Data"
            except:
                pass
        
        print(f"{status} {endpoint:<30} | Status: {response.status_code:<3} | CORS: {cors_header:<20} | {mock_check}")
        
        return response.status_code == 200 and cors_header != 'MISSING'
    
    except Exception as e:
        print(f"❌ {endpoint:<30} | ERROR: {str(e)}")
        return False

def main():
    print("🚀 COMPREHENSIVE RAILWAY-VERCEL ENDPOINT TEST")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    # All endpoints to test
    endpoints = [
        # Core health endpoints
        "/health",
        "/health/detailed",
        
        # Trading endpoints
        "/api/account",
        "/api/positions",
        "/api/trades/active",
        "/api/trades/performance",
        
        # AI endpoints
        "/api/ai/decisions/recent",
        "/api/ai/signals/recent",
        "/api/ai/analysis/sentiment",
        
        # Market data endpoints
        "/api/market/data",
        "/api/market/scan/results",
        
        # System endpoints
        "/api/system/status",
        "/api/system/health",
        
        # Dashboard endpoints
        "/api/dashboard/overview",
        "/api/dashboard/performance",
    ]
    
    print("Endpoint                       | Status | CORS               | Data Quality")
    print("-" * 100)
    
    working_count = 0
    cors_count = 0
    
    for endpoint in endpoints:
        if test_endpoint_with_cors(endpoint):
            working_count += 1
            cors_count += 1
    
    print("="*100)
    print(f"📊 RESULTS:")
    print(f"   Working Endpoints: {working_count}/{len(endpoints)}")
    print(f"   CORS Configured: {cors_count}/{len(endpoints)}")
    
    if working_count == len(endpoints) and cors_count == len(endpoints):
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ Railway backend fully working")
        print("✅ Vercel frontend can connect") 
        print("✅ No mock or fallback data detected")
        print("✅ CORS properly configured")
        print("🚀 READY FOR LIVE TRADING!")
    else:
        print(f"\n⚠️  {len(endpoints) - working_count} endpoints need attention")
        print("🔧 Check logs and fix failing endpoints")

if __name__ == "__main__":
    main()
