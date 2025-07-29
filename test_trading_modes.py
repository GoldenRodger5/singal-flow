"""
Test the new auto and interactive trading functionality.
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.config import Config
from services.interactive_trading import InteractiveTradingService
from services.alpaca_trading import AlpacaTradingService


async def test_auto_vs_interactive_trading():
    """Test both auto and interactive trading modes."""
    print("🚀 Testing Auto vs Interactive Trading Modes")
    print("=" * 60)
    
    config = Config()
    
    # Show current configuration
    print(f"📊 CURRENT SETTINGS:")
    print(f"   Auto Trading: {config.AUTO_TRADING_ENABLED}")
    print(f"   Interactive Trading: {config.INTERACTIVE_TRADING_ENABLED}")
    print(f"   Paper Trading: {config.PAPER_TRADING}")
    print(f"   Confirmation Timeout: {config.TRADE_CONFIRMATION_TIMEOUT}s")
    
    # Test interactive trading service
    print(f"\n🤖 Testing Interactive Trading Service...")
    
    interactive = InteractiveTradingService()
    
    # Create mock recommendation for testing
    mock_recommendation = {
        'ticker': 'TEST',
        'entry': 25.50,
        'stop_loss': 24.00,
        'take_profit': 28.00,
        'confidence': 9.2,
        'risk_reward_ratio': 2.5,
        'position_size': {'percentage': 0.15}
    }
    
    mock_explanation = """Strong VWAP bounce setup with bullish news sentiment. 
RSI oversold at 28.5 with significant volume spike. Technical indicators 
align for high-probability reversal play."""
    
    print(f"📱 Mock buy confirmation request will be sent...")
    print(f"   (In real scenario, you'd receive WhatsApp message)")
    print(f"   Sample message format:")
    print(f"""
🤖 SIGNAL FLOW - BUY CONFIRMATION NEEDED

📊 TICKER: TEST
💰 ENTRY: $25.50
🛑 STOP: $24.00
🎯 TARGET: $28.00
📈 R:R: 2.5:1
⭐ CONFIDENCE: 9.2/10
💼 POSITION: 15.0% of account

🧠 REASONING:
Strong VWAP bounce setup with bullish news sentiment...

⚡ RESPOND QUICKLY:
• Reply "YES" to BUY
• Reply "NO" to SKIP

⏰ Auto-expires in {config.TRADE_CONFIRMATION_TIMEOUT} seconds
""")
    
    # Test alpaca service connection
    print(f"\n📊 Testing Alpaca Connection...")
    try:
        alpaca = AlpacaTradingService()
        account_info = alpaca.get_account_info()
        
        if account_info:
            print(f"✅ Alpaca connected successfully")
            print(f"   Buying Power: ${account_info.get('buying_power', 0):,.2f}")
            print(f"   Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
            print(f"   Paper Trading: {config.PAPER_TRADING}")
        else:
            print(f"❌ Alpaca connection failed")
            
    except Exception as e:
        print(f"❌ Alpaca error: {e}")
    
    # Test affirmative phrase detection
    print(f"\n🗣️ Testing Response Recognition...")
    test_phrases = [
        ("yes", True),
        ("buy it", True), 
        ("go", True),
        ("no", False),
        ("skip", False),
        ("BUY NOW!", True),
        ("nope", False)
    ]
    
    for phrase, expected in test_phrases:
        result = interactive._is_affirmative(phrase)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{phrase}' -> {result} (expected: {expected})")
    
    print(f"\n🎯 TRADING MODE RECOMMENDATIONS:")
    print(f"   🔸 Start with: AUTO_TRADING=false, INTERACTIVE_TRADING=true")
    print(f"   🔸 Test interactive mode first with paper trading")
    print(f"   🔸 Once comfortable, can enable AUTO_TRADING=true")
    print(f"   🔸 Always keep PAPER_TRADING=true for safety")
    
    print(f"\n📱 TO ENABLE FEATURES:")
    print(f"   1. Edit .env file:")
    print(f"      AUTO_TRADING_ENABLED=true    (for automatic trading)")
    print(f"      INTERACTIVE_TRADING_ENABLED=true  (for confirmations)")
    print(f"   2. Restart main.py")
    print(f"   3. During market hours, system will use selected mode")
    
    print(f"\n⚡ RESPONSE SPEED:")
    print(f"   • Interactive mode: ~5-10 seconds for confirmation")
    print(f"   • Auto mode: ~1-2 seconds for execution")
    print(f"   • Both modes monitor exits in real-time")


if __name__ == "__main__":
    asyncio.run(test_auto_vs_interactive_trading())
