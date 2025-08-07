"""Test Polygon Stocks Starter API integration"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_polygon_stocks_starter():
    """Test the Polygon API with Stocks Starter account."""
    print("🧪 Testing Polygon Stocks Starter API Access...")
    print("=" * 60)
    
    try:
        from backend.services.real_time_market_data import market_data_service
        
        # Test 1: Market Status
        print("\n1️⃣ Testing Market Status...")
        status = await market_data_service.get_market_status()
        market_open = status.get('market_open', False)
        print(f"   📊 Market Status: {'OPEN' if market_open else 'CLOSED'}")
        print(f"   🕐 Server Time: {status.get('server_time', 'N/A')}")
        
        # Test 2: Real-time Quote - AAPL
        print("\n2️⃣ Testing Real-time Quote for AAPL...")
        aapl = await market_data_service.get_real_time_quote('AAPL')
        print(f"   💰 AAPL: ${aapl.price:.2f}")
        print(f"   📈 Change: {aapl.change:+.2f} ({aapl.change_percent:+.2f}%)")
        print(f"   📊 Volume: {aapl.volume:,}")
        print(f"   📅 Timestamp: {aapl.timestamp}")
        
        # Test 3: Real-time Quote - TSLA
        print("\n3️⃣ Testing Real-time Quote for TSLA...")
        tsla = await market_data_service.get_real_time_quote('TSLA')
        print(f"   💰 TSLA: ${tsla.price:.2f}")
        print(f"   📈 Change: {tsla.change:+.2f} ({tsla.change_percent:+.2f}%)")
        print(f"   📊 Volume: {tsla.volume:,}")
        
        # Test 4: Multiple Quotes
        print("\n4️⃣ Testing Multiple Quotes...")
        symbols = ['SPY', 'QQQ', 'NVDA']
        quotes = await market_data_service.get_multiple_quotes(symbols)
        
        for symbol in symbols:
            if symbol in quotes:
                quote = quotes[symbol]
                print(f"   📈 {symbol}: ${quote.price:.2f} ({quote.change_percent:+.2f}%)")
            else:
                print(f"   ❌ {symbol}: No data")
        
        # Test 5: Historical Data
        print("\n5️⃣ Testing Historical Data...")
        historical = await market_data_service.get_historical_data('AAPL', days=5)
        print(f"   📊 Retrieved {len(historical)} days of AAPL historical data")
        if historical:
            latest = historical[-1]
            print(f"   📅 Latest: {latest['date']} - Close: ${latest['close']:.2f}")
        
        print("\n🎉 All Polygon Stocks Starter API tests completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_polygon_stocks_starter())
