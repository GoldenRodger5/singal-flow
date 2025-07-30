#!/usr/bin/env python3
"""
Production Telegram Signal Sender
Integrates with main trading system to send real signals with actionable buttons
"""
import requests
import json
import os
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

from services.telegram_trading import telegram_trading

load_dotenv()

class ProductionTelegramNotifier:
    """Production Telegram notifier that sends real trading signals."""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_trading_signal(self, recommendation: Dict[str, Any], explanation: str) -> bool:
        """Send a real trading signal with executable buttons."""
        try:
            ticker = recommendation['ticker']
            action = recommendation.get('action', 'BUY')
            entry_price = recommendation['entry']
            stop_loss = recommendation['stop_loss']
            take_profit = recommendation['take_profit']
            confidence = recommendation['confidence']
            position_size = recommendation.get('position_size', {})
            
            # Calculate position details
            position_pct = position_size.get('percentage', 0.05) * 100
            position_dollars = position_size.get('dollar_amount', 5000)
            
            # Calculate risk/reward
            risk = entry_price - stop_loss if action == 'BUY' else stop_loss - entry_price
            reward = take_profit - entry_price if action == 'BUY' else entry_price - take_profit
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Store the trade for execution
            callback_id = await telegram_trading.store_trade_signal(recommendation, explanation)
            
            # Create the signal message
            signal_message = f"""🚨 *LIVE TRADING SIGNAL* 🚨

📈 **{ticker} - {action.upper()} SIGNAL**
🔥 *HIGH CONFIDENCE ALERT*

💰 **Trade Setup:**
• Entry: ${entry_price:.2f}
• Target: ${take_profit:.2f} (+{((take_profit/entry_price - 1) * 100):+.1f}%)
• Stop: ${stop_loss:.2f} ({((stop_loss/entry_price - 1) * 100):+.1f}%)
• Size: ${position_dollars:,.0f} ({position_pct:.1f}% portfolio)

🧠 **AI Analysis:**
• Confidence: {confidence}/10 {"⭐" * int(confidence)}
• Risk/Reward: 1:{rr_ratio:.1f}
• Expected Value: Positive

📊 **Technical Signals:**
{explanation[:200]}...

⚡ **LIVE MARKET DATA** ⚡
• Real-time pricing via Polygon.io
• Alpaca trading integration ready
• Paper trading mode (safe)

⏰ **Generated:** {datetime.now().strftime('%H:%M:%S EST')}
🤖 **Source:** Signal Flow AI Bot

*Click below to execute or skip this trade:*"""

            # Create executable buttons with stored trade ID
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": f"✅ Execute {action} (${position_dollars:,.0f})", "callback_data": f"execute_{ticker}_{action}_{int(datetime.now().timestamp())}"},
                        {"text": "❌ Skip Signal", "callback_data": f"skip_{ticker}_{action}"}
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
            
            # Send the signal
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": signal_message,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(keyboard)
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                print(f"✅ Live trading signal sent: {ticker} {action}")
                return True
            else:
                print(f"❌ Failed to send signal: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending trading signal: {e}")
            return False
    
    async def send_execution_update(self, ticker: str, action: str, status: str, details: Dict[str, Any]) -> bool:
        """Send an update about trade execution."""
        try:
            if status == 'success':
                message = f"""✅ *TRADE EXECUTED SUCCESSFULLY* ✅

🎯 **{ticker} {action} COMPLETED**
💰 Shares: {details.get('shares', 'N/A')}
📊 Fill Price: ${details.get('fill_price', details.get('entry_price', 0)):.2f}
📋 Order ID: {details.get('order_id', 'N/A')}

🛡️ **Risk Management:**
• Stop Loss: ${details.get('stop_loss', 0):.2f}
• Take Profit: ${details.get('take_profit', 0):.2f}
• Max Risk: ${details.get('max_risk', 0):.2f}

⏰ **Execution Time:** {datetime.now().strftime('%H:%M:%S EST')}
🤖 **Status:** Position active, monitoring enabled"""
            
            elif status == 'failed':
                message = f"""❌ *TRADE EXECUTION FAILED* ❌

🚫 **{ticker} {action} REJECTED**
⚠️ **Error:** {details.get('error', 'Unknown error')}

🔧 **Possible Causes:**
• Insufficient buying power
• Market hours restriction
• Position size limits
• Broker connectivity

💡 **Next Steps:**
• Check account status
• Verify market hours
• Reduce position size
• Try manual execution"""
            
            else:
                message = f"📋 **{ticker} {action}** - Status: {status}"
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error sending execution update: {e}")
            return False
    
    async def send_market_update(self, message: str) -> bool:
        """Send a general market update."""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error sending market update: {e}")
            return False

# Global instance for use in main trading system
production_telegram = ProductionTelegramNotifier()
