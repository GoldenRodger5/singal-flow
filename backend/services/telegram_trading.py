#!/usr/bin/env python3
"""
Production Telegram Integration Service
Connects FastAPI webhook system with main trading application
"""
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from services.config import Config
from services.alpaca_trading import AlpacaTradingService



class TelegramTradingService:
    """Production-ready Telegram trading service with real execution."""
    
    def __init__(self):
        """Initialize the service."""
        self.config = Config()
        self.alpaca = AlpacaTradingService()
        # Note: Interactive trading removed to avoid circular imports
        self.interactive_trading = None
        
        # Store pending trade recommendations for execution
        self.pending_trades: Dict[str, Dict[str, Any]] = {}
        self.executed_trades: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Production Telegram Trading Service initialized")
    
    async def store_trade_signal(self, recommendation: Dict[str, Any], explanation: str) -> str:
        """Store a trade recommendation and return a callback ID."""
        ticker = recommendation['ticker']
        action = recommendation.get('action', 'BUY')
        timestamp = datetime.now().isoformat()
        
        callback_id = f"{action}_{ticker}_{int(datetime.now().timestamp())}"
        
        self.pending_trades[callback_id] = {
            'recommendation': recommendation,
            'explanation': explanation,
            'timestamp': timestamp,
            'status': 'pending'
        }
        
        logger.info(f"Stored trade signal: {callback_id}")
        return callback_id
    
    async def execute_trade(self, callback_data: str) -> Dict[str, Any]:
        """Execute a trade based on callback data from Telegram button."""
        try:
            # Parse callback data (format: execute_TICKER_ACTION_TIMESTAMP)
            parts = callback_data.split('_')
            if len(parts) < 3:
                return {'success': False, 'error': 'Invalid callback data'}
            
            action = parts[0]  # execute
            ticker = parts[1]  # TSLA
            trade_action = parts[2] if len(parts) > 2 else 'BUY'  # BUY/SELL
            
            # Find the pending trade
            trade_key = None
            for key, trade in self.pending_trades.items():
                if ticker in key and trade_action in key and trade['status'] == 'pending':
                    trade_key = key
                    break
            
            if not trade_key:
                return {'success': False, 'error': f'No pending trade found for {ticker}'}
            
            trade_data = self.pending_trades[trade_key]
            recommendation = trade_data['recommendation']
            
            # Execute the trade through Alpaca
            if trade_action.upper() == 'BUY':
                order_result = await self.alpaca.place_buy_order(recommendation)
            elif trade_action.upper() == 'SELL':
                order_result = await self.alpaca.place_sell_order(recommendation)
            else:
                return {'success': False, 'error': f'Unknown action: {trade_action}'}
            
            if order_result and order_result.get('success'):
                # Mark as executed
                self.pending_trades[trade_key]['status'] = 'executed'
                self.pending_trades[trade_key]['execution_time'] = datetime.now().isoformat()
                self.pending_trades[trade_key]['order_result'] = order_result
                
                # Move to executed trades
                self.executed_trades[trade_key] = self.pending_trades[trade_key]
                
                logger.info(f"✅ Trade executed successfully: {ticker} {trade_action}")
                
                return {
                    'success': True,
                    'ticker': ticker,
                    'action': trade_action,
                    'shares': order_result.get('shares', 0),
                    'entry_price': recommendation['entry'],
                    'stop_loss': recommendation['stop_loss'],
                    'take_profit': recommendation['take_profit'],
                    'order_id': order_result.get('order_id'),
                    'timestamp': datetime.now().strftime('%H:%M:%S EST')
                }
            else:
                logger.error(f"❌ Trade execution failed: {order_result}")
                return {
                    'success': False, 
                    'error': order_result.get('error', 'Trade execution failed'),
                    'ticker': ticker
                }
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {'success': False, 'error': str(e)}
    
    async def skip_trade(self, callback_data: str) -> Dict[str, Any]:
        """Skip a trade based on callback data."""
        try:
            parts = callback_data.split('_')
            if len(parts) < 2:
                return {'success': False, 'error': 'Invalid callback data'}
            
            ticker = parts[1]  # TSLA
            
            # Find and mark the trade as skipped
            trade_key = None
            for key, trade in self.pending_trades.items():
                if ticker in key and trade['status'] == 'pending':
                    trade_key = key
                    break
            
            if trade_key:
                self.pending_trades[trade_key]['status'] = 'skipped'
                self.pending_trades[trade_key]['skip_time'] = datetime.now().isoformat()
                logger.info(f"⏭️ Trade skipped: {ticker}")
            
            return {
                'success': True,
                'ticker': ticker,
                'action': 'skipped',
                'timestamp': datetime.now().strftime('%H:%M:%S EST')
            }
            
        except Exception as e:
            logger.error(f"Error skipping trade: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get real portfolio status from Alpaca."""
        try:
            # Get account info
            account = await self.alpaca.get_account()
            positions = await self.alpaca.get_positions()
            
            # Calculate P&L
            total_value = float(account.get('portfolio_value', 0))
            day_change = float(account.get('unrealized_pl', 0))
            day_change_pct = (day_change / total_value) * 100 if total_value > 0 else 0
            
            # Get cash available
            buying_power = float(account.get('buying_power', 0))
            cash = float(account.get('cash', 0))
            
            # Process positions
            open_positions = []
            for position in positions:
                qty = float(position.get('qty', 0))
                if qty != 0:  # Only open positions
                    market_value = float(position.get('market_value', 0))
                    unrealized_pl = float(position.get('unrealized_pl', 0))
                    unrealized_plpc = float(position.get('unrealized_plpc', 0)) * 100
                    
                    open_positions.append({
                        'symbol': position.get('symbol'),
                        'qty': qty,
                        'market_value': market_value,
                        'unrealized_pl': unrealized_pl,
                        'unrealized_plpc': unrealized_plpc
                    })
            
            # Calculate today's stats
            executed_today = len([t for t in self.executed_trades.values() 
                                if t.get('execution_time', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
            
            pending_count = len([t for t in self.pending_trades.values() 
                               if t['status'] == 'pending'])
            
            return {
                'success': True,
                'account_value': total_value,
                'day_pl': day_change,
                'day_pl_pct': day_change_pct,
                'cash': cash,
                'buying_power': buying_power,
                'open_positions': open_positions,
                'trades_today': executed_today,
                'pending_signals': pending_count,
                'timestamp': datetime.now().strftime('%H:%M:%S EST')
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def pause_trading(self) -> Dict[str, Any]:
        """Pause the trading system."""
        try:
            # Set configuration to pause trading
            self.config.AUTO_TRADING_ENABLED = False
            logger.info("🛑 Trading system paused")
            
            return {
                'success': True,
                'status': 'paused',
                'timestamp': datetime.now().strftime('%H:%M:%S EST'),
                'message': 'All trading activity suspended. Existing positions remain monitored.'
            }
            
        except Exception as e:
            logger.error(f"Error pausing trading: {e}")
            return {'success': False, 'error': str(e)}
    
    async def resume_trading(self) -> Dict[str, Any]:
        """Resume the trading system."""
        try:
            # Set configuration to resume trading
            self.config.AUTO_TRADING_ENABLED = True
            logger.info("▶️ Trading system resumed")
            
            return {
                'success': True,
                'status': 'active',
                'timestamp': datetime.now().strftime('%H:%M:%S EST'),
                'message': 'Trading system reactivated. Market scanning resumed.'
            }
            
        except Exception as e:
            logger.error(f"Error resuming trading: {e}")
            return {'success': False, 'error': str(e)}
    
    async def force_market_scan(self) -> Dict[str, Any]:
        """Trigger an immediate market scan."""
        try:
            # Import here to avoid circular imports
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            from main import SignalFlowOrchestrator
            
            orchestrator = SignalFlowOrchestrator()
            
            # Run market scan in background
            asyncio.create_task(orchestrator.run_market_scan())
            
            logger.info("🔍 Market scan initiated")
            
            return {
                'success': True,
                'status': 'scanning',
                'timestamp': datetime.now().strftime('%H:%M:%S EST'),
                'message': 'Market scan initiated. New signals will appear automatically.'
            }
            
        except Exception as e:
            logger.error(f"Error initiating market scan: {e}")
            return {'success': False, 'error': str(e)}


# Global instance for webhook handlers - lazy initialization
_telegram_trading = None

def get_telegram_trading():
    """Get Telegram trading service with lazy initialization"""
    global _telegram_trading
    if _telegram_trading is None:
        _telegram_trading = TelegramTradingService()
    return _telegram_trading

# Create module-level instance that can be imported
telegram_trading = None

def _init_telegram_trading():
    global telegram_trading
    if telegram_trading is None:
        telegram_trading = TelegramTradingService()
    return telegram_trading

# Initialize only when accessed
class LazyTelegramTrading:
    def __getattr__(self, name):
        service = _init_telegram_trading()
        return getattr(service, name)

telegram_trading = LazyTelegramTrading()
