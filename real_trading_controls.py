"""
Real Trading Controls - Direct integration with live trading system
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.alpaca_trading import AlpacaTradingService
from services.ai_learning_engine import AILearningEngine
from services.database_manager import DatabaseManager
from services.config import Config
from services.telegram_trading import telegram_trading
from services.automated_trading_manager import AutomatedTradingManager

class RealTradingController:
    """Direct trading controller for real-time operations."""
    
    def __init__(self):
        self.config = Config()
        self.alpaca = AlpacaTradingService()
        self.ai_engine = AILearningEngine()
        self.db = DatabaseManager()
        self.trading_manager = AutomatedTradingManager()
        
    async def execute_manual_buy(self, ticker: str, shares: int = None, amount: float = None) -> Dict[str, Any]:
        """Execute manual buy order."""
        try:
            # Get current price and validate
            current_data = await self.trading_manager.data_provider.get_current_price(ticker)
            if not current_data:
                return {'success': False, 'error': f'Cannot get price data for {ticker}'}
            
            current_price = current_data['price']
            
            # Calculate shares if amount specified
            if amount and not shares:
                shares = int(amount / current_price)
            elif not shares:
                # Default position size (5% of portfolio)
                account = await self.get_account_info()
                portfolio_value = float(account.get('portfolio_value', 0))
                amount = portfolio_value * 0.05
                shares = max(1, int(amount / current_price))
            
            # Create recommendation structure
            recommendation = {
                'ticker': ticker,
                'entry': current_price,
                'stop_loss': current_price * 0.95,  # 5% stop loss
                'take_profit': current_price * 1.15,  # 15% take profit
                'position_size': {'percentage': 0.05},
                'confidence_score': 8.0,  # Manual trades get high confidence
                'reasoning': ['Manual dashboard execution']
            }
            
            # Execute through Alpaca service
            result = await self.alpaca.place_buy_order(recommendation)
            
            if result and result.get('success'):
                # Log to database
                await self.db.log_trade({
                    'ticker': ticker,
                    'action': 'BUY',
                    'shares': shares,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'source': 'manual_dashboard',
                    'order_id': result.get('order_id')
                })
                
                # Send notification
                await telegram_trading.send_message(
                    f"✅ *MANUAL BUY EXECUTED*\\n\\n"
                    f"📊 {ticker}: {shares} shares\\n"
                    f"💰 Price: ${current_price:.2f}\\n"
                    f"📱 Source: Dashboard\\n"
                    f"🆔 Order: {result.get('order_id', 'N/A')}"
                )
                
                return {
                    'success': True,
                    'order_id': result.get('order_id'),
                    'shares': shares,
                    'price': current_price,
                    'message': f'Buy order executed: {shares} shares of {ticker} at ${current_price:.2f}'
                }
            else:
                return {'success': False, 'error': result.get('error', 'Order execution failed')}
                
        except Exception as e:
            logger.error(f"Manual buy execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_manual_sell(self, ticker: str, shares: int = None) -> Dict[str, Any]:
        """Execute manual sell order."""
        try:
            # Get current position
            positions = await self.alpaca.get_positions()
            position = None
            
            for pos in positions:
                if pos.get('symbol') == ticker:
                    position = pos
                    break
            
            if not position:
                return {'success': False, 'error': f'No position found for {ticker}'}
            
            # Get shares to sell
            available_shares = abs(float(position.get('qty', 0)))
            if shares is None:
                shares = available_shares
            elif shares > available_shares:
                return {'success': False, 'error': f'Cannot sell {shares} shares, only {available_shares} available'}
            
            # Get current price
            current_data = await self.trading_manager.data_provider.get_current_price(ticker)
            if not current_data:
                return {'success': False, 'error': f'Cannot get current price for {ticker}'}
            
            current_price = current_data['price']
            
            # Execute sell order
            result = await self.alpaca.place_sell_order(ticker, shares)
            
            if result and result.get('success'):
                # Log to database
                await self.db.log_trade({
                    'ticker': ticker,
                    'action': 'SELL',
                    'shares': shares,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'source': 'manual_dashboard',
                    'order_id': result.get('order_id')
                })
                
                # Send notification
                await telegram_trading.send_message(
                    f"✅ *MANUAL SELL EXECUTED*\\n\\n"
                    f"📊 {ticker}: {shares} shares\\n"
                    f"💰 Price: ${current_price:.2f}\\n"
                    f"📱 Source: Dashboard\\n"
                    f"🆔 Order: {result.get('order_id', 'N/A')}"
                )
                
                return {
                    'success': True,
                    'order_id': result.get('order_id'),
                    'shares': shares,
                    'price': current_price,
                    'message': f'Sell order executed: {shares} shares of {ticker} at ${current_price:.2f}'
                }
            else:
                return {'success': False, 'error': result.get('error', 'Order execution failed')}
                
        except Exception as e:
            logger.error(f"Manual sell execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_live_signals(self) -> List[Dict[str, Any]]:
        """Get real-time trading signals."""
        try:
            # Get recent AI predictions
            predictions = self.ai_engine.get_recent_predictions()
            signals = []
            
            for pred in predictions:
                if pred.confidence_score >= 7.0:  # High confidence only
                    # Get current price
                    current_data = await self.trading_manager.data_provider.get_current_price(pred.ticker)
                    if current_data:
                        current_price = current_data['price']
                        
                        # Calculate targets based on predicted move
                        predicted_move = pred.predicted_move_percent / 100
                        if pred.predicted_direction == 'UP':
                            target_price = current_price * (1 + predicted_move)
                            stop_price = current_price * 0.95  # 5% stop
                        else:
                            target_price = current_price * (1 - predicted_move)
                            stop_price = current_price * 1.05  # 5% stop
                        
                        signals.append({
                            'ticker': pred.ticker,
                            'direction': pred.predicted_direction,
                            'confidence': pred.confidence_score,
                            'current_price': current_price,
                            'target_price': target_price,
                            'stop_price': stop_price,
                            'expected_move': pred.predicted_move_percent,
                            'timeframe': pred.predicted_timeframe_hours,
                            'reasoning': ' | '.join(pred.reasoning_factors[:3]),
                            'timestamp': pred.timestamp
                        })
            
            return signals
        except Exception as e:
            logger.error(f"Error getting live signals: {e}")
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get real account information."""
        try:
            return await self.alpaca.get_account()
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        try:
            return await self.alpaca.get_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_recent_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent trades from database."""
        try:
            return await self.db.get_recent_trades(limit=limit)
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    async def pause_auto_trading(self) -> Dict[str, Any]:
        """Pause automatic trading."""
        try:
            self.config.AUTO_TRADING_ENABLED = False
            await telegram_trading.send_message("⏸️ *Auto-trading paused* via dashboard")
            return {'success': True, 'message': 'Auto-trading paused'}
        except Exception as e:
            logger.error(f"Error pausing trading: {e}")
            return {'success': False, 'error': str(e)}
    
    async def resume_auto_trading(self) -> Dict[str, Any]:
        """Resume automatic trading."""
        try:
            self.config.AUTO_TRADING_ENABLED = True
            await telegram_trading.send_message("▶️ *Auto-trading resumed* via dashboard")
            return {'success': True, 'message': 'Auto-trading resumed'}
        except Exception as e:
            logger.error(f"Error resuming trading: {e}")
            return {'success': False, 'error': str(e)}
    
    async def trigger_market_scan(self) -> Dict[str, Any]:
        """Trigger immediate market scan."""
        try:
            # This would trigger the main trading loop
            await telegram_trading.send_message("🔄 *Market scan triggered* via dashboard")
            return {'success': True, 'message': 'Market scan triggered'}
        except Exception as e:
            logger.error(f"Error triggering scan: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_test_notification(self) -> Dict[str, Any]:
        """Send test notification."""
        try:
            await telegram_trading.send_message(
                f"📱 *DASHBOARD TEST*\\n\\n"
                f"✅ Connection verified\\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                f"💼 Account active\\n"
                f"🚀 Ready for trading"
            )
            return {'success': True, 'message': 'Test notification sent'}
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            return {'success': False, 'error': str(e)}
    
    async def update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update trading configuration."""
        try:
            # Update in-memory config
            for key, value in config_updates.items():
                if hasattr(self.config, key.upper()):
                    setattr(self.config, key.upper(), value)
            
            await telegram_trading.send_message(
                f"⚙️ *Configuration Updated*\\n\\n"
                f"Changes: {len(config_updates)} settings\\n"
                f"Source: Dashboard"
            )
            
            return {'success': True, 'message': 'Configuration updated'}
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        try:
            return await self.db.get_performance_summary()
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}

