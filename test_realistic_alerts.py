#!/usr/bin/env python3
"""
Test realistic trading notifications
"""
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

def send_trading_alert():
    """Send a realistic trading alert via SMS."""
    try:
        from twilio.rest import Client
        
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        
        # Realistic trading alert
        alert_message = f"""🚀 TRADE SIGNAL ALERT 🚀

📈 TSLA - BUY SIGNAL
💰 Entry: $248.50
🎯 Confidence: 9.2/10
💵 Position: $12,450 (12.5%)

📊 Targets:
🛡️  Stop Loss: $243.50 (-2.0%)
🎯 Take Profit: $258.50 (+4.0%)

🧠 Analysis:
• RSI oversold (22.3)
• VWAP bounce (+0.8%)  
• Volume spike 3.2x
• Bullish divergence

⏰ {datetime.now().strftime('%H:%M EST')}
🤖 Signal Flow Bot"""
        
        message = client.messages.create(
            body=alert_message,
            from_=os.getenv('SMS_FROM', '+1234567890'),
            to=os.getenv('SMS_TO', '+1987654321')
        )
        
        print("✅ Trading alert sent!")
        print(f"   Message ID: {message.sid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def send_profit_alert():
    """Send a profit notification."""
    try:
        from twilio.rest import Client
        
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        
        profit_message = f"""💰 PROFIT ALERT! 💰

✅ AAPL position CLOSED
📈 Entry: $150.25 → Exit: $156.40
💵 Profit: +$923 (+4.1%)
⏱️  Held: 2h 15m

📊 Today's Performance:
• Total P&L: +$1,247 (+1.2%)
• Win Rate: 75% (6/8 trades)
• Best Trade: NVDA +$445

🎯 Portfolio: $105,247 (+5.2% week)
⏰ {datetime.now().strftime('%H:%M EST')}"""
        
        message = client.messages.create(
            body=profit_message,
            from_=os.getenv('SMS_FROM', '+1234567890'),
            to=os.getenv('SMS_TO', '+1987654321')
        )
        
        print("✅ Profit alert sent!")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Realistic Trading Notifications")
    print("=" * 50)
    
    print("\n1. Sending trade signal alert...")
    send_trading_alert()
    
    print("\n2. Sending profit alert...")
    send_profit_alert()
    
    print("\n✅ Check your phone for realistic trading alerts!")
    print("This is what you'll receive when your bot trades live.")
