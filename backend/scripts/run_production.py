#!/usr/bin/env python3
"""
Production Signal Flow Trading System
Combines market scanning with FastAPI Telegram webhook for instant execution
"""
import asyncio
import os
import threading
import time
from datetime import datetime
from loguru import logger

# Import main trading system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from main import SignalFlowOrchestrator

# Import FastAPI webhook system
from telegram_webhook import app
import uvicorn

def run_fastapi_server():
    """Run the FastAPI webhook server in a separate thread."""
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting FastAPI webhook server on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

def setup_webhook_on_startup():
    """Set up webhook when the system starts."""
    import requests
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Wait for server to be ready
    time.sleep(10)
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    railway_url = os.getenv('RAILWAY_STATIC_URL')
    
    if not railway_url:
        logger.warning("RAILWAY_STATIC_URL not set - webhook setup skipped")
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
            logger.info(f"✅ Webhook configured: {webhook_url}")
        else:
            logger.error(f"❌ Webhook setup failed: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")

async def run_trading_system():
    """Run the main trading system with periodic scans."""
    logger.info("🚀 Starting Signal Flow Trading System")
    
    orchestrator = SignalFlowOrchestrator()
    
    # Send startup notification
    try:
        from services.production_telegram import production_telegram
        
        startup_message = f"""🚀 *SIGNAL FLOW BOT STARTED* 🚀

✅ **System Status:** Online
⏰ **Started:** {datetime.now().strftime('%H:%M:%S EST')}
📡 **Mode:** {os.getenv('SYSTEM_MODE', 'paper_trading').upper()}
🎯 **Trading:** {"✅ Interactive" if os.getenv('INTERACTIVE_TRADING_ENABLED', 'true').lower() == 'true' else "⏸️ Disabled"}

🔧 **Configuration:**
• Min Confidence: {os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.7')}/10
• Max Daily Trades: {os.getenv('MAX_DAILY_TRADES', '25')}
• Position Size: {float(os.getenv('MAX_POSITION_SIZE_PCT', '0.10')) * 100:.0f}% max
• Risk per Trade: {float(os.getenv('STOP_LOSS_PCT', '0.02')) * 100:.0f}%

📊 **Data Sources:**
• Market Data: Polygon.io ✅
• Broker: Alpaca Markets ✅  
• AI: GPT-4o + Claude ✅

📱 **Notifications:**
• Telegram: ✅ Interactive buttons enabled
• SMS Backup: {"✅ Enabled" if os.getenv('SMS_TO') else "❌ Disabled"}

🎯 **Ready to scan market and send signals!**
All trades are paper trades for safe testing."""

        await production_telegram.send_market_update(startup_message)
        
    except Exception as e:
        logger.error(f"Failed to send startup notification: {e}")
    
    # Main trading loop
    while True:
        try:
            logger.info("🔍 Running market scan...")
            await orchestrator.run_market_scan()
            
            # Wait before next scan (configurable)
            scan_interval = int(os.getenv('SCAN_INTERVAL_SECONDS', '300'))  # 5 minutes default
            logger.info(f"⏳ Next scan in {scan_interval} seconds")
            await asyncio.sleep(scan_interval)
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry

async def main():
    """Main entry point for production system."""
    logger.info("🚀 Signal Flow Production System Starting...")
    
    # Start FastAPI server in background thread
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    fastapi_thread.start()
    
    # Start webhook setup in background
    webhook_thread = threading.Thread(target=setup_webhook_on_startup, daemon=True)
    webhook_thread.start()
    
    # Start trading system
    await run_trading_system()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Signal Flow system stopped by user")
    except Exception as e:
        logger.error(f"💥 System error: {e}")
        raise
