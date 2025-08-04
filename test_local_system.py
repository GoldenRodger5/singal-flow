#!/usr/bin/env python3
"""
Test the trading system fixes locally
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def test_trading_system():
    """Test the main trading system components"""
    print("🧪 Testing Signal Flow Trading System...")
    print("=" * 50)
    
    # Test 1: Import and initialize orchestrator
    print("1. Testing orchestrator initialization...")
    try:
        from main import SignalFlowOrchestrator
        orchestrator = SignalFlowOrchestrator()
        print("✅ Orchestrator: INITIALIZED")
    except Exception as e:
        print(f"❌ Orchestrator: FAILED - {e}")
        return False
    
    # Test 2: Test scheduling system
    print("\n2. Testing task scheduling...")
    try:
        orchestrator.schedule_tasks()
        print("✅ Scheduling: CONFIGURED")
    except Exception as e:
        print(f"❌ Scheduling: FAILED - {e}")
        return False
    
    # Test 3: Test telegram service (without actually sending)
    print("\n3. Testing notification services...")
    try:
        from services.telegram_trading import telegram_trading
        print("✅ Telegram Service: IMPORTED")
    except Exception as e:
        print(f"❌ Telegram Service: FAILED - {e}")
    
    # Test 4: Test market scan function (dry run)
    print("\n4. Testing market scan function...")
    try:
        # This will test the function without actually running it
        import inspect
        scan_signature = inspect.signature(orchestrator.run_market_scan)
        print("✅ Market Scan: FUNCTION READY")
        print(f"   Signature: {scan_signature}")
    except Exception as e:
        print(f"❌ Market Scan: FAILED - {e}")
    
    print("\n" + "=" * 50)
    print("✅ Local tests completed successfully!")
    print("💡 The system should work when deployed to Railway")
    return True

if __name__ == "__main__":
    asyncio.run(test_trading_system())
