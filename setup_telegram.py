#!/usr/bin/env python3
"""
Quick Telegram setup for Isaac's trading bot
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def get_chat_id():
    """Get your chat ID from Telegram."""
    bot_token = "8413143996:AAFS1o9P5rXtVw0-3N3gseDoMaGhm62Mdf4"
    
    print("🤖 Getting your Telegram Chat ID...")
    print()
    print("📱 STEP 1: Open Telegram and go to: t.me/Isaac_training_bot")
    print("📝 STEP 2: Send any message to your bot (like 'hello')")
    print("⏳ STEP 3: Press Enter here after sending the message...")
    
    input()
    
    try:
        # Get updates from Telegram
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url)
        data = response.json()
        
        if data['ok'] and data['result']:
            # Get the most recent message
            latest_update = data['result'][-1]
            chat_id = latest_update['message']['chat']['id']
            username = latest_update['message']['from'].get('username', 'Unknown')
            
            print(f"✅ Found your Chat ID: {chat_id}")
            print(f"👤 Username: @{username}")
            
            # Update .env file
            update_env_file(chat_id)
            
            # Send test message
            send_test_message(bot_token, chat_id)
            
            return chat_id
        else:
            print("❌ No messages found. Make sure you sent a message to your bot first.")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def update_env_file(chat_id):
    """Update the .env file with the chat ID."""
    try:
        # Read current .env
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        # Update the chat ID line
        updated_lines = []
        for line in lines:
            if line.startswith('TELEGRAM_CHAT_ID='):
                updated_lines.append(f'TELEGRAM_CHAT_ID={chat_id}\n')
            else:
                updated_lines.append(line)
        
        # Write back to .env
        with open('.env', 'w') as f:
            f.writelines(updated_lines)
        
        print(f"✅ Updated .env file with Chat ID: {chat_id}")
        
    except Exception as e:
        print(f"❌ Error updating .env: {e}")

def send_test_message(bot_token, chat_id):
    """Send a test message with trading alert format."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        message = """🚀 *SIGNAL FLOW BOT ACTIVATED* 🚀

✅ Your trading bot is now connected!
📱 You'll receive interactive trading alerts here

🔧 *Next Steps:*
• Bot will send trade signals with buttons
• Tap ✅ to execute or ❌ to skip
• Send /status for portfolio updates
• Send /help for all commands

💰 *Sample Alert Preview:*
📈 AAPL BUY Signal
💵 $15,000 position
🎯 Confidence: 8.5/10

Ready to start paper trading! 🎯"""

        # Create inline keyboard for test
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ I'm Ready!", "callback_data": "ready"},
                    {"text": "📊 Show Commands", "callback_data": "commands"}
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
            print("✅ Test message sent! Check your Telegram.")
            print("🎉 Your trading bot notifications are ready!")
        else:
            print(f"❌ Failed to send test message: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending test: {e}")

if __name__ == "__main__":
    print("🤖 TELEGRAM BOT SETUP")
    print("=" * 40)
    print()
    
    get_chat_id()
