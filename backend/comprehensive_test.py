"""
Comprehensive Production System Test
Tests all services with proper environment configuration
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from utils.env_manager import env_manager
from loguru import logger

async def test_all_services():
    """Test all production services."""
    print("\n🚀 COMPREHENSIVE PRODUCTION SYSTEM TEST")
    print("="*60)
    
    # Test 1: Environment Configuration
    print("\n1️⃣ Testing Environment Configuration...")
    try:
        env_manager.print_config_summary()
        print("✅ Environment configuration: PASSED")
    except Exception as e:
        print(f"❌ Environment configuration: FAILED - {e}")
        return False
    
    # Test 2: Real-time Market Data Service
    print("\n2️⃣ Testing Real-time Market Data Service...")
    try:
        from services.real_time_market_data import market_data_service
        
        # Test market status
        status = await market_data_service.get_market_status()
        print(f"   Market Status: {status}")
        
        # Test real-time quote
        quote = await market_data_service.get_real_time_quote("AAPL")
        print(f"   AAPL Quote: ${quote.get('price', 'N/A')}")
        
        print("✅ Real-time Market Data: PASSED")
    except Exception as e:
        print(f"❌ Real-time Market Data: FAILED - {e}")
        return False
    
    # Test 3: AI Signal Generation Service
    print("\n3️⃣ Testing AI Signal Generation Service...")
    try:
        from services.ai_signal_generation import signal_generation_service
        
        # Test signal generation
        signals = await signal_generation_service.get_active_signals()
        print(f"   Active Signals: {len(signals)}")
        
        print("✅ AI Signal Generation: PASSED")
    except Exception as e:
        print(f"❌ AI Signal Generation: FAILED - {e}")
        return False
    
    # Test 4: Performance Analytics Service
    print("\n4️⃣ Testing Performance Analytics Service...")
    try:
        from services.performance_analytics import performance_analytics_service
        
        # Test performance metrics
        metrics = await performance_analytics_service.get_overall_performance()
        print(f"   Total Return: {metrics.total_return:.2%}")
        print(f"   Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        
        print("✅ Performance Analytics: PASSED")
    except Exception as e:
        print(f"❌ Performance Analytics: FAILED - {e}")
        return False
    
    # Test 5: Market Pulse Service
    print("\n5️⃣ Testing Market Pulse Service...")
    try:
        from services.market_pulse import market_pulse_service
        
        # Test market pulse
        pulse = await market_pulse_service.get_market_pulse()
        print(f"   Market Trend: {pulse.get('trend', 'N/A')}")
        print(f"   Volatility Level: {pulse.get('volatility_level', 'N/A')}")
        
        print("✅ Market Pulse: PASSED")
    except Exception as e:
        print(f"❌ Market Pulse: FAILED - {e}")
        return False
    
    # Test 6: Database Connectivity
    print("\n6️⃣ Testing Database Connectivity...")
    try:
        from backend.utils.database_manager import db_manager
        
        # Test database connection
        await db_manager.connect()
        collections = await db_manager.list_collections()
        print(f"   Connected Collections: {len(collections)}")
        
        print("✅ Database Connectivity: PASSED")
    except Exception as e:
        print(f"❌ Database Connectivity: FAILED - {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED! System is production ready!")
    print("="*60)
    return True

async def test_production_api_endpoints():
    """Test the production API endpoints."""
    print("\n🔗 Testing Production API Endpoints...")
    
    try:
        import aiohttp
        
        # Start the API server (if not already running)
        base_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health endpoint: {data['status']}")
                else:
                    print(f"❌ Health endpoint: HTTP {response.status}")
            
            # Test market data endpoint
            async with session.get(f"{base_url}/api/market-data/AAPL") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Market data endpoint: AAPL ${data.get('price', 'N/A')}")
                else:
                    print(f"❌ Market data endpoint: HTTP {response.status}")
            
            # Test signals endpoint
            async with session.get(f"{base_url}/api/signals/active") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Signals endpoint: {len(data)} active signals")
                else:
                    print(f"❌ Signals endpoint: HTTP {response.status}")
    
    except Exception as e:
        print(f"⚠️ API endpoint testing skipped: {e}")
        print("   (Run 'python backend/main.py' to start the API server)")

if __name__ == "__main__":
    print("Starting comprehensive production system test...")
    
    # Run the tests
    asyncio.run(test_all_services())
    
    # Test API endpoints if server is running
    asyncio.run(test_production_api_endpoints())
