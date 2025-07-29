#!/usr/bin/env python3
"""
Test the production Telegram integration with real data
"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from services.production_telegram import production_telegram

load_dotenv()

async def test_production_signal():
    """Test sending a production signal."""
    
    # Simulate a real trading recommendation
    recommendation = {
        'ticker': 'TSLA',
        'action': 'BUY',
        'entry': 248.50,
        'stop_loss': 243.50,
        'take_profit': 258.50,
        'confidence': 8.7,
        'position_size': {
            'percentage': 0.125,  # 12.5% of portfolio
            'dollar_amount': 12450
        },
        'risk_reward_ratio': 2.0
    }
    
    explanation = """Strong bullish momentum detected:
• RSI oversold bounce (32 → 42)
• Volume spike +340% above average  
• Breaking above 20-day moving average
• Bullish MACD divergence confirmed
• Institutional volume pattern suggests accumulation
• Technical confluence at key support level"""
    
    print("🧪 Testing production Telegram signal...")
    success = await production_telegram.send_trading_signal(recommendation, explanation)
    
    if success:
        print("✅ Production signal sent successfully!")
        print("📱 Check Telegram for the interactive trading signal")
        print("🔘 The buttons will now execute real trades (paper mode)")
    else:
        print("❌ Failed to send production signal")

async def test_execution_update():
    """Test sending an execution update."""
    
    details = {
        'shares': 50,
        'fill_price': 248.75,
        'entry_price': 248.50,
        'stop_loss': 243.50,
        'take_profit': 258.50,
        'order_id': 'TEST_ORDER_123',
        'max_risk': 250.00
    }
    
    print("🧪 Testing execution update...")
    success = await production_telegram.send_execution_update('TSLA', 'BUY', 'success', details)
    
    if success:
        print("✅ Execution update sent successfully!")
    else:
        print("❌ Failed to send execution update")

async def test_market_update():
    """Test sending a market update."""
    
    message = f"""📊 *MARKET SCAN COMPLETE* 📊

🔍 **Scan Results:**
• Stocks analyzed: 1,247
• Signals found: 3
• High confidence: 1 (TSLA)
• Medium confidence: 2

📈 **Market Conditions:**
• VIX: 18.5 (Low volatility)
• SPY: +0.8% (Bullish trend)
• Volume: Above average
• Sector leaders: Tech, Energy

⏰ **Next scan:** 5 minutes
🎯 **Status:** Ready for signals

⚡ Powered by live market data"""

    print("🧪 Testing market update...")
    success = await production_telegram.send_market_update(message)
    
    if success:
        print("✅ Market update sent successfully!")
    else:
        print("❌ Failed to send market update")

async def main():
    """Run all tests."""
    print("🚀 Testing Production Telegram Integration")
    print("=" * 50)
    
    print("\n1. 📊 Testing trading signal...")
    await test_production_signal()
    
    await asyncio.sleep(2)
    
    print("\n2. ✅ Testing execution update...")
    await test_execution_update()
    
    await asyncio.sleep(2)
    
    print("\n3. 📈 Testing market update...")
    await test_market_update()
    
    print("\n🎉 Production tests complete!")
    print("📱 Check your Telegram for all the messages")
    print("🔘 Test the buttons to verify webhook integration")

if __name__ == "__main__":
    asyncio.run(main())
