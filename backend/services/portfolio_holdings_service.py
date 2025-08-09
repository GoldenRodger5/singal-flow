"""
Portfolio Holdings Service - Real-time position tracking for API
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import os

logger = logging.getLogger(__name__)

class PortfolioHoldingsService:
    """Service for getting portfolio holdings data for frontend API."""
    
    def __init__(self):
        """Initialize portfolio holdings service."""
        pass
    
    def get_holdings_dashboard_data(self) -> Dict[str, Any]:
        """Get complete holdings data for dashboard."""
        try:
            # Get holdings from Alpaca API
            holdings_data = self.get_real_holdings_data()
            
            if holdings_data:
                return {
                    'success': True,
                    'holdings': holdings_data,
                    'summary': self.calculate_portfolio_summary(holdings_data),
                    'recent_trades': self.get_recent_trades(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': True,
                    'holdings': [],
                    'summary': self.get_empty_portfolio_summary(),
                    'recent_trades': [],
                    'message': "No current positions. Ready for new trades!",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting holdings dashboard data: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_real_holdings_data(self) -> List[Dict[str, Any]]:
        """Get real holdings data from Alpaca API."""
        try:
            import sys
            import os
            
            # Import from same directory
            current_dir = os.path.dirname(__file__)
            sys.path.insert(0, current_dir)
            
            from alpaca_trading import AlpacaTradingService
            
            logger.info("📊 Getting REAL holdings from Alpaca API")
            
            alpaca_service = AlpacaTradingService()
            positions = alpaca_service.api.list_positions()
            
            if not positions:
                logger.info("No current positions found")
                return []
            
            # Format positions for API response
            formatted_holdings = []
            for position in positions:
                try:
                    # Get current market data
                    current_price = float(position.market_value) / abs(float(position.qty)) if float(position.qty) != 0 else 0
                    
                    holding = {
                        'symbol': position.symbol,
                        'quantity': float(position.qty),
                        'avg_cost': float(position.avg_entry_price),
                        'current_price': current_price,
                        'market_value': float(position.market_value),
                        'unrealized_pnl': float(position.unrealized_pl),
                        'unrealized_pnl_percent': float(position.unrealized_plpc) * 100,
                        'cost_basis': float(position.cost_basis),
                        'side': position.side,
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    formatted_holdings.append(holding)
                    
                except Exception as e:
                    logger.error(f"Error formatting position {position.symbol}: {e}")
                    continue
            
            logger.info(f"Found {len(formatted_holdings)} real positions")
            return formatted_holdings
            
        except Exception as e:
            logger.error(f"Error getting real holdings from Alpaca: {e}")
            return []

    def calculate_portfolio_summary(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate portfolio summary metrics."""
        if not holdings:
            return self.get_empty_portfolio_summary()
        
        try:
            total_value = sum(h.get('market_value', 0) for h in holdings)
            total_cost = sum(h.get('cost_basis', 0) for h in holdings)
            total_pnl = sum(h.get('unrealized_pnl', 0) for h in holdings)
            
            # Calculate total percentage change
            total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            
            # Count positions
            long_positions = len([h for h in holdings if h.get('quantity', 0) > 0])
            short_positions = len([h for h in holdings if h.get('quantity', 0) < 0])
            
            # Find best and worst performers
            best_performer = max(holdings, key=lambda x: x.get('unrealized_pnl_percent', 0)) if holdings else None
            worst_performer = min(holdings, key=lambda x: x.get('unrealized_pnl_percent', 0)) if holdings else None
            
            return {
                'total_positions': len(holdings),
                'long_positions': long_positions,
                'short_positions': short_positions,
                'total_market_value': round(total_value, 2),
                'total_cost_basis': round(total_cost, 2),
                'total_unrealized_pnl': round(total_pnl, 2),
                'total_unrealized_pnl_percent': round(total_pnl_percent, 2),
                'best_performer': {
                    'symbol': best_performer.get('symbol', 'N/A') if best_performer else 'N/A',
                    'pnl_percent': round(best_performer.get('unrealized_pnl_percent', 0), 2) if best_performer else 0
                },
                'worst_performer': {
                    'symbol': worst_performer.get('symbol', 'N/A') if worst_performer else 'N/A',
                    'pnl_percent': round(worst_performer.get('unrealized_pnl_percent', 0), 2) if worst_performer else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio summary: {e}")
            return self.get_empty_portfolio_summary()

    def get_empty_portfolio_summary(self) -> Dict[str, Any]:
        """Return empty portfolio summary."""
        return {
            'total_positions': 0,
            'long_positions': 0,
            'short_positions': 0,
            'total_market_value': 0.0,
            'total_cost_basis': 0.0,
            'total_unrealized_pnl': 0.0,
            'total_unrealized_pnl_percent': 0.0,
            'best_performer': {'symbol': 'N/A', 'pnl_percent': 0},
            'worst_performer': {'symbol': 'N/A', 'pnl_percent': 0}
        }

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades from database."""
        try:
            import sys
            import os
            
            # Import from same directory
            current_dir = os.path.dirname(__file__)
            sys.path.insert(0, current_dir)
            
            from database_manager import DatabaseManager
            
            db = DatabaseManager()
            # Use async method properly
            import asyncio
            recent_trades = asyncio.run(db.get_recent_trades(limit=limit))
            
            if recent_trades:
                # Format trades for API
                formatted_trades = []
                for trade in recent_trades:
                    formatted_trades.append({
                        'symbol': trade.get('ticker', 'Unknown'),
                        'action': trade.get('action', 'Unknown'),
                        'quantity': trade.get('shares', 0),
                        'price': trade.get('price', 0),
                        'timestamp': trade.get('timestamp', datetime.now()).isoformat() if hasattr(trade.get('timestamp'), 'isoformat') else str(trade.get('timestamp')),
                        'order_id': trade.get('order_id', 'N/A'),
                        'source': trade.get('source', 'system')
                    })
                return formatted_trades
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get specific position by symbol."""
        holdings = self.get_real_holdings_data()
        for holding in holdings:
            if holding.get('symbol', '').upper() == symbol.upper():
                return holding
        return None

    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary from Alpaca."""
        try:
            import sys
            import os
            
            # Import from same directory
            current_dir = os.path.dirname(__file__)
            sys.path.insert(0, current_dir)
            
            from alpaca_trading import AlpacaTradingService
            
            alpaca_service = AlpacaTradingService()
            account = alpaca_service.api.get_account()
            
            return {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'day_trade_buying_power': float(account.day_trade_buying_power),
                'regt_buying_power': float(account.regt_buying_power),
                'unrealized_pl': float(account.unrealized_pl),
                'unrealized_plpc': float(account.unrealized_plpc) * 100,
                'day_trade_count': int(account.day_trade_count),
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked,
                'pattern_day_trader': account.pattern_day_trader,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {
                'buying_power': 0.0,
                'cash': 0.0,
                'portfolio_value': 0.0,
                'unrealized_pl': 0.0,
                'unrealized_plpc': 0.0,
                'error': str(e)
            }

    def get_portfolio_allocation(self) -> List[Dict[str, Any]]:
        """Get portfolio allocation by sector/position size."""
        holdings = self.get_real_holdings_data()
        if not holdings:
            return []
        
        try:
            total_value = sum(abs(h.get('market_value', 0)) for h in holdings)
            
            allocation = []
            for holding in holdings:
                allocation_percent = (abs(holding.get('market_value', 0)) / total_value * 100) if total_value > 0 else 0
                allocation.append({
                    'symbol': holding.get('symbol'),
                    'market_value': holding.get('market_value', 0),
                    'allocation_percent': round(allocation_percent, 2),
                    'quantity': holding.get('quantity', 0),
                    'side': 'Long' if holding.get('quantity', 0) > 0 else 'Short'
                })
            
            # Sort by allocation percentage
            return sorted(allocation, key=lambda x: x['allocation_percent'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error calculating portfolio allocation: {e}")
            return []

# Global service instance
portfolio_holdings_service = PortfolioHoldingsService()

# Add async methods for the performance analytics service
class AsyncPortfolioWrapper:
    """Async wrapper for portfolio holdings service."""
    
    def __init__(self, service):
        self.service = service
    
    async def get_portfolio_summary(self):
        """Get portfolio summary asynchronously."""
        holdings = self.service.get_real_holdings_data()
        summary = self.service.calculate_portfolio_summary(holdings)
        account = self.service.get_account_summary()
        
        return {
            'total_value': account.get('portfolio_value', 0),
            'market_value': summary.get('total_market_value', 0),
            'unrealized_pnl': summary.get('total_unrealized_pnl', 0),
            'cash': account.get('cash', 0),
            'buying_power': account.get('buying_power', 0)
        }
    
    async def get_holdings(self):
        """Get holdings asynchronously."""
        holdings = self.service.get_real_holdings_data()
        
        # Format for performance analytics
        formatted_holdings = []
        for holding in holdings:
            formatted_holdings.append({
                'symbol': holding.get('symbol'),
                'quantity': holding.get('quantity'),
                'average_cost': holding.get('avg_cost'),
                'current_price': holding.get('current_price'),
                'market_value': holding.get('market_value'),
                'unrealized_pnl': holding.get('unrealized_pnl')
            })
        
        return formatted_holdings
    
    async def get_holdings_dashboard_data(self):
        """Get holdings dashboard data asynchronously."""
        return self.service.get_holdings_dashboard_data()
    
    async def get_real_holdings_data(self):
        """Get real holdings data asynchronously."""
        return self.service.get_real_holdings_data()
    
    async def get_portfolio_allocation(self):
        """Get portfolio allocation asynchronously."""
        return self.service.get_portfolio_allocation()
    
    async def get_position_by_symbol(self, symbol: str):
        """Get position by symbol asynchronously."""
        return self.service.get_position_by_symbol(symbol)
    
    async def get_account_summary(self):
        """Get account summary asynchronously."""
        return self.service.get_account_summary()
    
    async def calculate_portfolio_summary(self, holdings):
        """Calculate portfolio summary asynchronously."""
        return self.service.calculate_portfolio_summary(holdings)

# Replace the global service with async wrapper
portfolio_holdings_service = AsyncPortfolioWrapper(PortfolioHoldingsService())
