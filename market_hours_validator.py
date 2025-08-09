#!/usr/bin/env python3
"""
Market Hours Startup Validator
Shows exactly what happens when you try to start the trading system
"""

import sys
import asyncio
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from backend.utils.market_hours import market_hours, format_time_until

def main():
    """Show current market status and startup validation."""
    print("🕐 SIGNALFLOW TRADING SYSTEM - MARKET HOURS VALIDATOR")
    print("=" * 65)
    
    current_time = market_hours.get_current_est_time()
    market_status = market_hours.get_market_status()
    
    print(f"📅 Current Date: {current_time.strftime('%A, %B %d, %Y')}")
    print(f"⏰ Current Time: {current_time.strftime('%I:%M:%S %p EST')}")
    print(f"📊 Market Status: {market_status}")
    print()
    
    # Show detailed status
    if market_status == "WEEKEND":
        print("🛑 STATUS: WEEKEND - Markets are closed")
        next_open, _ = market_hours.get_next_market_session()
        print(f"📅 Next trading day: {next_open.strftime('%A, %B %d')}")
        print(f"⏰ Market opens: {next_open.strftime('%I:%M %p EST')}")
        minutes_until = market_hours.time_until_market_open()
        if minutes_until:
            print(f"⏳ Time until open: {format_time_until(minutes_until)}")
        
        print("\n❌ RESULT: Trading system will NOT start")
        print("💡 TIP: Run during weekdays between 9:30 AM - 4:00 PM EST")
        
    elif market_status == "MARKET_CLOSED":
        print("🌙 STATUS: MARKET CLOSED - Outside trading hours")
        minutes_until = market_hours.time_until_market_open()
        if minutes_until:
            print(f"⏳ Market opens in: {format_time_until(minutes_until)}")
        
        print("\n❌ RESULT: Trading system will NOT start")
        print("💡 TIP: Run between 9:30 AM - 4:00 PM EST on weekdays")
        
    elif market_status == "PRE_MARKET":
        print("🌅 STATUS: PRE-MARKET HOURS")
        minutes_until = market_hours.time_until_market_open()
        if minutes_until:
            print(f"⏳ Market opens in: {format_time_until(minutes_until)}")
        
        print("\n⏳ RESULT: System will start in STANDBY mode")
        print("📋 ACTION: Will wait for market open, then send notifications")
        
    elif market_status == "MARKET_OPEN":
        print("🟢 STATUS: MARKET IS OPEN - Active trading session")
        minutes_until_close = market_hours.time_until_market_close()
        if minutes_until_close:
            print(f"⏳ Market closes in: {format_time_until(minutes_until_close)}")
        
        print("\n✅ RESULT: Trading system will start IMMEDIATELY")
        print("📋 ACTION: Will send startup notification and begin trading")
        
    elif market_status == "AFTER_HOURS":
        print("🌃 STATUS: AFTER-HOURS TRADING")
        print("⚠️ Limited trading capabilities available")
        
        print("\n⚠️ RESULT: System will start in LIMITED mode")
        print("📋 ACTION: Will monitor but limit trade execution")
    
    print("\n" + "=" * 65)
    print("🔧 SYSTEM BEHAVIOR:")
    print("   • ✅ Only starts during appropriate market hours")
    print("   • ✅ Prevents unnecessary 3 AM notifications") 
    print("   • ✅ Automatically waits for market open if needed")
    print("   • ✅ Respects weekends and holidays")
    print("   • ✅ Auto-shutdown at market close")
    print("\n🚀 To start trading system: python launch_enhanced_production_trading.py")
    
    return market_status

if __name__ == "__main__":
    status = main()
    print(f"\nCurrent market status: {status}")
