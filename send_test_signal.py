#!/usr/bin/env python3
"""
Send a test trading signal with interactive buttons
"""
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def send_test_signal():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Realistic trading signal with buttons
    message = f"""🚨 *NEW TRADING SIGNAL* 🚨

📈 **TSLA - TESLA INC**
🔥 *STRONG BUY SIGNAL*

💰 *Trade Details:*
• Entry: $245.80
• Target: $255.20 (+3.8%)
• Stop Loss: $240.15 (-2.3%)
• Position Size: $12,450 (15% of portfolio)

🧠 *AI Confidence: 8.7/10*

📊 *Why This Signal:*
• RSI oversold bounce (32 → 42)
• Volume spike +340% above average
• Breaking above 20-day MA
• Bullish divergence confirmed

⚡ *Time Sensitive - Expires in 5 minutes*

⏰ Generated: {datetime.now().strftime('%H:%M:%S EST')}"""

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Execute Trade ($12,450)", "callback_data": "execute_TSLA_BUY"},
                {"text": "❌ Skip Signal", "callback_data": "skip_TSLA_BUY"}
            ],
            [
                {"text": "📊 View Portfolio", "callback_data": "portfolio"},
                {"text": "⏸️ Pause Bot", "callback_data": "pause_bot"}
            ],
            [
                {"text": "🔍 Scan Market", "callback_data": "scan_market"},
                {"text": "⚙️ Settings", "callback_data": "settings"}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("✅ Test signal sent successfully!")
        print("🔘 Now click the buttons to test the handler")
        return True
    else:
        print(f"❌ Failed to send signal: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    send_test_signal()
