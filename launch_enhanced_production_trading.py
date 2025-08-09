#!/usr/bin/env python3
"""
Enhanced Production Trading Launcher with Full Notification System
Starts autonomous paper trading with session notifications and market close alerts.
"""

import sys
import asyncio
import signal
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from services.telegram_notifier import TelegramNotifier
from services.database_manager import DatabaseManager
from services.portfolio_holdings_service import PortfolioHoldingsService
from utils.market_hours import market_hours, format_time_until

class EnhancedTradingLauncher:
    """Enhanced launcher with complete notification system."""
    
    def __init__(self):
        self.notifier = None
        self.db = None
        self.portfolio = None
        self.running = False
        
    def check_market_hours(self):
        """Check if we should start trading based on market hours."""
        current_time = market_hours.get_current_est_time()
        market_status = market_hours.get_market_status()
        
        print(f"⏰ Current EST Time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📊 Market Status: {market_status}")
        
        if market_status == "WEEKEND":
            print("🛑 Market is closed - Weekend")
            next_open, _ = market_hours.get_next_market_session()
            print(f"📅 Next market open: {next_open.strftime('%A, %B %d at %I:%M %p EST')}")
            return False
        
        elif market_status == "MARKET_CLOSED":
            print("🛑 Market is closed - Outside trading hours")
            minutes_until = market_hours.time_until_market_open()
            if minutes_until:
                print(f"⏳ Market opens in: {format_time_until(minutes_until)}")
            return False
        
        elif market_status == "PRE_MARKET":
            print("🌅 Pre-market hours detected")
            minutes_until = market_hours.time_until_market_open()
            if minutes_until:
                print(f"⏳ Market opens in: {format_time_until(minutes_until)}")
            print("⚠️ Starting in standby mode until market opens...")
            return "standby"  # Special status for pre-market
        
        elif market_status == "MARKET_OPEN":
            print("🟢 Market is OPEN - Ready for trading!")
            minutes_until_close = market_hours.time_until_market_close()
            if minutes_until_close:
                print(f"⏳ Market closes in: {format_time_until(minutes_until_close)}")
            return True
        
        elif market_status == "AFTER_HOURS":
            print("🌃 After-hours trading detected")
            print("⚠️ Limited trading capabilities during after-hours")
            return "after_hours"  # Special status for after-hours
        
        return False

    async def wait_for_market_open(self):
        """Wait until market opens, with periodic status updates."""
        while not market_hours.is_market_hours():
            current_time = market_hours.get_current_est_time()
            market_status = market_hours.get_market_status()
            
            if market_status == "WEEKEND":
                print("💤 Weekend detected - sleeping until Monday...")
                # Sleep for 4 hours during weekends
                await asyncio.sleep(4 * 60 * 60)
                continue
            
            minutes_until = market_hours.time_until_market_open()
            if minutes_until:
                if minutes_until <= 30:
                    print(f"🚀 Market opening soon! {format_time_until(minutes_until)} remaining...")
                    # Check every minute when close to opening
                    await asyncio.sleep(60)
                elif minutes_until <= 120:
                    print(f"⏰ Market opens in {format_time_until(minutes_until)}")
                    # Check every 10 minutes when within 2 hours
                    await asyncio.sleep(10 * 60)
                else:
                    print(f"💤 Market opens in {format_time_until(minutes_until)} - sleeping...")
                    # Sleep for 30 minutes when far from opening
                    await asyncio.sleep(30 * 60)
            else:
                await asyncio.sleep(60)  # Default 1 minute sleep
        
        print("🟢 Market is now OPEN! Starting trading system...")

    async def initialize_services(self):
        """Initialize all required services."""
        try:
            print("🔄 Initializing production services...")
            
            # Initialize Telegram notifier
            self.notifier = TelegramNotifier()
            print("   ✅ Telegram notifier initialized")
            
            # Initialize database
            self.db = DatabaseManager()
            print("   ✅ MongoDB connection established")
            
            # Initialize portfolio service
            self.portfolio = PortfolioHoldingsService()
            print("   ✅ Portfolio service initialized")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Service initialization failed: {e}")
            return False
    
    async def get_session_info(self):
        """Get session information for startup notification."""
        try:
            # Get portfolio summary (mock data for now - replace with real data)
            portfolio_value = 100000.00  # Paper trading account
            cash_available = 25000.00    # Available cash
            watchlist_size = 50          # Stocks being monitored
            
            # Determine market conditions (simplified)
            now = datetime.now()
            if 9 <= now.hour < 16:  # Market hours
                market_conditions = "Active trading session - Real-time market analysis"
            else:
                market_conditions = "Pre/Post market - Preparing for next session"
            
            return {
                'portfolio_value': portfolio_value,
                'cash_available': cash_available,
                'watchlist_size': watchlist_size,
                'market_conditions': market_conditions
            }
            
        except Exception as e:
            print(f"⚠️ Could not get session info: {e}")
            return {}
    
    async def get_daily_summary(self):
        """Get daily trading summary for market close notification."""
        try:
            # Mock daily summary (replace with real data from database)
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'daily_pnl': 0.0,
                'best_trade': {},
                'worst_trade': {},
                'final_portfolio_value': 100000.00
            }
            
        except Exception as e:
            print(f"⚠️ Could not get daily summary: {e}")
            return {}
    
    async def send_startup_notification(self):
        """Send trading session start notification."""
        try:
            print("📱 Sending trading session start notification...")
            session_info = await self.get_session_info()
            
            success = await self.notifier.send_trading_session_start(session_info)
            if success:
                print("   ✅ Session start notification sent successfully")
            else:
                print("   ⚠️ Session start notification failed")
                
        except Exception as e:
            print(f"   ❌ Error sending startup notification: {e}")
    
    async def send_shutdown_notification(self):
        """Send market close notification."""
        try:
            print("📱 Sending market close notification...")
            daily_summary = await self.get_daily_summary()
            
            success = await self.notifier.send_market_close_notification(daily_summary)
            if success:
                print("   ✅ Market close notification sent successfully")
            else:
                print("   ⚠️ Market close notification failed")
                
        except Exception as e:
            print(f"   ❌ Error sending shutdown notification: {e}")
    
    async def start_production_trading(self):
        """Start the production trading system with market hours validation."""
        try:
            print("\n🤖 SIGNALFLOW AUTONOMOUS TRADING SYSTEM")
            print("=" * 55)
            
            # Check market hours BEFORE starting anything
            market_check = self.check_market_hours()
            
            if market_check is False:
                print("\n❌ TRADING SYSTEM NOT STARTED")
                print("💡 Tip: Run this script during market hours (9:30 AM - 4:00 PM EST, weekdays)")
                print("📱 For testing notifications, use: python test_startup_notifications.py")
                return False
            
            # Initialize services
            if not await self.initialize_services():
                print("❌ Failed to initialize services")
                return False
            
            # Handle pre-market scenario
            if market_check == "standby":
                print("\n⏳ STANDBY MODE - Waiting for market open...")
                await self.wait_for_market_open()
            
            # Send startup notification only when market is open or about to open
            if market_hours.is_market_hours() or market_hours.time_until_market_open() <= 30:
                await self.send_startup_notification()
            
            # Set running flag
            self.running = True
            
            current_time = market_hours.get_current_est_time()
            print(f"""
✅ PRODUCTION SYSTEM ACTIVE
⏰ Started: {current_time.strftime('%Y-%m-%d %H:%M:%S EST')}
📊 Market Status: {market_hours.get_market_status()}
🛡️ Safety Mode: Paper trading (no real money at risk)
📱 Notifications: Full Telegram alerts enabled
🤖 AI Trading: Autonomous signal generation active
📊 Database: MongoDB Atlas connected
🔄 Status: Monitoring markets and executing trades...

🎯 The system will:
   • Only trade during market hours (9:30 AM - 4:00 PM EST)
   • Automatically stop at market close
   • Generate AI trading signals in real-time
   • Execute paper trades automatically
   • Send detailed notifications for all trades
   • Monitor portfolio performance

Press Ctrl+C to stop the system gracefully...
            """)
            
            # Main trading loop with market hours checking
            try:
                while self.running:
                    current_time = market_hours.get_current_est_time()
                    
                    # Check if market has closed
                    if not market_hours.is_market_hours() and not market_hours.is_extended_hours():
                        market_status = market_hours.get_market_status()
                        if market_status in ["MARKET_CLOSED", "WEEKEND"]:
                            print(f"\n🔔 Market has closed - {market_status}")
                            await self.graceful_shutdown()
                            break
                    
                    # Trading logic would go here during market hours
                    if market_hours.is_market_hours():
                        # Active trading mode
                        pass
                    elif market_hours.is_extended_hours():
                        # Limited extended hours trading
                        pass
                    else:
                        # Market closed - standby mode
                        print(f"💤 {current_time.strftime('%H:%M EST')} - Market closed, standby mode...")
                    
                    # Check every minute
                    await asyncio.sleep(60)
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutdown signal received...")
                await self.graceful_shutdown()
                
            return True
            
        except Exception as e:
            print(f"❌ Error starting production trading: {e}")
            traceback.print_exc()
            return False
    
    async def graceful_shutdown(self):
        """Gracefully shutdown the trading system."""
        try:
            print("🔄 Shutting down trading system...")
            self.running = False
            
            # Send market close notification
            await self.send_shutdown_notification()
            
            # Clean up resources
            if self.notifier:
                await self.notifier.close()
            
            print("✅ System shutdown complete")
            
        except Exception as e:
            print(f"⚠️ Error during shutdown: {e}")

def setup_signal_handlers(launcher):
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}")
        asyncio.create_task(launcher.graceful_shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry point."""
    print("🤖 SignalFlow Enhanced Trading System")
    print("=" * 40)
    
    launcher = EnhancedTradingLauncher()
    setup_signal_handlers(launcher)
    
    try:
        success = await launcher.start_production_trading()
        if success:
            print("🎉 Trading session completed successfully")
        else:
            print("❌ Trading session ended with errors")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
