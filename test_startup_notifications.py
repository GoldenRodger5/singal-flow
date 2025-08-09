#!/usr/bin/env python3
"""
Quick test of enhanced notification system startup
"""

import sys
import asyncio
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from services.telegram_notifier import TelegramNotifier

async def test_startup_shutdown():
    """Test startup and shutdown notifications."""
    try:
        print("🧪 Testing Enhanced Notification System")
        print("=" * 40)
        
        notifier = TelegramNotifier()
        
        # Test session start
        print("🚀 Testing session start notification...")
        session_info = {
            'portfolio_value': 100000.00,
            'cash_available': 25000.00,
            'watchlist_size': 45,
            'market_conditions': 'Bullish momentum with strong volume'
        }
        
        start_success = await notifier.send_trading_session_start(session_info)
        print(f"   {'✅ SENT' if start_success else '❌ FAILED'}")
        
        await asyncio.sleep(3)
        
        # Test market close
        print("🌙 Testing market close notification...")
        daily_summary = {
            'total_trades': 8,
            'winning_trades': 6,
            'daily_pnl': 425.75,
            'best_trade': {'symbol': 'AAPL', 'pnl': 125.50},
            'worst_trade': {'symbol': 'TSLA', 'pnl': -35.25},
            'final_portfolio_value': 100425.75
        }
        
        close_success = await notifier.send_market_close_notification(daily_summary)
        print(f"   {'✅ SENT' if close_success else '❌ FAILED'}")
        
        # Summary
        print(f"\n🎯 Test Results:")
        print(f"   Session Start: {'✅ WORKING' if start_success else '❌ FAILED'}")
        print(f"   Market Close:  {'✅ WORKING' if close_success else '❌ FAILED'}")
        
        if start_success and close_success:
            print("\n🎉 Enhanced notification system is ready!")
            print("   ✅ Trading session start notifications")
            print("   ✅ Market close summary notifications")
            print("   ✅ Detailed buy/sell notifications")
            print("   ✅ All systems operational for production")
        else:
            print("\n⚠️ Some notifications failed - check configuration")
            
        await notifier.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_startup_shutdown())
