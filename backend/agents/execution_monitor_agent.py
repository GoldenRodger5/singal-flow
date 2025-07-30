"""
Execution Monitor Agent - Monitors trades and handles exits.
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from services.data_provider import PolygonDataProvider
from services.config import Config
from agents.reasoning_agent import ReasoningAgent


class ExecutionMonitorAgent:
    """Agent responsible for monitoring active trades and managing exits."""
    
    def __init__(self):
        """Initialize the execution monitor agent."""
        self.config = Config()
        self.reasoning_agent = ReasoningAgent()
        self.active_trades = []
        self.monitoring = False
        
    async def start_monitoring(self) -> None:
        """Start monitoring active trades."""
        if self.monitoring:
            logger.warning("Trade monitoring already active")
            return
        
        self.monitoring = True
        logger.info("Starting trade execution monitoring")
        
        # Load any existing active trades
        await self._load_active_trades()
        
        # Start monitoring loop
        while self.monitoring:
            try:
                await self._monitor_active_trades()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop_monitoring(self) -> None:
        """Stop trade monitoring."""
        self.monitoring = False
        logger.info("Trade execution monitoring stopped")
    
    async def add_trade(self, recommendation: Dict[str, Any]) -> str:
        """Add a new trade to monitoring."""
        try:
            trade_id = self._generate_trade_id(recommendation['ticker'])
            
            trade = {
                'id': trade_id,
                'ticker': recommendation['ticker'],
                'entry_price': recommendation['entry'],
                'stop_loss': recommendation['stop_loss'],
                'take_profit': recommendation['take_profit'],
                'position_size': recommendation.get('position_size', {}),
                'entry_time': datetime.now().isoformat(),
                'status': 'monitoring',
                'max_hold_time': self._calculate_max_hold_time(),
                'trailing_stop': recommendation.get('exit_strategy', {}).get('trailing_stop', False),
                'current_stop': recommendation['stop_loss'],
                'highest_price': recommendation['entry'],
                'setup_type': recommendation.get('setup_type', 'Unknown'),
                'confidence': recommendation.get('confidence', 0)
            }
            
            self.active_trades.append(trade)
            await self._save_active_trades()
            
            logger.info(f"Added trade {trade_id} for {recommendation['ticker']} to monitoring")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error adding trade to monitoring: {e}")
            return ""
    
    async def remove_trade(self, trade_id: str, exit_reason: str = 'manual') -> Optional[Dict[str, Any]]:
        """Remove a trade from monitoring."""
        try:
            trade = None
            for i, t in enumerate(self.active_trades):
                if t['id'] == trade_id:
                    trade = self.active_trades.pop(i)
                    break
            
            if trade:
                trade['exit_time'] = datetime.now().isoformat()
                trade['exit_reason'] = exit_reason
                trade['status'] = 'closed'
                
                await self._save_active_trades()
                await self._log_completed_trade(trade)
                
                logger.info(f"Removed trade {trade_id} from monitoring ({exit_reason})")
                return trade
            else:
                logger.warning(f"Trade {trade_id} not found in active trades")
                return None
                
        except Exception as e:
            logger.error(f"Error removing trade from monitoring: {e}")
            return None
    
    async def _monitor_active_trades(self) -> None:
        """Monitor all active trades for exit conditions."""
        if not self.active_trades:
            return
        
        logger.debug(f"Monitoring {len(self.active_trades)} active trades")
        
        async with PolygonDataProvider() as data_provider:
            for trade in self.active_trades.copy():  # Copy to avoid modification during iteration
                try:
                    await self._monitor_single_trade(trade, data_provider)
                except Exception as e:
                    logger.error(f"Error monitoring trade {trade['id']}: {e}")
    
    async def _monitor_single_trade(self, trade: Dict[str, Any], data_provider: PolygonDataProvider) -> None:
        """Monitor a single trade for exit conditions."""
        ticker = trade['ticker']
        
        # Get current market data
        snapshot = await data_provider.get_market_snapshot(ticker)
        
        if not snapshot or 'ticker' not in snapshot:
            logger.warning(f"No market data for {ticker}")
            return
        
        ticker_data = snapshot['ticker']
        last_quote = ticker_data.get('lastQuote', {})
        current_price = last_quote.get('P', 0)  # Current price
        
        if current_price <= 0:
            logger.warning(f"Invalid price for {ticker}: {current_price}")
            return
        
        # Update trade tracking
        trade['current_price'] = current_price
        trade['last_check'] = datetime.now().isoformat()
        
        # Update highest price for trailing stop
        if current_price > trade['highest_price']:
            trade['highest_price'] = current_price
            if trade['trailing_stop']:
                await self._update_trailing_stop(trade)
        
        # Check exit conditions
        exit_signal = await self._check_exit_conditions(trade, current_price)
        
        if exit_signal:
            await self._execute_exit(trade, exit_signal)
    
    async def _check_exit_conditions(self, trade: Dict[str, Any], current_price: float) -> Optional[Dict[str, Any]]:
        """Check if any exit conditions are met."""
        
        # 1. Take Profit Hit
        if current_price >= trade['take_profit']:
            return {
                'type': 'take_profit',
                'reason': 'Take profit target reached',
                'price': current_price
            }
        
        # 2. Stop Loss Hit (including trailing stop)
        current_stop = trade.get('current_stop', trade['stop_loss'])
        if current_price <= current_stop:
            return {
                'type': 'stop_loss',
                'reason': 'Stop loss triggered',
                'price': current_price
            }
        
        # 3. Time-based Exit
        max_hold_time = datetime.fromisoformat(trade['max_hold_time'])
        if datetime.now() >= max_hold_time:
            return {
                'type': 'time_exit',
                'reason': 'Maximum hold time reached',
                'price': current_price
            }
        
        # 4. Risk Management - Large Unrealized Loss
        entry_price = trade['entry_price']
        unrealized_loss = (current_price - entry_price) / entry_price
        if unrealized_loss < -0.08:  # 8% loss (emergency exit)
            return {
                'type': 'emergency_exit',
                'reason': 'Emergency risk management exit',
                'price': current_price
            }
        
        # 5. Technical Exit Signals (could be enhanced with more sophisticated logic)
        # For now, we'll rely on the predefined levels
        
        return None
    
    async def _update_trailing_stop(self, trade: Dict[str, Any]) -> None:
        """Update trailing stop loss based on highest price."""
        try:
            entry_price = trade['entry_price']
            highest_price = trade['highest_price']
            original_stop = trade['stop_loss']
            
            # Calculate initial risk
            initial_risk = entry_price - original_stop
            
            # Set trailing stop at breakeven + small buffer once we're up 1.5x initial risk
            profit_threshold = entry_price + (initial_risk * 1.5)
            
            if highest_price >= profit_threshold:
                # Move stop to breakeven + small buffer
                new_stop = entry_price + (initial_risk * 0.2)
                
                # Only update if new stop is higher than current stop
                current_stop = trade.get('current_stop', original_stop)
                if new_stop > current_stop:
                    trade['current_stop'] = new_stop
                    logger.info(f"Updated trailing stop for {trade['ticker']} to ${new_stop:.2f}")
                    
        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
    
    async def _execute_exit(self, trade: Dict[str, Any], exit_signal: Dict[str, Any]) -> None:
        """Execute trade exit and send notifications."""
        try:
            from services.config import Config
            from services.interactive_trading import InteractiveTradingService
            from services.alpaca_trading import AlpacaTradingService
            
            config = Config()
            ticker = trade['ticker']
            exit_price = exit_signal['price']
            exit_reason = exit_signal['type']
            exit_type = exit_signal['reason']
            
            # Calculate P&L
            entry_price = trade['entry_price']
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            
            # Get shares from trade or calculate
            shares = trade.get('shares', 100)  # Default fallback
            pnl_dollar = shares * (exit_price - entry_price)
            
            # Check trading mode for exit execution
            if config.AUTO_TRADING_ENABLED:
                # Auto-trading: Execute immediately
                logger.info(f"Auto-trading: executing sell order for {ticker}")
                
                alpaca = AlpacaTradingService()
                order_result = await alpaca.place_sell_order(ticker, shares)
                
                if order_result:
                    # Send notification about executed exit
                    from services.twilio_whatsapp import WhatsAppNotifier
                    notifier = WhatsAppNotifier()
                    
                    await notifier.send_message(
                        f"🤖 AUTO-EXIT EXECUTED\n"
                        f"📊 {ticker}: {shares} shares SOLD\n"
                        f"💰 Exit: ${exit_price:.2f}\n"
                        f"📈 P&L: ${pnl_dollar:.2f} ({pnl_percent:+.1f}%)\n"
                        f"🎯 Reason: {exit_type}"
                    )
                    
                    # Remove from monitoring
                    await self.remove_trade(trade['id'], exit_reason)
                    logger.info(f"Auto-exit executed for {ticker}")
                else:
                    logger.error(f"Failed to execute auto-exit for {ticker}")
            
            elif config.INTERACTIVE_TRADING_ENABLED:
                # Interactive trading: Request confirmation
                logger.info(f"Interactive trading: requesting sell confirmation for {ticker}")
                
                interactive = InteractiveTradingService()
                confirmed = await interactive.request_sell_confirmation(
                    ticker, shares, f"{exit_type} - ${exit_price:.2f}"
                )
                
                if confirmed:
                    # Remove from monitoring after successful interactive exit
                    await self.remove_trade(trade['id'], exit_reason)
                    logger.info(f"Interactive exit confirmed and executed for {ticker}")
                else:
                    logger.info(f"Interactive exit declined for {ticker} - continuing to monitor")
            
            else:
                # Notification-only mode: Just alert user
                from services.twilio_whatsapp import WhatsAppNotifier
                notifier = WhatsAppNotifier()
                
                await notifier.send_message(
                    f"🚨 EXIT SIGNAL - {ticker}\n"
                    f"💰 Current: ${exit_price:.2f}\n"
                    f"📈 P&L: ${pnl_dollar:.2f} ({pnl_percent:+.1f}%)\n"
                    f"🎯 Reason: {exit_type}\n"
                    f"⚡ Manual action required"
                )
                
                # Remove from monitoring (user needs to manually exit)
                await self.remove_trade(trade['id'], exit_reason)
                logger.info(f"Exit signal sent for {ticker}")
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
    
    def _generate_trade_id(self, ticker: str) -> str:
        """Generate unique trade ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{ticker}_{timestamp}"
    
    def _calculate_max_hold_time(self) -> str:
        """Calculate maximum hold time for a trade."""
        # Default to 2 hours from now
        max_hold = datetime.now() + timedelta(hours=2)
        return max_hold.isoformat()
    
    async def _load_active_trades(self) -> None:
        """Load active trades from storage."""
        try:
            with open('data/active_trades.json', 'r') as f:
                data = json.load(f)
                self.active_trades = data.get('trades', [])
                logger.info(f"Loaded {len(self.active_trades)} active trades")
        except FileNotFoundError:
            logger.info("No active trades file found, starting fresh")
            self.active_trades = []
        except Exception as e:
            logger.error(f"Error loading active trades: {e}")
            self.active_trades = []
    
    async def _save_active_trades(self) -> None:
        """Save active trades to storage."""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'trades': self.active_trades
            }
            with open('data/active_trades.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving active trades: {e}")
    
    async def _log_completed_trade(self, trade: Dict[str, Any]) -> None:
        """Log completed trade to trade log."""
        try:
            # Load existing trade log
            try:
                with open('data/trade_log.json', 'r') as f:
                    trade_log = json.load(f)
            except FileNotFoundError:
                trade_log = []
            
            # Add completed trade
            trade_log.append(trade)
            
            # Save updated log
            with open('data/trade_log.json', 'w') as f:
                json.dump(trade_log, f, indent=2)
                
            logger.info(f"Logged completed trade: {trade['ticker']} ({trade.get('exit_reason', 'unknown')})")
            
        except Exception as e:
            logger.error(f"Error logging completed trade: {e}")
    
    def get_active_trades_summary(self) -> Dict[str, Any]:
        """Get summary of active trades."""
        if not self.active_trades:
            return {'count': 0, 'tickers': []}
        
        return {
            'count': len(self.active_trades),
            'tickers': [trade['ticker'] for trade in self.active_trades],
            'total_at_risk': sum(
                trade.get('position_size', {}).get('max_risk_per_trade', 0) 
                for trade in self.active_trades
            )
        }
    
    async def manual_exit_trade(self, ticker: str, reason: str = "manual") -> bool:
        """Manually exit a trade."""
        try:
            for trade in self.active_trades:
                if trade['ticker'] == ticker:
                    # Get current price
                    async with PolygonDataProvider() as data_provider:
                        snapshot = await data_provider.get_market_snapshot(ticker)
                        
                        if snapshot and 'ticker' in snapshot:
                            current_price = snapshot['ticker'].get('lastQuote', {}).get('P', 0)
                            
                            if current_price > 0:
                                exit_signal = {
                                    'type': 'manual_exit',
                                    'reason': reason,
                                    'price': current_price
                                }
                                await self._execute_exit(trade, exit_signal)
                                return True
            
            logger.warning(f"No active trade found for {ticker}")
            return False
            
        except Exception as e:
            logger.error(f"Error manually exiting trade: {e}")
            return False
