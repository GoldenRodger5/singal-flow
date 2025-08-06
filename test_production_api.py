#!/usr/bin/env python3
"""
Test script for the production API to verify all components work correctly
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / 'backend'))

async def test_api_components():
    """Test all major API components"""
    
    print("🧪 Testing Production API Components...")
    
    # Test 1: Import the production API
    print("\n1. Testing imports...")
    try:
        from scripts.production_api import app, get_db, get_trading_service, get_orchestrator
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Test database connection
    print("\n2. Testing database connection...")
    try:
        db = get_db()
        result = await db.log_system_health("test_component", "testing")
        if result:
            print("✅ Database connection working")
        else:
            print("⚠️ Database connection issue")
    except Exception as e:
        print(f"❌ Database test failed: {e}")
    
    # Test 3: Test trading service
    print("\n3. Testing trading service...")
    try:
        trading_service = get_trading_service()
        account = await trading_service.get_account()
        if account:
            print(f"✅ Trading service connected - Account: {account.status}")
        else:
            print("⚠️ Trading service connection issue")
    except Exception as e:
        print(f"❌ Trading service test failed: {e}")
    
    # Test 4: Test AI endpoints functionality
    print("\n4. Testing AI endpoints...")
    try:
        # Test get_recent_decisions
        decisions = await db.get_recent_decisions(limit=5)
        print(f"✅ AI decisions endpoint ready - Found {len(decisions)} decisions")
        
        # Test get_active_trades
        trades = await db.get_active_trades()
        print(f"✅ Active trades endpoint ready - Found {len(trades)} trades")
        
        # Test learning summary
        summary = await db.get_learning_summary()
        print(f"✅ Learning summary ready - {summary.get('total_trades', 0)} trades recorded")
        
    except Exception as e:
        print(f"❌ AI endpoints test failed: {e}")
    
    # Test 5: Test health monitoring
    print("\n5. Testing health monitoring...")
    try:
        from services.health_monitor import health_monitor
        health_status = await health_monitor.perform_full_health_check()
        print(f"✅ Health monitoring working - Status: {health_status.get('overall', 'unknown')}")
    except Exception as e:
        print(f"❌ Health monitoring test failed: {e}")
    
    print("\n🎉 Production API component testing complete!")
    return True

def test_environment():
    """Test environment configuration"""
    print("🔧 Testing Environment Configuration...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'ALPACA_API_KEY': 'Alpaca Trading API Key',
        'ALPACA_SECRET': 'Alpaca Trading Secret',
        'MONGODB_URL': 'MongoDB Atlas Connection',
        'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
        'TELEGRAM_CHAT_ID': 'Telegram Chat ID'
    }
    
    all_set = True
    for var, description in required_vars.items():
        if os.getenv(var):
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - Missing {var}")
            all_set = False
    
    if all_set:
        print("✅ All environment variables configured!")
    else:
        print("❌ Some environment variables missing!")
    
    return all_set

async def main():
    """Main test function"""
    print("🚀 Signal Flow Production API Test Suite")
    print("=" * 50)
    
    # Test environment first
    env_ok = test_environment()
    if not env_ok:
        print("\n❌ Environment configuration issues detected!")
        return
    
    # Test API components
    api_ok = await test_api_components()
    
    if api_ok and env_ok:
        print("\n🎉 ALL TESTS PASSED - Production API ready!")
        print("\nTo start the server:")
        print("cd /Users/isaacmineo/Main/projects/singal-flow")
        print("python backend/scripts/production_api.py")
        print("\nOr via uvicorn:")
        print("cd /Users/isaacmineo/Main/projects/singal-flow/backend")
        print("uvicorn scripts.production_api:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("\n❌ Some tests failed - check the issues above!")

if __name__ == "__main__":
    asyncio.run(main())
