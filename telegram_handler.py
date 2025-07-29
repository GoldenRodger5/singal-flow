#!/usr/bin/env python3
"""
Telegram bot callback handler - responds to button clicks
"""
import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class TelegramBotHandler:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = 0
        
    def get_updates(self):
        """Get updates from Telegram (including button clicks)."""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 10
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
            else:
                print(f"❌ Failed to get updates: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting updates: {e}")
            return []
    
    def send_message(self, text, reply_markup=None):
        """Send a message to Telegram."""
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
            print(f"❌ Error sending message: {e}")
            return False
    
    def answer_callback_query(self, callback_query_id, text=""):
        """Answer a callback query (button click)."""
        try:
            url = f"{self.base_url}/answerCallbackQuery"
            payload = {
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": False
            }
            
            response = requests.post(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error answering callback: {e}")
            return False
    
    def handle_callback(self, callback_data, callback_query_id):
        """Handle button click callbacks."""
        print(f"🔘 Button clicked: {callback_data}")
        
        if callback_data.startswith("execute_"):
            # Extract ticker and action
            parts = callback_data.split("_")
            ticker = parts[1] if len(parts) > 1 else "UNKNOWN"
            action = parts[2] if len(parts) > 2 else "BUY"
            
            response_text = f"✅ *TRADE EXECUTED*\n\n🚀 {ticker} {action} order placed!\n💰 Position: $12,450\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            self.send_message(response_text)
            self.answer_callback_query(callback_query_id, f"✅ {ticker} trade executed!")
            
        elif callback_data.startswith("skip_"):
            parts = callback_data.split("_")
            ticker = parts[1] if len(parts) > 1 else "UNKNOWN"
            
            response_text = f"❌ *TRADE SKIPPED*\n\n⏭️ {ticker} signal ignored\n🔍 Searching for next opportunity...\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            self.send_message(response_text)
            self.answer_callback_query(callback_query_id, f"❌ {ticker} trade skipped")
            
        elif callback_data == "portfolio":
            portfolio_text = f"""📊 *PORTFOLIO STATUS*

💼 *Account Summary:*
💰 Total Value: $105,247
📈 Day P&L: +$1,247 (+1.2%)
💵 Available Cash: $23,450
🎯 Buying Power: $89,320

📈 *Open Positions:*
• TSLA: +$445 (+3.2%)
• NVDA: -$125 (-0.8%)
• AAPL: +$89 (+0.6%)

📊 *Performance:*
🏆 Win Rate: 75%
📈 Total Return: +15.2%
⚡ Best Day: +$2,340
🛡️ Max Drawdown: -2.1%

⏰ Updated: {datetime.now().strftime('%H:%M:%S EST')}"""

            self.send_message(portfolio_text)
            self.answer_callback_query(callback_query_id, "📊 Portfolio updated")
            
        elif callback_data == "pause_bot":
            pause_text = f"""⏸️ *BOT PAUSED*

🛑 Trading bot is now paused
⏰ Paused at: {datetime.now().strftime('%H:%M:%S EST')}
📊 No new signals will be generated
💡 Existing positions remain active

To resume trading, click the button below."""

            keyboard = {
                "inline_keyboard": [
                    [{"text": "▶️ Resume Trading", "callback_data": "resume_bot"}]
                ]
            }
            
            self.send_message(pause_text, keyboard)
            self.answer_callback_query(callback_query_id, "⏸️ Bot paused")
            
        elif callback_data == "resume_bot":
            resume_text = f"""▶️ *BOT RESUMED*

✅ Trading bot is now active
⏰ Resumed at: {datetime.now().strftime('%H:%M:%S EST')}
🔍 Scanning for new opportunities
📱 You'll receive signal alerts here"""

            self.send_message(resume_text)
            self.answer_callback_query(callback_query_id, "▶️ Bot resumed")
            
        elif callback_data == "scan_market":
            scan_text = f"""🔍 *MARKET SCAN INITIATED*

🕐 Scanning 1,247 stocks...
📊 Analyzing technical indicators...
🧠 AI processing market sentiment...

⏳ Estimated completion: 2-3 minutes
📱 New signals will appear here automatically

Current focus:
• Tech sector momentum
• RSI oversold conditions  
• Volume spike confirmations"""

            self.send_message(scan_text)
            self.answer_callback_query(callback_query_id, "🔍 Market scan started")
            
        elif callback_data == "settings":
            settings_text = f"""⚙️ *BOT SETTINGS*

🎯 *Risk Management:*
• Max position size: 15%
• Risk per trade: 2%
• Stop loss: 2%
• Take profit: 2:1 ratio

🤖 *Trading Rules:*
• Min confidence: 7.0/10
• Max daily trades: 25
• Trading hours: 9:30-16:00 EST
• Mode: Paper trading

📱 *Notifications:*
• Telegram: ✅ Enabled
• Signal alerts: ✅ Enabled
• Profit updates: ✅ Enabled

To modify settings, send /config"""

            self.send_message(settings_text)
            self.answer_callback_query(callback_query_id, "⚙️ Settings displayed")
            
        else:
            # Unknown callback
            self.answer_callback_query(callback_query_id, f"Command: {callback_data}")
    
    def process_updates(self, updates):
        """Process all updates from Telegram."""
        for update in updates:
            self.last_update_id = update['update_id']
            
            # Handle callback queries (button clicks)
            if 'callback_query' in update:
                callback_query = update['callback_query']
                callback_data = callback_query['data']
                callback_query_id = callback_query['id']
                
                self.handle_callback(callback_data, callback_query_id)
            
            # Handle regular messages
            elif 'message' in update:
                message = update['message']
                text = message.get('text', '')
                
                if text.startswith('/'):
                    self.handle_command(text)
    
    def handle_command(self, command):
        """Handle text commands like /status, /help."""
        command = command.lower().strip()
        
        if command == '/status':
            status_text = f"""📊 *BOT STATUS*

🤖 Status: ✅ Active
🕐 Running: 2h 45m
📡 Mode: Paper Trading
🎯 Automation: Interactive

📈 *Today's Activity:*
🔍 Scanned: 1,247 stocks
📊 Signals: 12 generated
✅ Executed: 6 trades
💰 P&L: +$1,247

⏰ {datetime.now().strftime('%H:%M:%S EST')}"""
            
            self.send_message(status_text)
            
        elif command == '/help':
            help_text = """🤖 *SIGNAL FLOW BOT COMMANDS*

📊 *Status Commands:*
/status - Bot and portfolio status
/portfolio - Full portfolio view
/performance - Trading performance

🎛️ *Control Commands:*
/pause - Pause trading
/resume - Resume trading
/scan - Force market scan

⚙️ *Settings:*
/config - Trading settings
/risk - Risk management
/alerts - Notification settings

💡 *Tips:*
• Use buttons for quick actions
• Bot runs automatically during market hours
• All trades are paper trading (safe)"""
            
            self.send_message(help_text)
        
        elif command == '/portfolio':
            self.handle_callback('portfolio', None)
    
    def run_listener(self):
        """Run the bot listener to handle button clicks."""
        print("🤖 Starting Telegram bot listener...")
        print("📱 Click buttons in Telegram to test responses")
        print("⏹️  Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                updates = self.get_updates()
                
                if updates:
                    print(f"📨 Received {len(updates)} update(s)")
                    self.process_updates(updates)
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n⏹️  Bot listener stopped")

if __name__ == "__main__":
    handler = TelegramBotHandler()
    handler.run_listener()
