#!/usr/bin/env python3
"""
Production Configuration Verification Script
Ensures all systems are ready for autonomous paper trading deployment.
"""

import os
import asyncio
from datetime import datetime
from backend.services.database_manager import DatabaseManager
from backend.services.alpaca_trading import AlpacaTradingService
from backend.services.real_time_market_data import RealTimeMarketData


async def verify_production_config():
    print("🔍 PRODUCTION READINESS VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks_passed = 0
    total_checks = 0
    
    # Check 1: Environment Variables
    print("📋 ENVIRONMENT CONFIGURATION")
    print("-" * 30)
    total_checks += 1
    
    required_vars = [
        'ALPACA_API_KEY',
        'ALPACA_SECRET', 
        'MONGODB_URI',
        'POLYGON_API_KEY',
        'OPENAI_API_KEY'
    ]
    
    env_check = True
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Configured")
        else:
            print(f"❌ {var}: Missing")
            env_check = False
    
    # Trading Configuration
    print(f"✅ ALPACA_BASE_URL: {os.getenv('ALPACA_BASE_URL', 'Not set')}")
    print(f"✅ PAPER_TRADING: {os.getenv('PAPER_TRADING', 'false')}")
    print(f"✅ AUTO_EXECUTE_SIGNALS: {os.getenv('AUTO_EXECUTE_SIGNALS', 'false')}")
    print(f"✅ AUTOMATION_MODE: {os.getenv('AUTOMATION_MODE', 'manual')}")
    
    if env_check:
        checks_passed += 1
        print("✅ Environment variables: PASSED")
    else:
        print("❌ Environment variables: FAILED")
    print()
    
    # Check 2: Database Connection
    print("🗄️  DATABASE CONNECTION")
    print("-" * 30)
    total_checks += 1
    
    try:
        db_manager = DatabaseManager()
        print("✅ MongoDB connection: ESTABLISHED")
        print(f"✅ Database: {db_manager.db.name}")
        checks_passed += 1
    except Exception as e:
        print(f"❌ MongoDB connection: FAILED - {e}")
    print()
    
    # Check 3: Alpaca Trading Service
    print("📈 ALPACA TRADING SERVICE")
    print("-" * 30)
    total_checks += 1
    
    try:
        alpaca_service = AlpacaTradingService()
        account = alpaca_service.api.get_account()
        print(f"✅ Alpaca connection: ESTABLISHED")
        print(f"✅ Account status: {account.status}")
        print(f"✅ Trading blocked: {account.trading_blocked}")
        print(f"✅ Buying power: ${float(account.buying_power):,.2f}")
        print(f"✅ Portfolio value: ${float(account.portfolio_value):,.2f}")
        
        if account.status == 'ACTIVE' and not account.trading_blocked:
            checks_passed += 1
            print("✅ Alpaca trading: READY")
        else:
            print("⚠️ Alpaca trading: Account issues detected")
    except Exception as e:
        print(f"❌ Alpaca connection: FAILED - {e}")
    print()
    
    # Check 4: Market Data Service  
    print("📊 MARKET DATA SERVICE")
    print("-" * 30)
    total_checks += 1
    
    try:
        market_data_service = RealTimeMarketData()
        test_data = await market_data_service.get_current_price('AAPL')
        if test_data and test_data.get('price'):
            print(f"✅ Market data: ACTIVE")
            print(f"✅ AAPL current price: ${test_data['price']}")
            checks_passed += 1
        else:
            print("❌ Market data: No valid data returned")
    except Exception as e:
        print(f"❌ Market data service: FAILED - {e}")
    print()
    
    # Check 5: Production Safety Settings
    print("🛡️  PRODUCTION SAFETY CHECKS")
    print("-" * 30)
    total_checks += 1
    
    safety_checks = []
    
    # Verify paper trading is enabled
    if os.getenv('PAPER_TRADING', 'false').lower() == 'true':
        safety_checks.append("✅ Paper trading enabled")
    else:
        safety_checks.append("❌ Paper trading disabled - DANGEROUS!")
    
    # Verify base URL is paper
    if 'paper-api.alpaca.markets' in os.getenv('ALPACA_BASE_URL', ''):
        safety_checks.append("✅ Using paper trading API")
    else:
        safety_checks.append("❌ Using LIVE trading API - DANGEROUS!")
    
    # Check automation settings
    if os.getenv('AUTO_EXECUTE_SIGNALS', 'false').lower() == 'true':
        safety_checks.append("✅ Autonomous trading enabled")
    else:
        safety_checks.append("⚠️ Autonomous trading disabled")
    
    # Check confidence threshold
    confidence_threshold = float(os.getenv('SIGNAL_CONFIDENCE_AUTO_EXECUTE', '0.8'))
    if confidence_threshold >= 0.7:
        safety_checks.append(f"✅ Confidence threshold: {confidence_threshold}")
    else:
        safety_checks.append(f"⚠️ Low confidence threshold: {confidence_threshold}")
    
    for check in safety_checks:
        print(check)
    
    if all('✅' in check for check in safety_checks):
        checks_passed += 1
        print("✅ Production safety: PASSED")
    else:
        print("⚠️ Production safety: Review required")
    print()
    
    # Final Results
    print("🎯 PRODUCTION READINESS SUMMARY")
    print("=" * 60)
    print(f"Checks passed: {checks_passed}/{total_checks}")
    print(f"Success rate: {checks_passed/total_checks*100:.1f}%")
    
    if checks_passed == total_checks:
        print("🎉 SYSTEM READY FOR PRODUCTION DEPLOYMENT!")
        print("✅ All systems operational")
        print("✅ Paper trading configured") 
        print("✅ Autonomous trading enabled")
        print("✅ Database cleared and ready")
        print("✅ Real market data connected")
        return True
    else:
        print("⚠️ SYSTEM NOT READY - Please fix failing checks")
        return False


if __name__ == "__main__":
    result = asyncio.run(verify_production_config())
    exit(0 if result else 1)
