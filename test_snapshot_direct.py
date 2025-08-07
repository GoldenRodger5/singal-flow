#!/usr/bin/env python3
"""
Test the working real-time snapshot endpoint directly
Tests Polygon /v2/snapshot API with Stocks Starter account
"""

import asyncio
import aiohttp
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv('.env')

async def test_snapshot_endpoint():
    """Test the working snapshot endpoint directly."""
    print("\n🔄 Testing Real-time Snapshot Endpoint...")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    
    if not api_key:
        print("❌ ERROR: POLYGON_API_KEY not found in environment")
        return
    
    print(f"✅ API Key loaded: {api_key[:8]}...")
    
    # Test symbols
    test_symbols = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT']
    
    base_url = "https://api.polygon.io"
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        for symbol in test_symbols:
            print(f"\n📊 Testing {symbol}...")
            
            try:
                # Use the working snapshot endpoint
                url = f"{base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
                params = {'apikey': api_key}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'ticker' in data and data['ticker']:
                            ticker_data = data['ticker']
                            
                            # Extract data
                            last_quote = ticker_data.get('lastQuote', {})
                            last_trade = ticker_data.get('lastTrade', {})
                            day_data = ticker_data.get('day', {})
                            prev_day = ticker_data.get('prevDay', {})
                            
                            # Get current price
                            current_price = float(last_trade.get('p', 0))
                            if current_price == 0:
                                current_price = float(last_quote.get('p', 0))
                            
                            volume = int(day_data.get('v', 0))
                            previous_close = float(prev_day.get('c', current_price))
                            change = current_price - previous_close
                            change_percent = (change / previous_close * 100) if previous_close > 0 else 0
                            
                            print(f"  ✅ SUCCESS: {symbol}")
                            print(f"     Price: ${current_price:.2f}")
                            print(f"     Change: {change:+.2f} ({change_percent:+.2f}%)")
                            print(f"     Volume: {volume:,}")
                            print(f"     Range: ${day_data.get('l', 0):.2f} - ${day_data.get('h', 0):.2f}")
                            print(f"     Previous Close: ${previous_close:.2f}")
                            
                            # Get timestamp
                            trade_time = last_trade.get('t', 0)
                            if trade_time:
                                timestamp = datetime.fromtimestamp(trade_time / 1000)
                                print(f"     Last Trade: {timestamp}")
                            
                            results.append({
                                'symbol': symbol,
                                'success': True,
                                'price': current_price,
                                'change': change,
                                'change_percent': change_percent,
                                'volume': volume
                            })
                        else:
                            print(f"  ❌ FAILED: {symbol} - No ticker data")
                            results.append({'symbol': symbol, 'success': False, 'error': 'No ticker data'})
                            
                    else:
                        error_text = await response.text()
                        print(f"  ❌ HTTP {response.status}: {error_text[:100]}")
                        results.append({
                            'symbol': symbol, 
                            'success': False, 
                            'error': f'HTTP {response.status}'
                        })
                        
            except Exception as e:
                print(f"  ❌ ERROR: {symbol} - {str(e)}")
                results.append({'symbol': symbol, 'success': False, 'error': str(e)})
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.1)
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n📈 REAL-TIME SNAPSHOT ENDPOINT TEST:")
    print("=" * 50)
    print(f"Total symbols tested: {len(test_symbols)}")
    print(f"Successful: {successful}/{len(test_symbols)}")
    print(f"Success rate: {successful/len(test_symbols)*100:.1f}%")
    
    if successful > 0:
        print("\n🎉 REAL-TIME SNAPSHOT ENDPOINT WORKING!")
        print("✅ /v2/snapshot endpoint accessible with Stocks Starter")
        print("✅ Real market prices being retrieved")
        print("✅ Full market data available")
        print("\n💡 This endpoint provides:")
        print("   • Current price from last trade")
        print("   • Daily volume")
        print("   • Day high/low/open")
        print("   • Previous close")
        print("   • Real-time quotes")
        
        # Show best performing stocks
        gainers = [r for r in results if r['success'] and r.get('change_percent', 0) > 0]
        if gainers:
            best_gainer = max(gainers, key=lambda x: x['change_percent'])
            print(f"\n📈 Today's best performer: {best_gainer['symbol']} (+{best_gainer['change_percent']:.2f}%)")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_snapshot_endpoint())
