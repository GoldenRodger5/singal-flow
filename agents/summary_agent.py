"""
Summary Agent - Generates daily performance summaries and analytics.
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from services.config import Config
from agents.reasoning_agent import ReasoningAgent


class SummaryAgent:
    """Agent responsible for generating trading performance summaries and analytics."""
    
    def __init__(self):
        """Initialize the summary agent."""
        self.config = Config()
        self.reasoning_agent = ReasoningAgent()
    
    async def generate_daily_summary(self) -> Dict[str, Any]:
        """Generate comprehensive daily trading summary."""
        try:
            logger.info("Generating daily trading summary")
            
            # Get today's date
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Load trade data
            trades = await self._load_todays_trades()
            
            # Calculate performance metrics
            performance = self._calculate_daily_performance(trades)
            
            # Get strategy analytics
            strategy_stats = await self._analyze_strategy_performance(trades)
            
            # Generate insights
            insights = await self._generate_performance_insights(trades, performance)
            
            # Prepare watchlist info
            watchlist_info = await self._get_watchlist_summary()
            
            summary = {
                'date': today,
                'timestamp': datetime.now().isoformat(),
                'trade_count': len(trades),
                'performance': performance,
                'strategy_stats': strategy_stats,
                'insights': insights,
                'watchlist': watchlist_info,
                'trades': trades
            }
            
            # Save summary
            await self._save_daily_summary(summary)
            
            logger.info(f"Daily summary generated: {len(trades)} trades, {performance.get('win_rate', 0)*100:.0f}% win rate")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return self._generate_fallback_summary()
    
    async def _load_todays_trades(self) -> List[Dict[str, Any]]:
        """Load all trades executed today."""
        try:
            with open('data/trade_log.json', 'r') as f:
                all_trades = json.load(f)
            
            today = datetime.now().strftime("%Y-%m-%d")
            todays_trades = []
            
            for trade in all_trades:
                entry_time = trade.get('entry_time', '')
                if entry_time.startswith(today):
                    todays_trades.append(trade)
            
            return todays_trades
            
        except FileNotFoundError:
            logger.info("No trade log found")
            return []
        except Exception as e:
            logger.error(f"Error loading today's trades: {e}")
            return []
    
    def _calculate_daily_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate daily performance metrics."""
        try:
            if not trades:
                return {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'avg_rr': 0.0,
                    'daily_pnl': 0.0,
                    'daily_pnl_percent': 0.0,
                    'best_trade': None,
                    'worst_trade': None
                }
            
            wins = 0
            losses = 0
            total_pnl = 0.0
            rr_ratios = []
            best_trade = None
            worst_trade = None
            best_pnl = float('-inf')
            worst_pnl = float('inf')
            
            for trade in trades:
                pnl_percent = trade.get('pnl_percent', 0)
                total_pnl += pnl_percent
                
                # Track best/worst trades
                if pnl_percent > best_pnl:
                    best_pnl = pnl_percent
                    best_trade = {
                        'ticker': trade.get('ticker'),
                        'pnl_percent': pnl_percent,
                        'setup_type': trade.get('setup_type')
                    }
                
                if pnl_percent < worst_pnl:
                    worst_pnl = pnl_percent
                    worst_trade = {
                        'ticker': trade.get('ticker'),
                        'pnl_percent': pnl_percent,
                        'setup_type': trade.get('setup_type')
                    }
                
                # Win/Loss counting
                if pnl_percent > 0:
                    wins += 1
                else:
                    losses += 1
                
                # R:R ratio calculation
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                stop_loss = trade.get('stop_loss', 0)
                
                if entry_price > 0 and stop_loss > 0:
                    risk = entry_price - stop_loss
                    reward = abs(exit_price - entry_price)
                    if risk > 0:
                        rr_ratio = reward / risk
                        rr_ratios.append(rr_ratio)
            
            # Calculate metrics
            total_trades = len(trades)
            win_rate = wins / total_trades if total_trades > 0 else 0
            avg_rr = sum(rr_ratios) / len(rr_ratios) if rr_ratios else 0
            
            return {
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_rr': avg_rr,
                'daily_pnl': total_pnl,
                'daily_pnl_percent': total_pnl,  # Same as above for now
                'best_trade': best_trade,
                'worst_trade': worst_trade
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily performance: {e}")
            return {'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0, 'avg_rr': 0.0, 'daily_pnl': 0.0}
    
    async def _analyze_strategy_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by strategy type."""
        try:
            strategy_stats = {}
            
            for trade in trades:
                setup_type = trade.get('setup_type', 'Unknown')
                pnl = trade.get('pnl_percent', 0)
                
                if setup_type not in strategy_stats:
                    strategy_stats[setup_type] = {
                        'count': 0,
                        'wins': 0,
                        'total_pnl': 0.0,
                        'avg_pnl': 0.0,
                        'win_rate': 0.0
                    }
                
                stats = strategy_stats[setup_type]
                stats['count'] += 1
                stats['total_pnl'] += pnl
                
                if pnl > 0:
                    stats['wins'] += 1
            
            # Calculate averages and win rates
            for setup_type, stats in strategy_stats.items():
                stats['avg_pnl'] = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
                stats['win_rate'] = stats['wins'] / stats['count'] if stats['count'] > 0 else 0
            
            # Find best performing strategy
            best_strategy = None
            best_performance = 0
            
            for setup_type, stats in strategy_stats.items():
                if stats['count'] >= 2:  # Minimum 2 trades for significance
                    performance_score = stats['win_rate'] * stats['avg_pnl']
                    if performance_score > best_performance:
                        best_performance = performance_score
                        best_strategy = setup_type
            
            return {
                'by_strategy': strategy_stats,
                'best_strategy': best_strategy,
                'total_strategies_used': len(strategy_stats)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strategy performance: {e}")
            return {'by_strategy': {}, 'best_strategy': None, 'total_strategies_used': 0}
    
    async def _generate_performance_insights(self, trades: List[Dict[str, Any]], 
                                           performance: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from trading performance."""
        try:
            insights = []
            
            total_trades = performance.get('total_trades', 0)
            win_rate = performance.get('win_rate', 0)
            avg_rr = performance.get('avg_rr', 0)
            daily_pnl = performance.get('daily_pnl', 0)
            
            if total_trades == 0:
                insights.append("No trades executed today - market conditions may not have met criteria")
                insights.append("Continue monitoring for quality setups tomorrow")
                return insights
            
            # Win rate analysis
            if win_rate >= 0.7:
                insights.append(f"Excellent win rate of {win_rate*100:.0f}% - strategy is working well")
            elif win_rate >= 0.5:
                insights.append(f"Solid {win_rate*100:.0f}% win rate - maintain current approach")
            elif win_rate >= 0.4:
                insights.append(f"Win rate of {win_rate*100:.0f}% needs improvement - review entry criteria")
            else:
                insights.append(f"Low {win_rate*100:.0f}% win rate - consider tightening setup requirements")
            
            # R:R analysis
            if avg_rr >= 2.5:
                insights.append(f"Strong {avg_rr:.1f}:1 average R:R ratio - good risk management")
            elif avg_rr >= 2.0:
                insights.append(f"Decent {avg_rr:.1f}:1 R:R ratio - meeting minimum requirements")
            elif avg_rr >= 1.5:
                insights.append(f"R:R ratio of {avg_rr:.1f}:1 is below target - consider wider targets")
            else:
                insights.append(f"Poor {avg_rr:.1f}:1 R:R ratio - review exit strategy")
            
            # P&L analysis
            if daily_pnl > 2:
                insights.append(f"Strong daily performance with +{daily_pnl:.1f}% gain")
            elif daily_pnl > 0:
                insights.append(f"Positive day with +{daily_pnl:.1f}% gain - consistent growth")
            elif daily_pnl > -1:
                insights.append(f"Small loss of {daily_pnl:.1f}% - within acceptable risk parameters")
            else:
                insights.append(f"Significant loss of {daily_pnl:.1f}% - review risk management")
            
            # Trade frequency analysis
            if total_trades > 5:
                insights.append("High trade frequency - ensure each setup meets quality standards")
            elif total_trades >= 3:
                insights.append("Good trade frequency - maintaining selective approach")
            elif total_trades >= 1:
                insights.append("Conservative approach with few trades - quality over quantity")
            
            # Time-based insights
            current_hour = datetime.now().hour
            if current_hour < 12:
                insights.append("Early market session - momentum plays often work well")
            else:
                insights.append("Late morning session - consider range-bound strategies")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return ["Performance analysis completed - review detailed metrics"]
    
    async def _get_watchlist_summary(self) -> Dict[str, Any]:
        """Get summary of current watchlist status."""
        try:
            with open('data/watchlist_dynamic.json', 'r') as f:
                watchlist_data = json.load(f)
            
            stocks = watchlist_data.get('stocks', [])
            
            return {
                'total_stocks': len(stocks),
                'last_updated': watchlist_data.get('timestamp', ''),
                'avg_momentum_score': sum(stock.get('momentum_score', 0) for stock in stocks) / len(stocks) if stocks else 0,
                'top_stock': stocks[0].get('ticker') if stocks else None
            }
            
        except Exception as e:
            logger.error(f"Error getting watchlist summary: {e}")
            return {'total_stocks': 0, 'last_updated': '', 'avg_momentum_score': 0, 'top_stock': None}
    
    async def _save_daily_summary(self, summary: Dict[str, Any]) -> None:
        """Save daily summary to file."""
        try:
            # Load existing summaries
            try:
                with open('data/daily_summaries.json', 'r') as f:
                    summaries = json.load(f)
            except FileNotFoundError:
                summaries = []
            
            # Add today's summary
            summaries.append(summary)
            
            # Keep only last 30 days
            if len(summaries) > 30:
                summaries = summaries[-30:]
            
            # Save updated summaries
            with open('data/daily_summaries.json', 'w') as f:
                json.dump(summaries, f, indent=2)
                
            logger.info("Daily summary saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving daily summary: {e}")
    
    def _generate_fallback_summary(self) -> Dict[str, Any]:
        """Generate basic summary when full analysis fails."""
        return {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'timestamp': datetime.now().isoformat(),
            'trade_count': 0,
            'performance': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'avg_rr': 0.0,
                'daily_pnl': 0.0
            },
            'strategy_stats': {'by_strategy': {}, 'best_strategy': None},
            'insights': ["Summary generation completed with limited data"],
            'watchlist': {'total_stocks': 0},
            'trades': []
        }
    
    async def get_weekly_performance(self) -> Dict[str, Any]:
        """Generate weekly performance summary."""
        try:
            # Load last 7 daily summaries
            with open('data/daily_summaries.json', 'r') as f:
                summaries = json.load(f)
            
            # Filter last 7 days
            last_week = summaries[-7:] if len(summaries) >= 7 else summaries
            
            total_trades = sum(s['trade_count'] for s in last_week)
            total_pnl = sum(s['performance']['daily_pnl'] for s in last_week)
            avg_win_rate = sum(s['performance']['win_rate'] for s in last_week) / len(last_week) if last_week else 0
            
            return {
                'period': 'last_7_days',
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_daily_pnl': total_pnl / 7,
                'avg_win_rate': avg_win_rate,
                'trading_days': len(last_week)
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly performance: {e}")
            return {'period': 'last_7_days', 'total_trades': 0, 'total_pnl': 0.0}
    
    async def update_strategy_stats(self) -> None:
        """Update overall strategy statistics."""
        try:
            # Load all trade data
            with open('data/trade_log.json', 'r') as f:
                all_trades = json.load(f)
            
            # Calculate overall statistics
            strategy_performance = {}
            
            for trade in all_trades:
                setup_type = trade.get('setup_type', 'Unknown')
                pnl = trade.get('pnl_percent', 0)
                
                if setup_type not in strategy_performance:
                    strategy_performance[setup_type] = {
                        'total_trades': 0,
                        'wins': 0,
                        'total_pnl': 0.0,
                        'best_trade': 0.0,
                        'worst_trade': 0.0
                    }
                
                stats = strategy_performance[setup_type]
                stats['total_trades'] += 1
                stats['total_pnl'] += pnl
                
                if pnl > 0:
                    stats['wins'] += 1
                
                stats['best_trade'] = max(stats['best_trade'], pnl)
                stats['worst_trade'] = min(stats['worst_trade'], pnl)
            
            # Calculate final metrics
            for setup_type, stats in strategy_performance.items():
                stats['win_rate'] = stats['wins'] / stats['total_trades'] if stats['total_trades'] > 0 else 0
                stats['avg_pnl'] = stats['total_pnl'] / stats['total_trades'] if stats['total_trades'] > 0 else 0
            
            # Save strategy stats
            strategy_stats = {
                'last_updated': datetime.now().isoformat(),
                'total_trades': len(all_trades),
                'strategies': strategy_performance
            }
            
            with open('data/strategy_stats.json', 'w') as f:
                json.dump(strategy_stats, f, indent=2)
                
            logger.info("Strategy statistics updated")
            
        except Exception as e:
            logger.error(f"Error updating strategy stats: {e}")
