"""
Performance Analytics Service
Calculates real trading performance, portfolio metrics, and analytics
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from loguru import logger
from dataclasses import dataclass
import math

from services.database_manager import db_manager
from services.portfolio_holdings_service import portfolio_holdings_service
from services.real_time_market_data import market_data_service

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    total_return: float
    daily_return: float
    weekly_return: float
    monthly_return: float
    ytd_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profitable_trades: int
    average_win: float
    average_loss: float
    current_balance: float
    portfolio_value: float
    unrealized_pnl: float
    realized_pnl: float

class PerformanceAnalyticsService:
    """Service for calculating trading performance and portfolio analytics."""
    
    def __init__(self):
        """Initialize performance analytics service."""
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        self.initial_balance = 10000.0  # Starting portfolio value
        
        logger.info("Performance Analytics Service initialized")
    
    async def get_overall_performance(self) -> PerformanceMetrics:
        """Calculate overall portfolio performance metrics."""
        try:
            # Get current portfolio data
            portfolio_data = await portfolio_holdings_service.get_portfolio_summary()
            
            # Get trading history
            trades = await db_manager.get_trading_history(days=365)  # Last year
            
            # Get account balance history
            balance_history = await db_manager.get_balance_history(days=365)
            
            # Calculate metrics
            metrics = await self._calculate_performance_metrics(
                portfolio_data, trades, balance_history
            )
            
            logger.debug("Calculated overall performance metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating overall performance: {e}")
            return self._get_default_metrics()
            
        except Exception as e:
            logger.error(f"Error calculating overall performance: {e}")
            return self._get_default_metrics()
    
    async def get_daily_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily performance data for the last N days."""
        try:
            # Get daily balance history
            balance_history = await db_manager.get_balance_history(days=days)
            
            if not balance_history:
                return []
            
            daily_performance = []
            previous_balance = self.initial_balance
            
            for i, day_data in enumerate(balance_history):
                current_balance = day_data.get('total_value', previous_balance)
                daily_return = ((current_balance / previous_balance) - 1) * 100 if previous_balance > 0 else 0
                
                daily_performance.append({
                    'date': day_data.get('date', datetime.now().date().isoformat()),
                    'balance': round(current_balance, 2),
                    'daily_return': round(daily_return, 2),
                    'cumulative_return': round(((current_balance / self.initial_balance) - 1) * 100, 2),
                    'trades_count': day_data.get('trades_count', 0),
                    'pnl': round(current_balance - previous_balance, 2)
                })
                
                previous_balance = current_balance
            
            logger.debug(f"Retrieved {len(daily_performance)} days of performance data")
            return daily_performance
            
        except Exception as e:
            logger.error(f"Error getting daily performance: {e}")
            return []
    
    async def get_position_performance(self) -> List[Dict[str, Any]]:
        """Get performance for each position in the portfolio."""
        try:
            holdings = await portfolio_holdings_service.get_holdings()
            
            if not holdings:
                return []
            
            position_performance = []
            
            # Get current market prices
            symbols = [holding['symbol'] for holding in holdings]
            async with market_data_service:
                current_prices = await market_data_service.get_multiple_quotes(symbols)
            
            for holding in holdings:
                symbol = holding['symbol']
                shares = holding['quantity']
                avg_cost = holding['average_cost']
                
                if symbol in current_prices:
                    current_price = current_prices[symbol].price
                    market_value = shares * current_price
                    cost_basis = shares * avg_cost
                    unrealized_pnl = market_value - cost_basis
                    unrealized_return = (unrealized_pnl / cost_basis) * 100 if cost_basis > 0 else 0
                    
                    # Get trading history for this symbol
                    symbol_trades = await db_manager.get_symbol_trading_history(symbol)
                    realized_pnl = sum(trade.get('pnl', 0) for trade in symbol_trades)
                    
                    position_performance.append({
                        'symbol': symbol,
                        'shares': shares,
                        'avg_cost': round(avg_cost, 2),
                        'current_price': round(current_price, 2),
                        'market_value': round(market_value, 2),
                        'cost_basis': round(cost_basis, 2),
                        'unrealized_pnl': round(unrealized_pnl, 2),
                        'unrealized_return': round(unrealized_return, 2),
                        'realized_pnl': round(realized_pnl, 2),
                        'total_return': round(unrealized_return, 2),  # For open positions
                        'change_today': round(current_prices[symbol].change_percent, 2)
                    })
            
            # Sort by unrealized PnL descending
            position_performance.sort(key=lambda x: x['unrealized_pnl'], reverse=True)
            
            logger.debug(f"Calculated performance for {len(position_performance)} positions")
            return position_performance
            
        except Exception as e:
            logger.error(f"Error getting position performance: {e}")
            return []
    
    async def get_trading_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get detailed trading statistics."""
        try:
            trades = await db_manager.get_trading_history(days=days)
            
            if not trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'average_win': 0.0,
                    'average_loss': 0.0,
                    'largest_win': 0.0,
                    'largest_loss': 0.0,
                    'consecutive_wins': 0,
                    'consecutive_losses': 0,
                    'total_commissions': 0.0
                }
            
            # Separate winning and losing trades
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
            
            total_trades = len(trades)
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            
            # Calculate statistics
            win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
            
            total_wins = sum(t.get('pnl', 0) for t in winning_trades)
            total_losses = abs(sum(t.get('pnl', 0) for t in losing_trades))
            
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            average_win = total_wins / win_count if win_count > 0 else 0
            average_loss = total_losses / loss_count if loss_count > 0 else 0
            
            largest_win = max((t.get('pnl', 0) for t in winning_trades), default=0)
            largest_loss = min((t.get('pnl', 0) for t in losing_trades), default=0)
            
            # Calculate consecutive wins/losses
            consecutive_wins, consecutive_losses = self._calculate_consecutive_trades(trades)
            
            # Calculate total commissions
            total_commissions = sum(t.get('commission', 0) for t in trades)
            
            return {
                'total_trades': total_trades,
                'winning_trades': win_count,
                'losing_trades': loss_count,
                'win_rate': round(win_rate, 2),
                'profit_factor': round(profit_factor, 2),
                'average_win': round(average_win, 2),
                'average_loss': round(abs(average_loss), 2),
                'largest_win': round(largest_win, 2),
                'largest_loss': round(abs(largest_loss), 2),
                'consecutive_wins': consecutive_wins,
                'consecutive_losses': consecutive_losses,
                'total_commissions': round(total_commissions, 2),
                'net_profit': round(total_wins - total_losses, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting trading statistics: {e}")
            return {}
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio risk metrics."""
        try:
            # Get portfolio balance history
            balance_history = await db_manager.get_balance_history(days=252)  # ~1 year
            
            if len(balance_history) < 30:
                return {
                    'volatility': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'var_95': 0.0,
                    'beta': 0.0,
                    'alpha': 0.0
                }
            
            # Calculate daily returns
            returns = []
            for i in range(1, len(balance_history)):
                prev_value = balance_history[i-1].get('total_value', self.initial_balance)
                curr_value = balance_history[i].get('total_value', self.initial_balance)
                
                if prev_value > 0:
                    daily_return = (curr_value / prev_value) - 1
                    returns.append(daily_return)
            
            if not returns:
                return self._get_default_risk_metrics()
            
            # Calculate volatility (annualized)
            volatility = self._calculate_volatility(returns)
            
            # Calculate Sharpe ratio
            avg_return = sum(returns) / len(returns)
            excess_return = avg_return - (self.risk_free_rate / 252)  # Daily risk-free rate
            sharpe_ratio = (excess_return / volatility * math.sqrt(252)) if volatility > 0 else 0
            
            # Calculate maximum drawdown
            max_drawdown = self._calculate_max_drawdown(balance_history)
            
            # Calculate VaR (95% confidence)
            var_95 = self._calculate_var(returns, 0.05)
            
            # Beta and Alpha (compared to market - using SPY as proxy)
            beta, alpha = await self._calculate_beta_alpha(returns)
            
            return {
                'volatility': round(volatility * 100, 2),  # Convert to percentage
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown, 2),
                'var_95': round(var_95 * 100, 2),  # Convert to percentage
                'beta': round(beta, 2),
                'alpha': round(alpha * 100, 2)  # Convert to percentage
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return self._get_default_risk_metrics()
    
    async def _calculate_performance_metrics(self, portfolio_data, trades, balance_history) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        try:
            current_balance = portfolio_data.get('total_value', self.initial_balance)
            
            # Calculate returns
            total_return = ((current_balance / self.initial_balance) - 1) * 100
            
            # Calculate period returns
            daily_return = self._calculate_period_return(balance_history, 1)
            weekly_return = self._calculate_period_return(balance_history, 7)
            monthly_return = self._calculate_period_return(balance_history, 30)
            ytd_return = self._calculate_ytd_return(balance_history)
            
            # Calculate Sharpe ratio and max drawdown
            risk_metrics = await self.get_risk_metrics()
            sharpe_ratio = risk_metrics.get('sharpe_ratio', 0.0)
            max_drawdown = risk_metrics.get('max_drawdown', 0.0)
            
            # Calculate trading statistics
            trading_stats = await self.get_trading_statistics(days=365)
            win_rate = trading_stats.get('win_rate', 0.0)
            total_trades = trading_stats.get('total_trades', 0)
            profitable_trades = trading_stats.get('winning_trades', 0)
            average_win = trading_stats.get('average_win', 0.0)
            average_loss = trading_stats.get('average_loss', 0.0)
            
            # Calculate P&L
            unrealized_pnl = portfolio_data.get('unrealized_pnl', 0.0)
            realized_pnl = sum(trade.get('pnl', 0) for trade in trades)
            
            return PerformanceMetrics(
                total_return=round(total_return, 2),
                daily_return=round(daily_return, 2),
                weekly_return=round(weekly_return, 2),
                monthly_return=round(monthly_return, 2),
                ytd_return=round(ytd_return, 2),
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                profitable_trades=profitable_trades,
                average_win=average_win,
                average_loss=average_loss,
                current_balance=round(current_balance, 2),
                portfolio_value=round(portfolio_data.get('market_value', 0.0), 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                realized_pnl=round(realized_pnl, 2)
            )
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return self._get_default_metrics()
    
    def _calculate_period_return(self, balance_history: List[Dict], days: int) -> float:
        """Calculate return for a specific period."""
        try:
            if len(balance_history) < days + 1:
                return 0.0
            
            current_value = balance_history[-1].get('total_value', self.initial_balance)
            past_value = balance_history[-(days + 1)].get('total_value', self.initial_balance)
            
            if past_value > 0:
                return ((current_value / past_value) - 1) * 100
            
            return 0.0
            
        except (IndexError, KeyError):
            return 0.0
    
    def _calculate_ytd_return(self, balance_history: List[Dict]) -> float:
        """Calculate year-to-date return."""
        try:
            if not balance_history:
                return 0.0
            
            current_year = datetime.now().year
            
            # Find first balance entry of current year
            ytd_start_value = self.initial_balance
            for entry in balance_history:
                entry_date = entry.get('date')
                if isinstance(entry_date, str):
                    entry_date = datetime.fromisoformat(entry_date).date()
                
                if entry_date.year == current_year:
                    ytd_start_value = entry.get('total_value', self.initial_balance)
                    break
            
            current_value = balance_history[-1].get('total_value', self.initial_balance)
            
            if ytd_start_value > 0:
                return ((current_value / ytd_start_value) - 1) * 100
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate volatility from returns."""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        
        return math.sqrt(variance)
    
    def _calculate_max_drawdown(self, balance_history: List[Dict]) -> float:
        """Calculate maximum drawdown."""
        if len(balance_history) < 2:
            return 0.0
        
        peak = 0
        max_drawdown = 0
        
        for entry in balance_history:
            value = entry.get('total_value', self.initial_balance)
            
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk."""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int(confidence * len(sorted_returns))
        
        return sorted_returns[index] if index < len(sorted_returns) else 0.0
    
    async def _calculate_beta_alpha(self, returns: List[float]) -> Tuple[float, float]:
        """Calculate beta and alpha relative to market (SPY)."""
        try:
            # Get SPY historical data for comparison
            async with market_data_service:
                spy_data = await market_data_service.get_historical_data('SPY', days=len(returns))
            
            if len(spy_data) < len(returns):
                return 1.0, 0.0  # Default beta = 1, alpha = 0
            
            # Calculate SPY returns
            spy_returns = []
            for i in range(1, min(len(spy_data), len(returns) + 1)):
                prev_close = spy_data[i-1]['close']
                curr_close = spy_data[i]['close']
                spy_return = (curr_close / prev_close) - 1
                spy_returns.append(spy_return)
            
            # Calculate beta and alpha
            if len(spy_returns) == len(returns) and len(returns) > 1:
                # Covariance and variance calculations
                mean_portfolio = sum(returns) / len(returns)
                mean_market = sum(spy_returns) / len(spy_returns)
                
                covariance = sum((returns[i] - mean_portfolio) * (spy_returns[i] - mean_market) 
                               for i in range(len(returns))) / (len(returns) - 1)
                
                market_variance = sum((r - mean_market) ** 2 for r in spy_returns) / (len(spy_returns) - 1)
                
                beta = covariance / market_variance if market_variance > 0 else 1.0
                alpha = mean_portfolio - beta * mean_market
                
                return beta, alpha * 252  # Annualize alpha
            
            return 1.0, 0.0
            
        except Exception as e:
            logger.error(f"Error calculating beta/alpha: {e}")
            return 1.0, 0.0
    
    def _calculate_consecutive_trades(self, trades: List[Dict]) -> Tuple[int, int]:
        """Calculate consecutive wins and losses."""
        if not trades:
            return 0, 0
        
        # Sort trades by date
        sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', datetime.now()))
        
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in sorted_trades:
            pnl = trade.get('pnl', 0)
            
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        return max_consecutive_wins, max_consecutive_losses
    
    def _get_default_metrics(self) -> PerformanceMetrics:
        """Return default performance metrics."""
        return PerformanceMetrics(
            total_return=0.0,
            daily_return=0.0,
            weekly_return=0.0,
            monthly_return=0.0,
            ytd_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            total_trades=0,
            profitable_trades=0,
            average_win=0.0,
            average_loss=0.0,
            current_balance=self.initial_balance,
            portfolio_value=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0
        )
    
    def _get_default_risk_metrics(self) -> Dict[str, Any]:
        """Return default risk metrics."""
        return {
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'var_95': 0.0,
            'beta': 1.0,
            'alpha': 0.0
        }

# Global instance
performance_service = PerformanceAnalyticsService()
performance_analytics_service = performance_service  # Alias for consistency

# Export for easy importing
__all__ = ['performance_service', 'performance_analytics_service', 'PerformanceAnalyticsService', 'PerformanceMetrics']