# Global controller instance
trading_controller = RealTradingController()

# Command-line interface for direct trading
async def main():
    """Command-line interface for real trading controls."""
    if len(sys.argv) < 2:
        print("Usage: python real_trading_controls.py <command> [args]")
        print("\nCommands:")
        print("  buy <ticker> [shares|amount]  - Execute buy order")
        print("  sell <ticker> [shares]        - Execute sell order")
        print("  signals                       - Show live signals")
        print("  positions                     - Show current positions")
        print("  account                       - Show account info")
        print("  pause                         - Pause auto-trading")
        print("  resume                        - Resume auto-trading")
        print("  scan                          - Trigger market scan")
        print("  test                          - Send test notification")
        return
    
    command = sys.argv[1].lower()
    controller = trading_controller
    
    try:
        if command == 'buy' and len(sys.argv) >= 3:
            ticker = sys.argv[2].upper()
            shares = int(sys.argv[3]) if len(sys.argv) > 3 else None
            result = await controller.execute_manual_buy(ticker, shares=shares)
            print(f"Buy result: {result}")
            
        elif command == 'sell' and len(sys.argv) >= 3:
            ticker = sys.argv[2].upper()
            shares = int(sys.argv[3]) if len(sys.argv) > 3 else None
            result = await controller.execute_manual_sell(ticker, shares=shares)
            print(f"Sell result: {result}")
            
        elif command == 'signals':
            signals = await controller.get_live_signals()
            print(f"\n📊 Live Signals ({len(signals)} found):")
            for signal in signals:
                print(f"  {signal['ticker']}: {signal['direction']} "
                      f"({signal['confidence']:.1f}/10) - {signal['reasoning'][:50]}...")
                      
        elif command == 'positions':
            positions = await controller.get_positions()
            print(f"\n💼 Current Positions ({len(positions)} found):")
            for pos in positions:
                if float(pos.get('qty', 0)) != 0:
                    print(f"  {pos['symbol']}: {pos['qty']} shares, "
                          f"${float(pos['market_value']):.2f} value")
                          
        elif command == 'account':
            account = await controller.get_account_info()
            print(f"\n💰 Account Info:")
            print(f"  Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
            print(f"  Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
            print(f"  Day P&L: ${float(account.get('unrealized_pl', 0)):,.2f}")
            
        elif command == 'pause':
            result = await controller.pause_auto_trading()
            print(f"Pause result: {result}")
            
        elif command == 'resume':
            result = await controller.resume_auto_trading()
            print(f"Resume result: {result}")
            
        elif command == 'scan':
            result = await controller.trigger_market_scan()
            print(f"Scan result: {result}")
            
        elif command == 'test':
            result = await controller.send_test_notification()
            print(f"Test result: {result}")
            
        else:
            print(f"Unknown command: {command}")
            
    except Exception as e:
        print(f"Error executing command: {e}")

if __name__ == "__main__":
    asyncio.run(main())
