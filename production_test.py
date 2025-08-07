"""Quick test of services with proper API key management"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_services():
    print("🚀 Testing Production Services with Robust API Key Management")
    print("=" * 70)
    
    # Test 1: Environment Configuration
    print("\n1️⃣ Environment Configuration Test...")
    try:
        from backend.utils.env_manager import env_manager
        
        config = env_manager.get_api_config()
        api_keys_ok = 0
        for key, value in config.items():
            if value and len(str(value)) > 10:
                print(f"   ✅ {key}: OK")
                api_keys_ok += 1
            else:
                print(f"   ❌ {key}: Missing")
        
        print(f"   📊 API Keys Status: {api_keys_ok}/{len(config)} configured")
        
    except Exception as e:
        print(f"   ❌ Environment test failed: {e}")
        return
    
    # Test 2: Real-time Market Data
    print("\n2️⃣ Real-time Market Data Test...")
    try:
        from backend.services.real_time_market_data import market_data_service
        
        # Get market status
        status = await market_data_service.get_market_status()
        market_open = status.get('market_open', False)
        print(f"   📈 Market Status: {'Open' if market_open else 'Closed'}")
        
        # Get quote for AAPL
        quote = await market_data_service.get_real_time_quote('AAPL')
        print(f"   💰 AAPL: ${quote.price:.2f}")
        print(f"   📊 Change: {quote.change:+.2f} ({quote.change_percent:+.2f}%)")
        print(f"   📈 Volume: {quote.volume:,}")
        
        print("   ✅ Market Data Service: WORKING")
        
    except Exception as e:
        print(f"   ❌ Market Data test failed: {e}")
    
    # Test 3: AI Signal Generation
    print("\n3️⃣ AI Signal Generation Test...")
    try:
        from backend.services.ai_signal_generation import signal_generation_service
        
        signals = await signal_generation_service.get_active_signals()
        print(f"   🤖 Active AI Signals: {len(signals)}")
        
        print("   ✅ AI Signal Generation: WORKING")
        
    except Exception as e:
        print(f"   ❌ AI Signal Generation test failed: {e}")
    
    # Test 4: Performance Analytics
    print("\n4️⃣ Performance Analytics Test...")
    try:
        from backend.services.performance_analytics import performance_analytics_service
        
        metrics = await performance_analytics_service.get_overall_performance()
        print(f"   📊 Total Return: {metrics.total_return:.2%}")
        print(f"   📈 Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"   💹 Max Drawdown: {metrics.max_drawdown:.2%}")
        
        print("   ✅ Performance Analytics: WORKING")
        
    except Exception as e:
        print(f"   ❌ Performance Analytics test failed: {e}")
    
    # Test 5: Market Pulse
    print("\n5️⃣ Market Pulse Test...")
    try:
        from backend.services.market_pulse import market_pulse_service
        
        pulse = await market_pulse_service.get_market_pulse()
        print(f"   🔄 Market Trend: {pulse.market_trend}")
        print(f"   📊 Volatility: {pulse.market_volatility}")
        print(f"   📈 Volume Profile: {pulse.volume_profile}")
        
        print("   ✅ Market Pulse Service: WORKING")
        
    except Exception as e:
        print(f"   ❌ Market Pulse test failed: {e}")
    
    print("\n🎉 Production System Test Complete!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_services())
