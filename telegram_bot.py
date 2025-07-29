#!/usr/bin/env python3
"""
Telegram bot for trading alerts - easier than WhatsApp
"""
import requests
import json
from datetime import datetime

class TelegramBot:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text, reply_markup=None):
        """Send message to Telegram."""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            
            response = requests.post(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def send_trading_alert(self, trade_data):
        """Send trading alert with action buttons."""
        message = f"""🚀 *TRADING SIGNAL* 🚀

📈 *{trade_data['ticker']} - {trade_data['signal']}*
💰 Entry: ${trade_data['price']}
🎯 Confidence: {trade_data['confidence']}/10
💵 Position: ${trade_data['position_size']:,}

📊 *Targets:*
🛡️ Stop Loss: ${trade_data['stop_loss']}
🎯 Take Profit: ${trade_data['take_profit']}

🧠 *Analysis:*
{trade_data['reasoning']}

⏰ {datetime.now().strftime('%H:%M EST')}"""

        # Interactive buttons
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Execute Trade", "callback_data": f"execute_{trade_data['ticker']}"},
                    {"text": "❌ Skip Trade", "callback_data": f"skip_{trade_data['ticker']}"}
                ],
                [
                    {"text": "⏸️ Pause Bot", "callback_data": "pause_bot"},
                    {"text": "📊 Show Portfolio", "callback_data": "show_portfolio"}
                ]
            ]
        }
        
        return self.send_message(message, keyboard)

def setup_telegram_instructions():
    """Instructions for setting up Telegram bot."""
    print("""
🤖 TELEGRAM BOT SETUP (5 minutes):

1. Open Telegram app
2. Search for @BotFather
3. Send /newbot
4. Choose a name like "MyTradingBot"
5. Choose username like "my_trading_bot_123"
6. Copy the bot token (looks like: 123456789:ABC...)

7. Start a chat with your new bot
8. Send any message to it
9. Go to: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
10. Find your chat_id in the response

Add to your .env:
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

Then you can:
• Get instant trading alerts
• Tap buttons to approve/reject trades
• Query your portfolio anytime
• Much easier than Twilio!
""")

def test_telegram_setup():
    """Test Telegram bot setup."""
    bot_token = "YOUR_BOT_TOKEN"  # Get from @BotFather
    chat_id = "YOUR_CHAT_ID"      # Get from getUpdates
    
    if bot_token == "YOUR_BOT_TOKEN":
        setup_telegram_instructions()
        return
    
    bot = TelegramBot(bot_token, chat_id)
    
    sample_trade = {
        'ticker': 'TSLA',
        'signal': 'BUY',
        'price': 248.50,
        'confidence': 9.2,
        'position_size': 12450,
        'stop_loss': 243.50,
        'take_profit': 258.50,
        'reasoning': 'RSI oversold (22.3) + VWAP bounce + volume spike 3.2x'
    }
    
    success = bot.send_trading_alert(sample_trade)
    
    if success:
        print("✅ Telegram alert sent with action buttons!")
    else:
        print("❌ Telegram setup needed")

if __name__ == "__main__":
    test_telegram_setup()
