#!/usr/bin/env python3
"""
Test Telegram Notification System for Trading Alerts
Tests all types of notifications you'll receive during autonomous trading.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from services.telegram_notifier import TelegramNotifier

async def test_all_notifications():
    """Test all notification types you'll receive during trading."""
    print("📱 TESTING TELEGRAM TRADING NOTIFICATIONS")
    print("=" * 50)
    
    try:
        notifier = TelegramNotifier()
        
        print("🔄 Sending notification tests to your Telegram...")
        print(f"   Bot: {notifier.config.TELEGRAM_BOT_TOKEN[:10]}...")
        print(f"   Chat: {notifier.config.TELEGRAM_CHAT_ID}")
        print()
        
        # Test 1: Enhanced Buy Notification with Price Predictions
        print("1. 🟢 Testing ENHANCED BUY notification with predictions...")
        buy_success = await notifier.send_buy_notification(
            symbol="AAPL",
            quantity=50,
            price=175.25,
            order_id="PAPER_BUY_001",
            predicted_target=185.50,  # AI predicted target
            confidence=8.5,           # AI confidence (8.5/10)
            stop_loss=168.00,         # Risk management stop
            reasoning="AI detected strong momentum breakout with high volume confirmation and positive market sentiment"
        )
        print(f"   ✅ Enhanced buy notification: {'SENT' if buy_success else 'FAILED'}")
        
        await asyncio.sleep(2)  # Prevent rate limiting
        
        # Test 2: Enhanced Sell Notification with Performance Analysis
        print("2. 🔴 Testing ENHANCED SELL notification with analysis...")
        sell_success = await notifier.send_sell_notification(
            symbol="TSLA",
            quantity=25, 
            price=242.80,
            pnl=375.50,
            order_id="PAPER_SELL_002",
            entry_price=227.30,       # Original entry price
            sell_reason="Take profit target achieved",
            target_hit=True           # Target was hit
        )
        print(f"   ✅ Enhanced sell notification: {'SENT' if sell_success else 'FAILED'}")
        
        await asyncio.sleep(2)
        
        # Test 3: Trading Session Start Notification
        print("3. 🚀 Testing TRADING SESSION START notification...")
        session_start_success = await notifier.send_trading_session_start({
            'portfolio_value': 103750.25,
            'cash_available': 28500.00,
            'watchlist_size': 45,
            'market_conditions': 'Bullish momentum with strong volume'
        })
        print(f"   ✅ Session start notification: {'SENT' if session_start_success else 'FAILED'}")
        
        await asyncio.sleep(2)
        
        # Test 4: Market Close Notification  
        print("4. 🌙 Testing MARKET CLOSE notification...")
        market_close_success = await notifier.send_market_close_notification({
            'total_trades': 12,
            'winning_trades': 8,
            'daily_pnl': 742.35,
            'best_trade': {'symbol': 'NVDA', 'pnl': 285.50},
            'worst_trade': {'symbol': 'META', 'pnl': -45.20},
            'final_portfolio_value': 104492.60
        })
        print(f"   ✅ Market close notification: {'SENT' if market_close_success else 'FAILED'}")
        
        await asyncio.sleep(2)
        
        # Test 5: Portfolio Update
        print("5. 📊 Testing PORTFOLIO update...")
        portfolio_success = await notifier.send_portfolio_update(
            total_value=103750.25,
            cash=28500.00,
            pnl_today=1250.75
        )
        print(f"   ✅ Portfolio notification: {'SENT' if portfolio_success else 'FAILED'}")
        
        await asyncio.sleep(2)
        
        # Test 6: AI Trade Alert (Signal Generated)
        print("6. 🤖 Testing AI TRADE ALERT...")
        recommendation = {
            'ticker': 'MSFT',
            'action': 'BUY',
            'entry': 410.50,
            'confidence': 0.85,
            'position_size': {'percentage': 0.05},
            'stop_loss': 395.00,
            'take_profit': 440.00
        }
        
        explanation = {
            'reasoning': 'Strong momentum breakout with high volume confirmation',
            'technical_factors': ['RSI oversold recovery', 'Volume spike', 'Support bounce'],
            'risk_level': 'Medium'
        }
        
        alert_success = await notifier.send_trade_alert(recommendation, explanation)
        print(f"   ✅ AI trade alert: {'SENT' if alert_success else 'FAILED'}")
        
        # Results Summary
        print("\n🎯 ENHANCED NOTIFICATION TEST RESULTS")
        print("-" * 40)
        total_tests = 6
        passed_tests = sum([buy_success, sell_success, session_start_success, 
                           market_close_success, portfolio_success, alert_success])
        
        print(f"Tests passed: {passed_tests}/{total_tests}")
        print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 ALL ENHANCED NOTIFICATIONS WORKING!")
            print("✅ You will receive detailed alerts for:")
            print("   • Buy orders with price predictions & AI analysis")
            print("   • Sell orders with profit analysis & performance assessment") 
            print("   • Trading session start with market conditions")
            print("   • Market close with daily performance summary")
            print("   • Portfolio value updates")
            print("   • AI-generated trading signals")
            print("   • System status updates")
        else:
            print("⚠️ Some notifications failed - check Telegram configuration")
            
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"❌ Notification test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_all_notifications())
    
    if result:
        print("\n🚀 Your notification system is ready for production trading!")
        print("📱 You'll be notified of all trades via Telegram")
    else:
        print("\n⚠️ Fix notification issues before starting autonomous trading")
    
    exit(0 if result else 1)
