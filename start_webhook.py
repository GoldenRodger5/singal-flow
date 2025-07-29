#!/usr/bin/env python3
"""
Railway startup script for Telegram webhook bot
"""
import os
import time
import requests
from telegram_webhook import app
import uvicorn
import asyncio

def setup_webhook_on_startup():
    """Set up webhook when Railway app starts."""
    # Wait a bit for the server to be fully ready
    time.sleep(10)
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    railway_url = os.getenv('RAILWAY_STATIC_URL')
    
    if not railway_url:
        # Try to detect Railway URL from PORT
        port = os.getenv('PORT', '8000')
        print(f"⚠️ RAILWAY_STATIC_URL not set, server running on port {port}")
        return
    
    webhook_url = f"{railway_url}/webhook"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print(f"✅ Webhook configured: {webhook_url}")
        else:
            print(f"❌ Webhook setup failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print("🚀 Starting Signal Flow Telegram Bot")
    print(f"📡 Port: {port}")
    print(f"🔗 Webhook will be configured automatically")
    
    # Start webhook setup in background
    import threading
    threading.Thread(target=setup_webhook_on_startup, daemon=True).start()
    
    # Start the FastAPI server
    uvicorn.run(
        "telegram_webhook:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
