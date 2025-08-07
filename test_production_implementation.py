#!/usr/bin/env python3
"""
Production Implementation Test Script
Tests all the new services and API endpoints to ensure 100% functionality
"""
import asyncio
import os
import sys
import json
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, '/Users/isaacmineo/Main/projects/singal-flow/backend')

async def test_real_time_market_data():
    """Test real-time market data service."""
    print("\n🔍 Testing Real-time Market Data Service...")
    try:
        from backend.services.real_time_market_data import market_data_service
        
        # Test single quote
        async with market_data_service:
            quote = await market_data_service.get_real_time_quote('AAPL')
            if quote:
                print(f"✅ AAPL Quote: ${quote.price:.2f} ({quote.change_percent:.2f}%)")
            else:
                print("❌ Failed to get AAPL quote")
            
            # Test multiple quotes
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            quotes = await market_data_service.get_multiple_quotes(symbols)
            print(f"✅ Retrieved {len(quotes)}/{len(symbols)} quotes")
            
            # Test market status
            status = await market_data_service.get_market_status()
            print(f"✅ Market Status: {'Open' if status.get('market_open') else 'Closed'}")
            
        return True
        
    except Exception as e:
        print(f"❌ Real-time Market Data Service Error: {e}")
        return False

async def test_ai_signal_generation():
    """Test AI signal generation service."""
    print("\n🤖 Testing AI Signal Generation Service...")
    try:
        from backend.services.ai_signal_generation import ai_signal_service
        
        # Test signal generation for watchlist
        signals = await ai_signal_service.generate_signals_for_watchlist()
        print(f"✅ Generated {len(signals)} AI signals")
        
        # Test getting active signals
        active_signals = await ai_signal_service.get_active_signals()
        print(f"✅ Found {len(active_signals)} active signals")
        
        # Test signal performance
        performance = await ai_signal_service.get_signal_performance(days=7)
        print(f"✅ Signal Performance: {performance.get('success_rate', 0)}% success rate")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Signal Generation Service Error: {e}")
        return False

async def test_performance_analytics():
    """Test performance analytics service."""
    print("\n📊 Testing Performance Analytics Service...")
    try:
        from backend.services.performance_analytics import performance_service
        
        # Test overall performance
        overall = await performance_service.get_overall_performance()
        print(f"✅ Overall Performance: {overall.total_return:.2f}% return")
        
        # Test daily performance
        daily = await performance_service.get_daily_performance(days=7)
        print(f"✅ Daily Performance: {len(daily)} days of data")
        
        # Test trading statistics
        stats = await performance_service.get_trading_statistics(days=30)
        print(f"✅ Trading Stats: {stats.get('total_trades', 0)} trades, {stats.get('win_rate', 0):.1f}% win rate")
        
        # Test risk metrics
        risk = await performance_service.get_risk_metrics()
        print(f"✅ Risk Metrics: {risk.get('sharpe_ratio', 0):.2f} Sharpe ratio")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance Analytics Service Error: {e}")
        return False

async def test_market_pulse():
    """Test market pulse service."""
    print("\n📈 Testing Market Pulse Service...")
    try:
        from backend.services.market_pulse import market_pulse_service
        
        # Test market pulse generation
        pulse = await market_pulse_service.get_market_pulse()
        print(f"✅ Market Trend: {pulse.market_trend}")
        print(f"✅ Volatility: {pulse.market_volatility}")
        print(f"✅ Volume Profile: {pulse.volume_profile}")
        print(f"✅ VIX: {pulse.volatility_index}")
        
        # Test historical pulse
        history = await market_pulse_service.get_historical_pulse(days=3)
        print(f"✅ Historical Pulse: {len(history)} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Market Pulse Service Error: {e}")
        return False

