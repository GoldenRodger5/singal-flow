"""
Alpaca Trading Service for order execution and management.
"""
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError

from services.config import Config


class AlpacaTradingService:
    """Service for executing trades through Alpaca API."""
    
    def __init__(self):
        """Initialize Alpaca trading service."""
        self.config = Config()
        self.api = tradeapi.REST(
            self.config.ALPACA_API_KEY,
            self.config.ALPACA_SECRET,
            self.config.ALPACA_BASE_URL,
            api_version='v2'
        )
        
    async def place_buy_order(self, recommendation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Place a buy order based on recommendation."""
        try:
            ticker = recommendation['ticker']
            entry_price = recommendation['entry']
            stop_loss = recommendation['stop_loss']
            take_profit = recommendation['take_profit']
            position_size = recommendation['position_size']['percentage']
            
            # Get account info to calculate shares
            account = self.api.get_account()
            buying_power = float(account.buying_power)
            position_value = buying_power * position_size
            shares = int(position_value / entry_price)
            
            if shares <= 0:
                logger.error(f"Invalid share calculation: {shares} shares for {ticker}")
                return None
            
            # Place market buy order
            order = self.api.submit_order(
                symbol=ticker,
                qty=shares,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            logger.info(f"Buy order placed: {shares} shares of {ticker} at market price")
            
            # Place bracket orders for stop loss and take profit
            await self._place_exit_orders(ticker, shares, stop_loss, take_profit)
            
            return {
                'order_id': order.id,
                'ticker': ticker,
                'shares': shares,
                'side': 'buy',
                'type': 'market',
                'status': order.status,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
        except APIError as e:
            logger.error(f"Alpaca API error placing buy order for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing buy order for {ticker}: {e}")
            return None
    
    async def place_sell_order(self, ticker: str, shares: int, order_type: str = 'market') -> Optional[Dict[str, Any]]:
        """Place a sell order."""
        try:
            order = self.api.submit_order(
                symbol=ticker,
                qty=shares,
                side='sell',
                type=order_type,
                time_in_force='day'
            )
            
            logger.info(f"Sell order placed: {shares} shares of {ticker}")
            
            return {
                'order_id': order.id,
                'ticker': ticker,
                'shares': shares,
                'side': 'sell',
                'type': order_type,
                'status': order.status
            }
            
        except APIError as e:
            logger.error(f"Alpaca API error placing sell order for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing sell order for {ticker}: {e}")
            return None
    
    async def _place_exit_orders(self, ticker: str, shares: int, stop_loss: float, take_profit: float):
        """Place stop loss and take profit orders."""
        try:
            # Place stop loss order
            stop_order = self.api.submit_order(
                symbol=ticker,
                qty=shares,
                side='sell',
                type='stop',
                stop_price=stop_loss,
                time_in_force='day'
            )
            
            # Place take profit order
            limit_order = self.api.submit_order(
                symbol=ticker,
                qty=shares,
                side='sell',
                type='limit',
                limit_price=take_profit,
                time_in_force='day'
            )
            
            logger.info(f"Exit orders placed for {ticker}: Stop ${stop_loss}, Target ${take_profit}")
            
        except Exception as e:
            logger.error(f"Error placing exit orders for {ticker}: {e}")
    
    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get current position for a ticker."""
        try:
            position = self.api.get_position(ticker)
            return {
                'ticker': ticker,
                'shares': int(position.qty),
                'market_value': float(position.market_value),
                'cost_basis': float(position.cost_basis),
                'unrealized_pl': float(position.unrealized_pl),
                'side': position.side
            }
        except Exception:
            return None
    
    def get_open_orders(self, ticker: str = None) -> list:
        """Get open orders, optionally filtered by ticker."""
        try:
            orders = self.api.list_orders(status='open')
            if ticker:
                orders = [order for order in orders if order.symbol == ticker]
            return orders
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        try:
            account = self.api.get_account()
            return {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'day_trade_count': int(account.daytrade_count),
                'pattern_day_trader': account.pattern_day_trader
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
