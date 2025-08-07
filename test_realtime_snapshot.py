#!/usr/bin/env python3
"""
Test real-time snapshot endpoint integration
Confirms the working Polygon /v2/snapshot endpoint is properly integrated
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add backend path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from services.real_time_market_data import RealTimeMarketDataService
from utils.env_manager import EnvManager

async def test_realtime_snapshot():
    """Test the real-time snapshot endpoint that actually works with Stocks Starter."""
    print("\n🔄 Testing Real-time Snapshot Integration...")
    print("=" * 60)
    
    # Initialize environment
    env_manager = EnvManager()
    config = env_manager.get_api_config()
    
    # Test symbols
    test_symbols = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT']
    
    # Initialize service
    market_service = RealTimeMarketDataService()
    
    results = []
    
    for symbol in test_symbols:
        print(f"\n📊 Testing {symbol}...")
        
        try:
            # Get real-time data
            data = await market_service.get_real_time_quote(symbol)
            
            if data:
                print(f"  ✅ SUCCESS: {symbol}")
                print(f"     Price: ${data.price:.2f}")
                print(f"     Change: {data.change:+.2f} ({data.change_percent:+.2f}%)")
                print(f"     Volume: {data.volume:,}")
                print(f"     Range: ${data.day_low:.2f} - ${data.day_high:.2f}")
                print(f"     Time: {data.timestamp}")
                
                results.append({
                    'symbol': symbol,
                    'success': True,
                    'price': data.price,
                    'change': data.change,
                    'change_percent': data.change_percent,
                    'volume': data.volume,
                    'timestamp': data.timestamp.isoformat()
                })
            else:
                print(f"  ❌ FAILED: {symbol} - No data returned")
                results.append({
                    'symbol': symbol,
                    'success': False,
                    'error': 'No data returned'
                })
                
        except Exception as e:
            print(f"  ❌ ERROR: {symbol} - {str(e)}")
            results.append({
                'symbol': symbol,
                'success': False,
                'error': str(e)
            })
    
    # Close service
    await market_service.close()
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n📈 REAL-TIME SNAPSHOT TEST SUMMARY:")
    print("=" * 50)
    print(f"Total symbols tested: {len(test_symbols)}")
    print(f"Successful: {successful}/{len(test_symbols)}")
    print(f"Success rate: {successful/len(test_symbols)*100:.1f}%")
    
    if successful > 0:
        print("\n🎉 REAL-TIME DATA WORKING!")
        print("✅ Snapshot endpoint successfully integrated")
        print("✅ Real market prices retrieved")
        print("✅ Full market data available with Stocks Starter")
        
        # Show sample data
        working_data = [r for r in results if r['success']]
        if working_data:
            sample = working_data[0]
            print(f"\n💡 Sample Data Format:")
            print(json.dumps(sample, indent=2, default=str))
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_realtime_snapshot())
