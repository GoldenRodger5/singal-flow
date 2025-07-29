#!/usr/bin/env python3
"""
Deploy and configure Telegram webhook on Railway
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def set_webhook_url():
    """Set the webhook URL for the deployed Railway app."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Get Railway URL from environment or prompt user
    railway_url = os.getenv('RAILWAY_STATIC_URL')
    
    if not railway_url:
        print("❌ RAILWAY_STATIC_URL not found in environment")
        print("💡 You'll need to set this after Railway deployment")
        print("🔗 Format: https://your-app-name.up.railway.app")
        return False
    
    webhook_url = f"{railway_url}/webhook"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook configured successfully!")
            print(f"🔗 URL: {webhook_url}")
            print(f"📋 Response: {result}")
            return True
        else:
            print(f"❌ Failed to set webhook: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

def check_webhook_status():
    """Check current webhook configuration."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(url)
        
        if response.status_code == 200:
            info = response.json()['result']
            print("📊 Current Webhook Status:")
            print(f"🔗 URL: {info.get('url', 'Not set')}")
            print(f"✅ Has certificate: {info.get('has_custom_certificate', False)}")
            print(f"📡 Pending updates: {info.get('pending_update_count', 0)}")
            print(f"🕐 Last error: {info.get('last_error_date', 'None')}")
            print(f"❌ Error message: {info.get('last_error_message', 'None')}")
            return True
        else:
            print(f"❌ Failed to get webhook info: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking webhook: {e}")
        return False

def remove_webhook():
    """Remove the current webhook (switch back to polling)."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        response = requests.post(url)
        
        if response.status_code == 200:
            print("✅ Webhook removed successfully!")
            print("🔄 Bot is now in polling mode")
            return True
        else:
            print(f"❌ Failed to remove webhook: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error removing webhook: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Telegram Webhook Configuration")
    print("=" * 40)
    
    print("\n1. 📊 Checking current webhook status...")
    check_webhook_status()
    
    print("\n2. 🔗 Setting up webhook...")
    success = set_webhook_url()
    
    if success:
        print("\n🎉 Webhook setup complete!")
        print("📱 Telegram buttons will now respond instantly")
        print("⚡ FastAPI server is ready for production")
    else:
        print("\n⚠️ Webhook setup incomplete")
        print("💡 Manual setup may be required after Railway deployment")
