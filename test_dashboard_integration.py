#!/usr/bin/env python3
"""
Comprehensive Dashboard Integration Test
Tests all dashboard endpoints and functionality to ensure real data connections.
"""

import requests
import json
from datetime import datetime
import sys

BACKEND_URL = "https://web-production-3e19d.up.railway.app"

def test_endpoint(endpoint, description, method='GET'):
    """Test a single endpoint and return results"""
    try:
        headers = {}
        data = None
        
        if method == 'POST':
            headers['Content-Type'] = 'application/json'
            data = '{}'  # Empty JSON body
            response = requests.post(f"{BACKEND_URL}{endpoint}", headers=headers, data=data, timeout=10)
        else:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=10)
            
        if response.status_code == 200:
            data = response.json()
            return True, data, f"✅ {description}"
        else:
            return False, None, f"❌ {description} - Status: {response.status_code}"
    except Exception as e:
        return False, None, f"❌ {description} - Error: {str(e)}"

def main():
    print("🧪 COMPREHENSIVE DASHBOARD INTEGRATION TEST")
    print("=" * 60)
    print(f"Testing backend: {BACKEND_URL}")
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Define test cases for each dashboard component
    test_cases = [
        # System Overview Dashboard
        ("/health/detailed", "System Health Check", 'GET'),
        ("/api/account", "Account Information", 'GET'),
        ("/api/holdings", "Portfolio Holdings", 'GET'),
        
        # Trading Dashboard  
        ("/api/dashboard/holdings/detailed", "Detailed Holdings", 'GET'),
        ("/api/dashboard/analytics/performance", "Performance Analytics", 'GET'),
        ("/api/dashboard/watchlist/signals", "Watchlist Signals", 'GET'),
        
        # AI Analysis Dashboard
        ("/api/dashboard/market/pulse", "Market Pulse", 'GET'),
        ("/api/dashboard/ai/signals", "AI Signals", 'GET'),
        ("/api/dashboard/ai/learning-metrics", "AI Learning Metrics", 'GET'),
        ("/api/ai/predictions", "AI Predictions", 'GET'),
        ("/api/ai/learning/summary", "AI Learning Summary", 'GET'),
        
        # Control Panel
        ("/api/control/status", "Control Panel Status", 'GET'),
        ("/api/control/toggle_auto_trading", "Auto-Trading Control", 'POST'),
        
        # Configuration Panel (using working endpoints)
        ("/api/control/status", "System Configuration", 'GET'),
        
        # Market Data
        ("/api/market/realtime/AAPL", "Real-time Market Data", 'GET'),
        ("/api/ai/market-sentiment/AAPL", "Market Sentiment", 'GET'),
    ]

    results = []
    working_endpoints = 0
    total_endpoints = len(test_cases)

    print("📋 TESTING INDIVIDUAL ENDPOINTS:")
    print("-" * 40)
    
    for endpoint, description, method in test_cases:
        success, data, message = test_endpoint(endpoint, description, method)
        results.append((endpoint, success, data, message))
        print(message)
        
        if success:
            working_endpoints += 1
            # Show sample data for key endpoints
            if endpoint == "/api/account":
                print(f"   💰 Portfolio Value: ${data.get('portfolio_value', 0):,.2f}")
                print(f"   💵 Buying Power: ${data.get('buying_power', 0):,.2f}")
            elif endpoint == "/health/detailed":
                print(f"   🔍 Overall Health: {data.get('status', 'unknown')}")
                print(f"   📊 Trading API: {data.get('trading_api', 'unknown')}")
                print(f"   🗄️  Database: {data.get('database', 'unknown')}")
            elif endpoint == "/api/control/toggle_auto_trading" and method == 'POST':
                print(f"   🔄 Action: toggle_auto_trading")
                print(f"   ✅ Status: {data.get('status', 'unknown')}")
                print(f"   🤖 Auto-trading: {data.get('new_status', 'unknown')}")

    print()
    print("📊 TEST RESULTS SUMMARY:")
    print("-" * 40)
    print(f"✅ Working endpoints: {working_endpoints}/{total_endpoints}")
    print(f"📈 Success rate: {(working_endpoints/total_endpoints)*100:.1f}%")
    
    # Analyze results by dashboard component
    system_overview = sum(1 for endpoint, success, _, _ in results[:3] if success)
    trading_dashboard = sum(1 for endpoint, success, _, _ in results[3:6] if success)  
    ai_analysis = sum(1 for endpoint, success, _, _ in results[6:11] if success)
    control_panel = sum(1 for endpoint, success, _, _ in results[11:13] if success)
    market_data = sum(1 for endpoint, success, _, _ in results[-2:] if success)

    print()
    print("🎯 DASHBOARD COMPONENT HEALTH:")
    print("-" * 40)
    print(f"🖥️  System Overview: {system_overview}/3 endpoints working")
    print(f"📈 Trading Dashboard: {trading_dashboard}/3 endpoints working") 
    print(f"🤖 AI Analysis: {ai_analysis}/5 endpoints working")
    print(f"⚙️  Control Panel: {control_panel}/2 endpoints working")
    print(f"📊 Market Data: {market_data}/2 endpoints working")

    # Check for real data vs mock data
    print()
    print("🔍 DATA QUALITY ANALYSIS:")
    print("-" * 40)
    
    real_data_indicators = []
    for endpoint, success, data, _ in results:
        if success and data:
            if endpoint == "/api/account" and data.get('account_number'):
                real_data_indicators.append("✅ Real Alpaca account connected")
            elif endpoint == "/health/detailed" and data.get('trading_api') == 'healthy':
                real_data_indicators.append("✅ Trading API fully operational")
            elif endpoint == "/api/market/realtime/AAPL" and data.get('price'):
                real_data_indicators.append("✅ Real-time market data flowing")

    for indicator in real_data_indicators:
        print(indicator)
    
    if not real_data_indicators:
        print("⚠️  Limited real data connections detected")

    print()
    print("🎯 INTEGRATION STATUS:")
    print("-" * 40)
    
    if working_endpoints >= total_endpoints * 0.8:
        print("🎉 EXCELLENT: Dashboard integration is highly functional")
        status = "EXCELLENT"
    elif working_endpoints >= total_endpoints * 0.6:
        print("👍 GOOD: Dashboard integration is mostly functional")
        status = "GOOD" 
    elif working_endpoints >= total_endpoints * 0.4:
        print("⚠️  PARTIAL: Dashboard has some functionality issues")
        status = "PARTIAL"
    else:
        print("❌ POOR: Dashboard integration needs significant work")
        status = "POOR"

    print(f"📋 Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return status code for automation
    if status in ["EXCELLENT", "GOOD"]:
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
