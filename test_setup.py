"""
Test script to verify Signal Flow setup and configuration.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.config import Config
from utils.logger_setup import setup_logger
from loguru import logger


async def test_configuration():
    """Test configuration setup."""
    print("🔧 Testing Configuration...")
    
    # Setup logger
    setup_logger()
    logger.info("Logger initialized successfully")
    
    # Test configuration
    config = Config()
    print(f"✅ Environment: {config.ENVIRONMENT}")
    print(f"✅ Trading hours: {config.TRADING_START_TIME} - {config.TRADING_END_TIME}")
    print(f"✅ Price range: ${config.TICKER_PRICE_MIN} - ${config.TICKER_PRICE_MAX}")
    print(f"✅ R:R Threshold: {config.RR_THRESHOLD}")
    
    # Test configuration validation
    validation = config.validate_config()
    if validation['valid']:
        print("✅ Configuration validation passed")
    else:
        print(f"⚠️  Missing configuration: {validation['missing_keys']}")
    
    # Check API keys (without exposing them)
    api_keys_status = {
        "Polygon": "✅" if config.POLYGON_API_KEY else "❌",
        "Alpaca API": "✅" if config.ALPACA_API_KEY else "❌", 
        "Alpaca Secret": "✅" if config.ALPACA_SECRET else "❌",
        "Twilio SID": "✅" if config.TWILIO_ACCOUNT_SID else "❌",
        "Twilio Token": "✅" if config.TWILIO_AUTH_TOKEN else "❌",
        "WhatsApp From": "✅" if config.WHATSAPP_FROM else "❌",
        "WhatsApp To": "✅" if config.WHATSAPP_TO else "❌",
        "OpenAI": "✅" if config.OPENAI_API_KEY else "❌",
        "Claude": "✅" if config.CLAUDE_API_KEY else "❌"
    }
    
    print("\n🔑 API Keys Status:")
    for key, status in api_keys_status.items():
        print(f"  {key}: {status}")
    
    # Validate required keys
    validation = config.validate_config()
    if validation['valid']:
        print("\n✅ All required API keys are configured")
    else:
        print("\n❌ Some required API keys are missing")
        print("📝 Please copy .env.template to .env and add your API keys")
    
    return True


async def test_data_provider():
    """Test data provider connection (if API keys available)."""
    print("\n📊 Testing Data Provider...")
    
    try:
        from services.data_provider import PolygonDataProvider
        
        config = Config()
        if not config.POLYGON_API_KEY:
            print("⚠️  Polygon API key not configured, skipping data provider test")
            return False
        
        async with PolygonDataProvider() as provider:
            # Test a simple API call
            snapshot = await provider.get_market_snapshot("AAPL")
            if snapshot:
                print("✅ Data provider connection successful")
                return True
            else:
                print("❌ Data provider connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Data provider test failed: {e}")
        return False


async def test_technical_indicators():
    """Test technical indicators calculation."""
    print("\n📈 Testing Technical Indicators...")
    
    try:
        import pandas as pd
        import numpy as np
        from services.indicators import TechnicalIndicators
        
        # Create sample data
        dates = pd.date_range('2025-01-01', periods=100, freq='H')
        np.random.seed(42)
        
        # Generate realistic price data
        base_price = 20.0
        price_changes = np.random.normal(0, 0.02, 100)
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.1))  # Ensure positive prices
        
        df = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(10000, 100000, 100)
        }, index=dates)
        
        # Test indicators
        rsi = TechnicalIndicators.calculate_rsi(df)
        macd = TechnicalIndicators.calculate_macd(df)
        vwap = TechnicalIndicators.calculate_vwap(df)
        
        if not rsi.empty and len(macd['macd']) > 0 and not vwap.empty:
            print("✅ Technical indicators calculation successful")
            print(f"  RSI (last): {rsi.iloc[-1]:.2f}")
            print(f"  MACD (last): {macd['macd'].iloc[-1]:.4f}")
            print(f"  VWAP (last): {vwap.iloc[-1]:.2f}")
            return True
        else:
            print("❌ Technical indicators calculation failed")
            return False
            
    except Exception as e:
        print(f"❌ Technical indicators test failed: {e}")
        return False


async def test_file_structure():
    """Test file structure and data files."""
    print("\n📁 Testing File Structure...")
    
    required_dirs = ['agents', 'services', 'data', 'utils', 'logs']
    required_files = [
        'data/watchlist_dynamic.json',
        'data/trade_log.json', 
        'data/strategy_stats.json',
        'services/config.py',
        'main.py',
        'requirements.txt'
    ]
    
    missing_dirs = []
    missing_files = []
    
    # Check directories
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
    
    # Check files
    for file_name in required_files:
        if not os.path.exists(file_name):
            missing_files.append(file_name)
    
    if not missing_dirs and not missing_files:
        print("✅ All required directories and files exist")
        return True
    else:
        if missing_dirs:
            print(f"❌ Missing directories: {missing_dirs}")
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Signal Flow Setup Test\n")
    
    tests = [
        ("Configuration", test_configuration),
        ("File Structure", test_file_structure),
        ("Technical Indicators", test_technical_indicators),
        ("Data Provider", test_data_provider),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("🎯 TEST SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Signal Flow is ready to go.")
        print("\n📝 Next steps:")
        print("1. Copy .env.template to .env and add your API keys")
        print("2. Run: python main.py")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues before proceeding.")


if __name__ == "__main__":
    asyncio.run(main())
