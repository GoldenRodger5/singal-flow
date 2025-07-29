#!/usr/bin/env python3
"""
Discord webhook notifications - much simpler than Twilio
"""
import requests
import json
from datetime import datetime

def send_discord_alert(webhook_url, trade_data):
    """Send trading alert to Discord channel."""
    try:
        # Create rich Discord message
        embed = {
            "title": f"🚀 {trade_data['ticker']} {trade_data['signal']} Signal",
            "description": f"Confidence: {trade_data['confidence']}/10",
            "color": 0x00ff00 if trade_data['signal'] == 'BUY' else 0xff0000,
            "fields": [
                {
                    "name": "💰 Entry Price",
                    "value": f"${trade_data['price']}",
                    "inline": True
                },
                {
                    "name": "💵 Position Size",
                    "value": f"${trade_data['position_size']:,}",
                    "inline": True
                },
                {
                    "name": "🛡️ Stop Loss",
                    "value": f"${trade_data['stop_loss']}",
                    "inline": True
                },
                {
                    "name": "🎯 Take Profit",
                    "value": f"${trade_data['take_profit']}",
                    "inline": True
                },
                {
                    "name": "🧠 Analysis",
                    "value": trade_data['reasoning'],
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Signal Flow Bot • {datetime.now().strftime('%H:%M EST')}"
            }
        }
        
        payload = {
            "content": "📱 **New Trading Signal** - React with ✅ to execute or ❌ to skip",
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 204:
            print("✅ Discord alert sent!")
            return True
        else:
            print(f"❌ Discord failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Discord error: {e}")
        return False

def test_discord_alert():
    """Test Discord notification."""
    # You'll get this URL from Discord channel settings
    webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
    
    sample_trade = {
        'ticker': 'AAPL',
        'signal': 'BUY',
        'price': 150.25,
        'confidence': 8.5,
        'position_size': 15000,
        'stop_loss': 147.25,
        'take_profit': 156.25,
        'reasoning': 'RSI oversold + VWAP bounce + volume spike 3.2x'
    }
    
    print("📱 Discord webhook test:")
    print("Note: Set up webhook URL in Discord channel settings")
    print(f"Would send: {sample_trade['ticker']} {sample_trade['signal']} alert")

if __name__ == "__main__":
    test_discord_alert()