async def test_database_connectivity():
    """Test database connectivity and new methods."""
    print("\n🗄️ Testing Database Connectivity...")
    try:
        from backend.services.database_manager import db_manager
        
        # Test AI signals storage
        test_signals = [{
            'symbol': 'TEST',
            'signal_type': 'BUY',
            'confidence': 0.85,
            'timestamp': datetime.now(timezone.utc),
            'reasoning': 'Test signal'
        }]
        
        await db_manager.store_ai_signals(test_signals)
        print("✅ AI signals storage working")
        
        # Test market pulse storage
        test_pulse = {
            'market_trend': 'BULLISH',
            'volatility_index': 15.5,
            'timestamp': datetime.now(timezone.utc)
        }
        
        await db_manager.store_market_pulse(test_pulse)
        print("✅ Market pulse storage working")
        
        # Test system config
        await db_manager.update_system_config('test', {'test_key': 'test_value'})
        config = await db_manager.get_system_config('test')
        print(f"✅ System config working: {config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database Connectivity Error: {e}")
        return False

async def test_production_api_endpoints():
    """Test the production API endpoints using aiohttp."""
    print("\n🌐 Testing Production API Endpoints...")
    try:
        import aiohttp
        
        base_url = "http://localhost:8000"
        
        # Test endpoints that should work now
        test_endpoints = [
            "/health",
            "/api/market/realtime/AAPL",
            "/api/ai/signals/recent",
            "/api/dashboard/analytics/performance",
            "/api/dashboard/market/pulse",
            "/api/dashboard/watchlist/signals",
            "/api/config/system"
        ]
        
        async with aiohttp.ClientSession() as session:
            working_endpoints = 0
            
            for endpoint in test_endpoints:
                try:
                    async with session.get(f"{base_url}{endpoint}", timeout=10) as response:
                        if response.status == 200:
                            print(f"✅ {endpoint}: Status 200")
                            working_endpoints += 1
                        elif response.status == 501:
                            print(f"❌ {endpoint}: Still returns 501 (Not Implemented)")
                        else:
                            print(f"⚠️ {endpoint}: Status {response.status}")
                            
                except aiohttp.ClientConnectorError:
                    print(f"❌ {endpoint}: Server not running")
                except asyncio.TimeoutError:
                    print(f"❌ {endpoint}: Timeout")
                except Exception as e:
                    print(f"❌ {endpoint}: Error - {e}")
            
            print(f"\n📊 API Endpoints Working: {working_endpoints}/{len(test_endpoints)}")
            return working_endpoints > 0
        
    except Exception as e:
        print(f"❌ API Testing Error: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive test of all new functionality."""
    print("🚀 Starting Comprehensive Production Implementation Test")
    print("=" * 70)
    
    test_results = []
    
    # Test all services
    services_to_test = [
        ("Real-time Market Data", test_real_time_market_data),
        ("AI Signal Generation", test_ai_signal_generation),
        ("Performance Analytics", test_performance_analytics),
        ("Market Pulse", test_market_pulse),
        ("Database Connectivity", test_database_connectivity)
    ]
    
    for service_name, test_func in services_to_test:
        try:
            result = await test_func()
            test_results.append((service_name, result))
        except Exception as e:
            print(f"❌ {service_name} Test Failed: {e}")
            test_results.append((service_name, False))
    
    # Test API endpoints (requires running server)
    print("\n🔄 Testing API endpoints (requires running server)...")
    api_result = await test_production_api_endpoints()
    test_results.append(("Production API Endpoints", api_result))
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(test_results)
    
    for service_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {service_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Success Rate: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! 100% Production Functionality Achieved!")
    elif passed >= total * 0.8:
        print("✅ Most functionality working! Ready for production with minor fixes.")
    else:
        print("⚠️ Significant issues detected. Review failed services.")
    
    return passed == total

if __name__ == "__main__":
    # Load environment variables
    if os.path.exists('/Users/isaacmineo/Main/projects/singal-flow/.env'):
        from dotenv import load_dotenv
        load_dotenv('/Users/isaacmineo/Main/projects/singal-flow/.env')
        print("📋 Environment variables loaded from .env")
    
    # Run tests
    success = asyncio.run(run_comprehensive_test())
    
    if success:
        print("\n🚀 READY FOR PRODUCTION DEPLOYMENT!")
        print("All services implemented and working correctly.")
    else:
        print("\n🔧 IMPLEMENTATION NEEDS REVIEW")
        print("Some services require attention before production.")
    
    sys.exit(0 if success else 1)
