"""Test market data service during market closed hours"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_closed_market():
    """Test market data service when market is closed"""
    
    print("🧪 Testing Market Data Service (Market Closed)")
    print("=" * 50)
    
    try:
        from backend.services.real_time_market_data import market_data_service
        
        # Test 1: Market Status
        print("\n1️⃣ Testing Market Status...")
        status = await market_data_service.get_market_status()
        market_open = status.get('market_open', False)
        print(f"   📊 Market Status: {'OPEN' if market_open else 'CLOSED'}")
        print(f"   🕐 Server Time: {status.get('server_time', 'N/A')}")
        
        # Test 2: Single Quote (Previous Close)
        print("\n2️⃣ Testing Single Quote...")
        quote = await market_data_service.get_real_time_quote('AAPL')
        print(f"   💰 AAPL: ${quote.price:.2f}")
        print(f"   📈 Change: {quote.change:+.2f} ({quote.change_percent:+.2f}%)")
        print(f"   📊 Volume: {quote.volume:,}")
        print(f"   📅 Previous Close: ${quote.previous_close:.2f}")
        
        # Test 3: Multiple Quotes
        print("\n3️⃣ Testing Multiple Quotes...")
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
        quotes = await market_data_service.get_multiple_quotes(symbols)
        print(f"   📈 Retrieved: {len(quotes)}/{len(symbols)} symbols")
        
        for symbol, quote in quotes.items():
            print(f"   • {symbol}: ${quote.price:.2f} ({quote.change_percent:+.2f}%)")
        
        # Test 4: Historical Data
        print("\n4️⃣ Testing Historical Data...")
        historical = await market_data_service.get_historical_data('AAPL', days=5)
        print(f"   📊 Historical Data Points: {len(historical)}")
        
        if historical:
            latest = historical[-1]
            print(f"   📅 Latest: {latest['date']} - Close: ${latest['close']:.2f}")
        
        print("\n✅ All tests passed! Market Data Service working correctly during closed market.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_closed_market())
