#!/usr/bin/env python3
"""
Test realistic trading notifications with Telegram
"""
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def send_realistic_trading_alert():
    """Send a realistic trading alert to Telegram."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Telegram not configured")
        return False
    
    # Realistic trading alert
    message = f"""🚀 *TRADING SIGNAL DETECTED* 🚀

📈 *TSLA - BUY SIGNAL*
💰 Entry: $248.50
🎯 Confidence: 9.2/10 ⭐⭐⭐⭐⭐
💵 Position: $12,450 (12.5% of portfolio)

📊 *Technical Analysis:*
🔴 RSI Oversold: 22.3 (Strong)
🟢 VWAP Bounce: +0.8% above
📈 Volume Spike: 3.2x average
🎯 MACD Bullish Cross

📋 *Trade Plan:*
🛡️ Stop Loss: $243.50 (-2.0%)
🎯 Take Profit: $258.50 (+4.0%)
⚡ Risk/Reward: 1:2.0 (Excellent)

🧠 *AI Reasoning:*
Market regime shows trending momentum with low volatility. Technical indicators align bullishly with institutional volume confirmation.

⏰ *Signal Time:* {datetime.now().strftime('%H:%M:%S EST')}
🤖 Signal Flow Bot"""

    # Interactive buttons for trading decisions
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Execute Trade", "callback_data": "execute_TSLA_BUY"},
                {"text": "❌ Skip Trade", "callback_data": "skip_TSLA_BUY"}
            ],
            [
                {"text": "📊 Show Portfolio", "callback_data": "portfolio"},
                {"text": "⏸️ Pause Bot", "callback_data": "pause_bot"}
            ],
            [
                {"text": "📈 Chart Analysis", "callback_data": "chart_TSLA"},
                {"text": "ℹ️ More Info", "callback_data": "info_TSLA"}
            ]
        ]
    }
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(keyboard)
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("✅ Trading alert sent to Telegram!")
            print("📱 Check your phone - you should see interactive buttons")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def send_profit_update():
    """Send a profit/loss update."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    message = f"""💰 *TRADE CLOSED - PROFIT!* 💰

✅ *AAPL Position Closed*
📈 Entry: $150.25 → Exit: $156.40
💵 Profit: +$923 (+4.1%)
⏱️ Duration: 2h 15m

📊 *Today's Performance:*
💰 Total P&L: +$1,247 (+1.2%)
🎯 Win Rate: 75% (6/8 trades)
🏆 Best Trade: NVDA +$445
📉 Worst Trade: SIRI -$89

📈 *Portfolio Status:*
💼 Account Value: $105,247
📊 Day Change: +5.2%
💵 Available Cash: $23,450
🎯 Active Positions: 2

⏰ {datetime.now().strftime('%H:%M:%S EST')}"""

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📊 Full Portfolio", "callback_data": "portfolio_full"},
                {"text": "📈 Performance Chart", "callback_data": "performance"}
            ],
            [
                {"text": "🔍 Find New Signals", "callback_data": "scan_market"},
                {"text": "⚙️ Settings", "callback_data": "settings"}
            ]
        ]
    }
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(keyboard)
        }
        
        response = requests.post(url, json=payload)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending profit update: {e}")
        return False

def test_command_responses():
    """Test command-style interactions."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    status_message = f"""📊 *BOT STATUS REPORT* 📊

🤖 *System Status:* ✅ Active
🕐 *Running Since:* 9:30 AM EST
📡 *Mode:* Paper Trading (Safe)
🎯 *Automation:* Supervised

📈 *Today's Activity:*
🔍 Stocks Scanned: 1,247
📊 Signals Generated: 12
✅ Trades Executed: 6
⏸️ Trades Skipped: 6

🎯 *Current Settings:*
💰 Max Position: 15% portfolio
🛡️ Risk Per Trade: 2%
🎯 Min Confidence: 7.0/10
⏱️ Max Daily Trades: 25

⚙️ *Next Scan:* 30 seconds
📱 *Notifications:* Telegram ✅

Type /help for commands"""

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": status_message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending status: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Telegram Trading Notifications")
    print("=" * 50)
    
    print("\n1. 🚀 Sending trading signal alert...")
    success1 = send_realistic_trading_alert()
    
    print("\n2. 💰 Sending profit update...")
    success2 = send_profit_update()
    
    print("\n3. 📊 Sending status update...")
    success3 = test_command_responses()
    
    print(f"\n📋 Results: {sum([success1, success2, success3])}/3 messages sent")
    
    if success1 and success2 and success3:
        print("\n🎉 Perfect! Your Telegram bot is fully operational!")
        print("📱 Check your phone for interactive trading notifications")
        print("✅ You can now approve/reject trades with a tap")
    else:
        print("\n⚠️ Some messages failed - check Telegram configuration")
