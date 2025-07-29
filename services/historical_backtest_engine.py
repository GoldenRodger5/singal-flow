"""
Historical Backtesting Engine - Validates AI strategies against historical data.
"""
import asyncio
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta, time
from dataclasses import dataclass, asdict
from loguru import logger
import statistics
from collections import defaultdict

from services.config import Config
from services.data_provider import PolygonDataProvider


@dataclass
class BacktestTrade:
    """Individual trade in backtest."""
    ticker: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    direction: str  # 'long', 'short'
    quantity: int
    exit_reason: str
    pnl: float
    pnl_percent: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    trade_duration_hours: float
    signals_at_entry: Dict[str, Any]
    confidence_score: float


@dataclass
class BacktestResults:
    """Comprehensive backtest results."""
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_winner: float
    avg_loser: float
    largest_winner: float
    largest_loser: float
    avg_trade_duration: float
    trades_per_day: float
    exposure_time_percent: float
    trades: List[BacktestTrade]
    daily_returns: List[float]
    equity_curve: List[Tuple[datetime, float]]
    monthly_returns: Dict[str, float]
    strategy_stats: Dict[str, Any]


class HistoricalBacktestEngine:
    """Advanced backtesting engine for strategy validation."""
    
    def __init__(self):
        """Initialize the backtest engine."""
        self.config = Config()
        self.data_provider = PolygonDataProvider()
        
        # Backtest parameters
        self.initial_capital = 100000  # $100k starting capital
        self.commission_per_trade = 1.0  # $1 per trade
        self.slippage_percent = 0.001   # 0.1% slippage
        
        # Risk management
        self.max_position_size = 0.1    # 10% max per trade
        self.max_daily_trades = 5
        self.stop_loss_percent = 0.05   # 5% stop loss
        self.take_profit_percent = 0.10 # 10% take profit
        
        # Files
        self.backtest_results_file = 'data/backtest_results.json'
        self.strategy_performance_file = 'data/strategy_performance.json'
    
    async def run_comprehensive_backtest(self, start_date: datetime, end_date: datetime,
                                       ticker_list: List[str], strategy_config: Dict[str, Any]) -> BacktestResults:
        """Run comprehensive backtest across multiple timeframes and tickers."""
        logger.info(f"Starting comprehensive backtest: {start_date.date()} to {end_date.date()}")
        logger.info(f"Testing {len(ticker_list)} tickers with strategy: {strategy_config.get('name', 'Custom')}")
        
        # Initialize backtest state
        capital = self.initial_capital
        positions = {}
        trades = []
        daily_pnl = defaultdict(float)
        equity_curve = [(start_date, capital)]
        
        # Get historical data for all tickers
        logger.info("Loading historical data...")
        historical_data = await self._load_historical_data(ticker_list, start_date, end_date)
        
        if not historical_data:
            logger.error("No historical data available for backtesting")
            return self._empty_backtest_results(start_date, end_date)
        
        # Run day-by-day simulation
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            daily_trades_count = 0
            
            # Process each ticker for this day
            for ticker in ticker_list:
                if daily_trades_count >= self.max_daily_trades:
                    break
                
                # Get market data for this day
                market_data = self._get_market_data_for_date(historical_data, ticker, current_date)
                if not market_data:
                    continue
                
                # Check for exit signals on existing positions
                if ticker in positions:
                    exit_signal = await self._check_exit_signals(
                        positions[ticker], market_data, current_date
                    )
                    
                    if exit_signal:
                        trade = await self._execute_exit(positions[ticker], market_data, exit_signal, current_date)
                        if trade:
                            trades.append(trade)
                            capital += trade.pnl - self.commission_per_trade
                            daily_pnl[current_date.date()] += trade.pnl
                            del positions[ticker]
                
                # Check for entry signals (only if not already in position)
                if ticker not in positions:
                    entry_signal = await self._generate_entry_signal(
                        market_data, strategy_config, current_date
                    )
                    
                    if entry_signal and entry_signal['confidence'] >= strategy_config.get('min_confidence', 7.0):
                        position = await self._execute_entry(
                            ticker, market_data, entry_signal, capital, current_date
                        )
                        
                        if position:
                            positions[ticker] = position
                            daily_trades_count += 1
                            capital -= position['position_value'] + self.commission_per_trade
            
            # Update equity curve
            total_portfolio_value = capital
            for position in positions.values():
                current_price = self._get_current_price(historical_data, position['ticker'], current_date)
                if current_price:
                    unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
                    if position['direction'] == 'short':
                        unrealized_pnl = -unrealized_pnl
                    total_portfolio_value += position['position_value'] + unrealized_pnl
            
            equity_curve.append((current_date, total_portfolio_value))
            
            current_date += timedelta(days=1)
        
        # Close any remaining positions at end date
        for ticker, position in positions.items():
            final_price = self._get_current_price(historical_data, ticker, end_date)
            if final_price:
                exit_signal = {'reason': 'backtest_end', 'price': final_price}
                trade = await self._execute_exit(position, {'close': final_price}, exit_signal, end_date)
                if trade:
                    trades.append(trade)
                    capital += trade.pnl - self.commission_per_trade
        
        # Calculate comprehensive results
        results = self._calculate_backtest_results(
            start_date, end_date, trades, equity_curve, daily_pnl
        )
        
        # Save results
        await self._save_backtest_results(results, strategy_config)
        
        logger.info(f"Backtest completed: {results.total_trades} trades, "
                   f"{results.win_rate*100:.1f}% win rate, "
                   f"{results.total_return_percent:.1f}% total return")
        
        return results
    
    async def _load_historical_data(self, tickers: List[str], start_date: datetime, 
                                  end_date: datetime) -> Dict[str, pd.DataFrame]:
        """Load historical data for backtesting."""
        historical_data = {}
        
        for ticker in tickers:
            try:
                # This would integrate with your actual data provider
                # For now, we'll create a placeholder structure
                dates = pd.date_range(start_date, end_date, freq='D')
                
                # Simulate realistic price data
                base_price = 25.0  # Starting price
                returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% daily return, 2% volatility
                prices = [base_price]
                
                for ret in returns[1:]:
                    prices.append(prices[-1] * (1 + ret))
                
                # Create DataFrame with OHLCV data
                df = pd.DataFrame({
                    'date': dates,
                    'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                    'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                    'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                    'close': prices,
                    'volume': [np.random.randint(100000, 1000000) for _ in prices]
                })
                
                # Add technical indicators
                df = await self._add_technical_indicators(df)
                
                historical_data[ticker] = df
                
            except Exception as e:
                logger.error(f"Error loading data for {ticker}: {e}")
                continue
        
        return historical_data
    
    async def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to historical data."""
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # VWAP
        df['vwap'] = self._calculate_vwap(df)
        
        # MACD
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # Volume metrics
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP indicator."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }
    
    def _get_market_data_for_date(self, historical_data: Dict[str, pd.DataFrame], 
                                ticker: str, date: datetime) -> Optional[Dict[str, Any]]:
        """Get market data for a specific ticker and date."""
        if ticker not in historical_data:
            return None
        
        df = historical_data[ticker]
        date_str = date.date()
        
        # Find the row for this date
        matching_rows = df[df['date'].dt.date == date_str]
        if matching_rows.empty:
            return None
        
        row = matching_rows.iloc[0]
        
        return {
            'ticker': ticker,
            'date': date,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
            'rsi': row['rsi'],
            'vwap': row['vwap'],
            'macd': row['macd'],
            'macd_signal': row['macd_signal'],
            'volume_ratio': row['volume_ratio']
        }
    
    async def _generate_entry_signal(self, market_data: Dict[str, Any], 
                                   strategy_config: Dict[str, Any], 
                                   date: datetime) -> Optional[Dict[str, Any]]:
        """Generate entry signal based on strategy configuration."""
        signals = {}
        confidence = 5.0  # Base confidence
        
        # RSI signal
        rsi = market_data.get('rsi', 50)
        if rsi <= strategy_config.get('rsi_oversold', 30):
            signals['rsi_oversold'] = True
            confidence += 1.2
        elif rsi >= strategy_config.get('rsi_overbought', 70):
            signals['rsi_overbought'] = True
            confidence -= 0.8
        
        # VWAP signal
        price = market_data.get('close', 0)
        vwap = market_data.get('vwap', 0)
        if price < vwap * 0.99:  # Price below VWAP with margin
            signals['vwap_bounce'] = True
            confidence += 1.0
        
        # MACD signal
        macd = market_data.get('macd', 0)
        macd_signal = market_data.get('macd_signal', 0)
        if macd > macd_signal and macd > 0:
            signals['macd_bullish'] = True
            confidence += 0.8
        
        # Volume signal
        volume_ratio = market_data.get('volume_ratio', 1)
        if volume_ratio >= strategy_config.get('volume_spike_threshold', 2.0):
            signals['volume_spike'] = True
            confidence += 0.6
        
        # Time-based signal (avoid end of day)
        hour = date.hour
        if 10 <= hour <= 15:  # Good trading hours
            confidence += 0.2
        
        # Only generate signal if minimum conditions met
        min_signals = strategy_config.get('min_signals_required', 2)
        if len([s for s in signals.values() if s]) >= min_signals:
            return {
                'direction': 'long',  # Focus on long trades for simplicity
                'confidence': min(confidence, 10.0),
                'signals': signals,
                'entry_price': price,
                'timestamp': date
            }
        
        return None
    
    async def _execute_entry(self, ticker: str, market_data: Dict[str, Any], 
                           entry_signal: Dict[str, Any], available_capital: float,
                           date: datetime) -> Optional[Dict[str, Any]]:
        """Execute entry trade."""
        entry_price = entry_signal['entry_price']
        direction = entry_signal['direction']
        
        # Calculate position size
        position_value = available_capital * self.max_position_size
        quantity = int(position_value / (entry_price * (1 + self.slippage_percent)))
        
        if quantity <= 0:
            return None
        
        # Apply slippage
        actual_entry_price = entry_price * (1 + self.slippage_percent)
        actual_position_value = quantity * actual_entry_price
        
        # Calculate stop loss and take profit
        if direction == 'long':
            stop_loss = actual_entry_price * (1 - self.stop_loss_percent)
            take_profit = actual_entry_price * (1 + self.take_profit_percent)
        else:
            stop_loss = actual_entry_price * (1 + self.stop_loss_percent)
            take_profit = actual_entry_price * (1 - self.take_profit_percent)
        
        return {
            'ticker': ticker,
            'entry_time': date,
            'entry_price': actual_entry_price,
            'direction': direction,
            'quantity': quantity,
            'position_value': actual_position_value,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'signals_at_entry': entry_signal['signals'],
            'confidence_score': entry_signal['confidence']
        }
    
    async def _check_exit_signals(self, position: Dict[str, Any], 
                                market_data: Dict[str, Any], date: datetime) -> Optional[Dict[str, Any]]:
        """Check for exit signals on existing position."""
        current_price = market_data.get('close', 0)
        
        if current_price == 0:
            return None
        
        # Check stop loss
        if position['direction'] == 'long' and current_price <= position['stop_loss']:
            return {'reason': 'stop_loss', 'price': current_price}
        elif position['direction'] == 'short' and current_price >= position['stop_loss']:
            return {'reason': 'stop_loss', 'price': current_price}
        
        # Check take profit
        if position['direction'] == 'long' and current_price >= position['take_profit']:
            return {'reason': 'take_profit', 'price': current_price}
        elif position['direction'] == 'short' and current_price <= position['take_profit']:
            return {'reason': 'take_profit', 'price': current_price}
        
        # Check time-based exit (max 2 days)
        time_in_position = (date - position['entry_time']).total_seconds() / 3600
        if time_in_position >= 48:  # 48 hours
            return {'reason': 'time_exit', 'price': current_price}
        
        # Check RSI reversal
        rsi = market_data.get('rsi', 50)
        if position['direction'] == 'long' and rsi >= 75:
            return {'reason': 'rsi_exit', 'price': current_price}
        
        return None
    
    async def _execute_exit(self, position: Dict[str, Any], market_data: Dict[str, Any],
                          exit_signal: Dict[str, Any], date: datetime) -> Optional[BacktestTrade]:
        """Execute exit trade."""
        exit_price = exit_signal['price']
        
        # Apply slippage
        if position['direction'] == 'long':
            actual_exit_price = exit_price * (1 - self.slippage_percent)
        else:
            actual_exit_price = exit_price * (1 + self.slippage_percent)
        
        # Calculate P&L
        if position['direction'] == 'long':
            pnl = (actual_exit_price - position['entry_price']) * position['quantity']
        else:
            pnl = (position['entry_price'] - actual_exit_price) * position['quantity']
        
        pnl_percent = pnl / position['position_value']
        
        # Calculate trade duration
        trade_duration = (date - position['entry_time']).total_seconds() / 3600
        
        return BacktestTrade(
            ticker=position['ticker'],
            entry_time=position['entry_time'],
            entry_price=position['entry_price'],
            exit_time=date,
            exit_price=actual_exit_price,
            direction=position['direction'],
            quantity=position['quantity'],
            exit_reason=exit_signal['reason'],
            pnl=pnl,
            pnl_percent=pnl_percent,
            max_favorable_excursion=0.0,  # Would need tick data for accurate calculation
            max_adverse_excursion=0.0,    # Would need tick data for accurate calculation
            trade_duration_hours=trade_duration,
            signals_at_entry=position['signals_at_entry'],
            confidence_score=position['confidence_score']
        )
    
    def _get_current_price(self, historical_data: Dict[str, pd.DataFrame], 
                          ticker: str, date: datetime) -> Optional[float]:
        """Get current price for a ticker on a specific date."""
        market_data = self._get_market_data_for_date(historical_data, ticker, date)
        return market_data.get('close') if market_data else None
    
    def _calculate_backtest_results(self, start_date: datetime, end_date: datetime,
                                  trades: List[BacktestTrade], equity_curve: List[Tuple[datetime, float]],
                                  daily_pnl: Dict) -> BacktestResults:
        """Calculate comprehensive backtest results."""
        if not trades:
            return self._empty_backtest_results(start_date, end_date)
        
        # Basic stats
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L stats
        total_pnl = sum(t.pnl for t in trades)
        initial_capital = equity_curve[0][1] if equity_curve else self.initial_capital
        final_capital = equity_curve[-1][1] if equity_curve else initial_capital
        total_return_percent = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Win/Loss stats
        winners = [t.pnl for t in trades if t.pnl > 0]
        losers = [t.pnl for t in trades if t.pnl < 0]
        
        avg_winner = statistics.mean(winners) if winners else 0
        avg_loser = statistics.mean(losers) if losers else 0
        largest_winner = max(winners) if winners else 0
        largest_loser = min(losers) if losers else 0
        
        # Drawdown calculation
        equity_values = [eq[1] for eq in equity_curve]
        peak = equity_values[0]
        max_drawdown = 0
        max_drawdown_percent = 0
        
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = peak - value
            drawdown_percent = drawdown / peak if peak > 0 else 0
            
            max_drawdown = max(max_drawdown, drawdown)
            max_drawdown_percent = max(max_drawdown_percent, drawdown_percent)
        
        # Risk metrics
        daily_returns = []
        if len(equity_curve) > 1:
            for i in range(1, len(equity_curve)):
                prev_value = equity_curve[i-1][1]
                curr_value = equity_curve[i][1]
                daily_return = (curr_value - prev_value) / prev_value if prev_value > 0 else 0
                daily_returns.append(daily_return)
        
        # Sharpe ratio (simplified)
        if daily_returns:
            avg_return = statistics.mean(daily_returns)
            return_std = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
            sharpe_ratio = (avg_return * 252) / (return_std * np.sqrt(252)) if return_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Sortino ratio (downside deviation)
        downside_returns = [r for r in daily_returns if r < 0]
        if downside_returns:
            downside_std = statistics.stdev(downside_returns)
            sortino_ratio = (statistics.mean(daily_returns) * 252) / (downside_std * np.sqrt(252))
        else:
            sortino_ratio = sharpe_ratio
        
        # Profit factor
        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Trading frequency
        days_in_backtest = (end_date - start_date).days
        trades_per_day = total_trades / days_in_backtest if days_in_backtest > 0 else 0
        
        # Trade duration
        avg_trade_duration = statistics.mean([t.trade_duration_hours for t in trades]) if trades else 0
        
        # Monthly returns
        monthly_returns = {}
        current_month = start_date.replace(day=1)
        while current_month <= end_date:
            month_str = current_month.strftime('%Y-%m')
            month_trades = [t for t in trades if t.entry_time.strftime('%Y-%m') == month_str]
            month_pnl = sum(t.pnl for t in month_trades)
            monthly_returns[month_str] = month_pnl
            
            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)
        
        return BacktestResults(
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return_percent=total_return_percent,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_winner=avg_winner,
            avg_loser=avg_loser,
            largest_winner=largest_winner,
            largest_loser=largest_loser,
            avg_trade_duration=avg_trade_duration,
            trades_per_day=trades_per_day,
            exposure_time_percent=0.0,  # Would need more detailed calculation
            trades=trades,
            daily_returns=daily_returns,
            equity_curve=equity_curve,
            monthly_returns=monthly_returns,
            strategy_stats={}
        )
    
    def _empty_backtest_results(self, start_date: datetime, end_date: datetime) -> BacktestResults:
        """Return empty backtest results."""
        return BacktestResults(
            start_date=start_date,
            end_date=end_date,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_return_percent=0.0,
            max_drawdown=0.0,
            max_drawdown_percent=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            profit_factor=0.0,
            avg_winner=0.0,
            avg_loser=0.0,
            largest_winner=0.0,
            largest_loser=0.0,
            avg_trade_duration=0.0,
            trades_per_day=0.0,
            exposure_time_percent=0.0,
            trades=[],
            daily_returns=[],
            equity_curve=[],
            monthly_returns={},
            strategy_stats={}
        )
    
    async def _save_backtest_results(self, results: BacktestResults, 
                                   strategy_config: Dict[str, Any]) -> None:
        """Save backtest results to file."""
        try:
            # Convert results to dict
            results_dict = asdict(results)
            
            # Convert datetime objects to ISO strings
            results_dict['start_date'] = results.start_date.isoformat()
            results_dict['end_date'] = results.end_date.isoformat()
            
            # Convert trades
            results_dict['trades'] = []
            for trade in results.trades:
                trade_dict = asdict(trade)
                trade_dict['entry_time'] = trade.entry_time.isoformat()
                trade_dict['exit_time'] = trade.exit_time.isoformat()
                results_dict['trades'].append(trade_dict)
            
            # Convert equity curve
            results_dict['equity_curve'] = [
                [dt.isoformat(), value] for dt, value in results.equity_curve
            ]
            
            # Add strategy config
            results_dict['strategy_config'] = strategy_config
            results_dict['backtest_timestamp'] = datetime.now().isoformat()
            
            # Save to file
            with open(self.backtest_results_file, 'w') as f:
                json.dump(results_dict, f, indent=2)
            
            logger.info(f"Backtest results saved to {self.backtest_results_file}")
            
        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")
    
    async def compare_strategies(self, strategy_configs: List[Dict[str, Any]], 
                               start_date: datetime, end_date: datetime,
                               ticker_list: List[str]) -> Dict[str, Any]:
        """Compare multiple strategies using the same data."""
        logger.info(f"Comparing {len(strategy_configs)} strategies")
        
        strategy_results = {}
        
        for config in strategy_configs:
            strategy_name = config.get('name', 'Unknown')
            logger.info(f"Testing strategy: {strategy_name}")
            
            results = await self.run_comprehensive_backtest(
                start_date, end_date, ticker_list, config
            )
            
            strategy_results[strategy_name] = {
                'config': config,
                'results': results,
                'performance_score': self._calculate_performance_score(results)
            }
        
        # Rank strategies by performance score
        ranked_strategies = sorted(
            strategy_results.items(),
            key=lambda x: x[1]['performance_score'],
            reverse=True
        )
        
        comparison_results = {
            'comparison_timestamp': datetime.now().isoformat(),
            'test_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'strategies_tested': len(strategy_configs),
            'best_strategy': ranked_strategies[0][0] if ranked_strategies else None,
            'strategy_rankings': [
                {
                    'rank': i + 1,
                    'strategy_name': name,
                    'performance_score': data['performance_score'],
                    'win_rate': data['results'].win_rate,
                    'total_return': data['results'].total_return_percent,
                    'sharpe_ratio': data['results'].sharpe_ratio,
                    'max_drawdown': data['results'].max_drawdown_percent
                }
                for i, (name, data) in enumerate(ranked_strategies)
            ],
            'detailed_results': strategy_results
        }
        
        # Save comparison
        comparison_file = 'data/strategy_comparison.json'
        with open(comparison_file, 'w') as f:
            # Convert BacktestResults objects to dicts for serialization
            serializable_results = {}
            for name, data in comparison_results['detailed_results'].items():
                serializable_results[name] = {
                    'config': data['config'],
                    'performance_score': data['performance_score'],
                    'results': asdict(data['results'])
                }
            
            comparison_results['detailed_results'] = serializable_results
            json.dump(comparison_results, f, indent=2, default=str)
        
        logger.info(f"Strategy comparison completed. Best strategy: {comparison_results['best_strategy']}")
        
        return comparison_results
    
    def _calculate_performance_score(self, results: BacktestResults) -> float:
        """Calculate overall performance score for strategy ranking."""
        if results.total_trades == 0:
            return 0.0
        
        # Weighted combination of multiple metrics
        return (
            results.total_return_percent * 0.3 +
            results.win_rate * 100 * 0.2 +
            results.sharpe_ratio * 20 * 0.2 +
            results.profit_factor * 20 * 0.15 +
            (100 - results.max_drawdown_percent * 100) * 0.15
        )
    
    def get_optimization_suggestions(self, results: BacktestResults) -> List[str]:
        """Generate optimization suggestions based on backtest results."""
        suggestions = []
        
        if results.win_rate < 0.5:
            suggestions.append("Win rate below 50% - consider tightening entry criteria")
        
        if results.max_drawdown_percent > 0.15:
            suggestions.append("High drawdown - implement stricter stop losses")
        
        if results.sharpe_ratio < 1.0:
            suggestions.append("Low risk-adjusted returns - optimize position sizing")
        
        if results.avg_trade_duration > 48:
            suggestions.append("Long average holding period - consider shorter timeframes")
        
        if results.profit_factor < 1.5:
            suggestions.append("Low profit factor - improve win rate or risk/reward ratio")
        
        return suggestions
