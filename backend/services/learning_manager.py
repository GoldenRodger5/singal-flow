"""
Learning Manager - Orchestrates all AI learning components and continuous improvement.
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from services.config import Config
from services.ai_learning_engine import AILearningEngine
from services.enhanced_decision_logger import EnhancedDecisionLogger
from services.historical_backtest_engine import HistoricalBacktestEngine


class LearningManager:
    """Central manager for all AI learning and improvement activities."""
    
    def __init__(self):
        """Initialize the learning manager."""
        self.config = Config()
        self.learning_engine = AILearningEngine()
        self.decision_logger = EnhancedDecisionLogger()
        self.backtest_engine = HistoricalBacktestEngine()
        
        # Learning schedule
        self.last_learning_cycle = None
        self.last_backtest = None
        self.learning_interval_hours = 24  # Learn daily
        self.backtest_interval_days = 7    # Backtest weekly
        
    async def start_continuous_learning(self) -> None:
        """Start the continuous learning process."""
        logger.info("Starting continuous AI learning system")
        
        while True:
            try:
                await self._run_learning_cycle()
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error in continuous learning: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _run_learning_cycle(self) -> None:
        """Run a single learning cycle."""
        current_time = datetime.now()
        
        # Check if it's time for regular learning
        if self._should_run_learning_cycle(current_time):
            await self.run_comprehensive_learning()
            self.last_learning_cycle = current_time
        
        # Check if it's time for backtesting
        if self._should_run_backtest(current_time):
            await self.run_strategy_validation()
            self.last_backtest = current_time
        
        # Generate daily insights
        if current_time.hour == 16 and current_time.minute < 5:  # After market close
            await self.generate_daily_insights()
    
    def _should_run_learning_cycle(self, current_time: datetime) -> bool:
        """Check if it's time to run a learning cycle."""
        if not self.last_learning_cycle:
            return True
        
        time_since_last = current_time - self.last_learning_cycle
        return time_since_last.total_seconds() >= (self.learning_interval_hours * 3600)
    
    def _should_run_backtest(self, current_time: datetime) -> bool:
        """Check if it's time to run backtesting."""
        if not self.last_backtest:
            return True
        
        time_since_last = current_time - self.last_backtest
        return time_since_last.days >= self.backtest_interval_days
    
    async def run_comprehensive_learning(self) -> Dict[str, Any]:
        """Run comprehensive learning across all components."""
        logger.info("Starting comprehensive learning cycle")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'learning_engine_results': None,
            'reasoning_patterns': None,
            'performance_insights': None,
            'improvement_actions': []
        }
        
        try:
            # 1. Run AI learning engine analysis
            logger.info("Running AI learning engine analysis...")
            learning_metrics = await self.learning_engine.learn_from_outcomes()
            results['learning_engine_results'] = learning_metrics
            
            # 2. Analyze reasoning patterns
            logger.info("Analyzing reasoning patterns...")
            reasoning_patterns = await self.decision_logger.get_reasoning_patterns()
            results['reasoning_patterns'] = reasoning_patterns
            
            # 3. Generate performance insights
            logger.info("Generating performance insights...")
            performance_insights = await self._generate_performance_insights(learning_metrics)
            results['performance_insights'] = performance_insights
            
            # 4. Identify improvement actions
            logger.info("Identifying improvement actions...")
            improvement_actions = await self._identify_improvement_actions(
                learning_metrics, reasoning_patterns, performance_insights
            )
            results['improvement_actions'] = improvement_actions
            
            # 5. Apply automatic improvements
            logger.info("Applying automatic improvements...")
            await self._apply_automatic_improvements(improvement_actions)
            
            # 6. Save comprehensive results
            await self._save_learning_results(results)
            
            logger.info(f"Comprehensive learning completed - {len(improvement_actions)} improvements identified")
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive learning: {e}")
            results['error'] = str(e)
            return results
    
    async def run_strategy_validation(self) -> Dict[str, Any]:
        """Run comprehensive strategy validation through backtesting."""
        logger.info("Starting strategy validation through backtesting")
        
        # Define test period (last 3 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Get learning status to create test strategies
        learning_status = self.learning_engine.get_learning_status()
        adaptive_thresholds = learning_status.get('adaptive_thresholds', {})
        
        # Create strategy configurations for testing
        test_strategies = self._create_test_strategies(adaptive_thresholds)
        
        # Get test ticker list
        test_tickers = self._get_test_ticker_list()
        
        try:
            # Run strategy comparison
            comparison_results = await self.backtest_engine.compare_strategies(
                test_strategies, start_date, end_date, test_tickers
            )
            
            # Analyze backtest results
            validation_insights = self._analyze_backtest_results(comparison_results)
            
            # Update strategy parameters based on results
            await self._update_strategy_from_backtest(comparison_results)
            
            logger.info(f"Strategy validation completed - best strategy: {comparison_results.get('best_strategy')}")
            return {
                'timestamp': datetime.now().isoformat(),
                'backtest_results': comparison_results,
                'validation_insights': validation_insights,
                'strategy_updates': True
            }
            
        except Exception as e:
            logger.error(f"Error in strategy validation: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def generate_daily_insights(self) -> Dict[str, Any]:
        """Generate daily insights and performance summary."""
        logger.info("Generating daily insights")
        
        try:
            today = datetime.now().date()
            
            # Get today's data
            learning_status = self.learning_engine.get_learning_status()
            active_decisions = self.decision_logger.get_active_decisions()
            
            # Load recent trade outcomes
            with open('data/trade_outcomes.json', 'r') as f:
                outcomes = json.load(f)
            
            # Filter today's outcomes
            today_outcomes = [
                o for o in outcomes 
                if datetime.fromisoformat(o['timestamp']).date() == today
            ]
            
            insights = {
                'date': today.isoformat(),
                'daily_summary': {
                    'total_trades': len(today_outcomes),
                    'successful_trades': len([o for o in today_outcomes if o['success']]),
                    'win_rate': len([o for o in today_outcomes if o['success']]) / len(today_outcomes) if today_outcomes else 0,
                    'total_pnl': sum(o['actual_move_percent'] for o in today_outcomes),
                    'avg_accuracy': sum(o['prediction_accuracy'] for o in today_outcomes) / len(today_outcomes) if today_outcomes else 0
                },
                'learning_progress': {
                    'total_predictions': learning_status.get('total_predictions', 0),
                    'total_outcomes': learning_status.get('total_outcomes', 0),
                    'learning_ready': learning_status.get('learning_ready', False),
                    'current_metrics': learning_status.get('current_metrics', {})
                },
                'active_decisions': len(active_decisions),
                'key_insights': [],
                'recommendations': []
            }
            
            # Generate key insights
            if today_outcomes:
                if insights['daily_summary']['win_rate'] > 0.7:
                    insights['key_insights'].append("Strong performance today - high win rate achieved")
                elif insights['daily_summary']['win_rate'] < 0.4:
                    insights['key_insights'].append("Below-average performance today - review risk management")
                
                if insights['daily_summary']['avg_accuracy'] > 80:
                    insights['key_insights'].append("High prediction accuracy - AI learning is effective")
                elif insights['daily_summary']['avg_accuracy'] < 60:
                    insights['key_insights'].append("Lower prediction accuracy - consider model adjustments")
            
            # Generate recommendations
            current_metrics = learning_status.get('current_metrics', {})
            if current_metrics.get('prediction_accuracy', 0) < 0.6:
                insights['recommendations'].append("Consider reducing position sizes due to lower accuracy")
            
            if learning_status.get('total_outcomes', 0) < 20:
                insights['recommendations'].append("Collect more trade data before making major strategy changes")
            
            if current_metrics.get('max_drawdown', 0) > 0.1:
                insights['recommendations'].append("High drawdown detected - implement stricter risk controls")
            
            # Save daily insights
            with open('data/daily_insights.json', 'w') as f:
                json.dump(insights, f, indent=2)
            
            logger.info(f"Daily insights generated: {len(insights['key_insights'])} insights, "
                       f"{len(insights['recommendations'])} recommendations")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating daily insights: {e}")
            return {'error': str(e)}
    
    async def _generate_performance_insights(self, learning_metrics) -> Dict[str, Any]:
        """Generate performance insights from learning metrics."""
        if not learning_metrics or not hasattr(learning_metrics, 'prediction_accuracy'):
            return {'error': 'No learning metrics available'}
        
        insights = {
            'overall_performance': 'good' if learning_metrics.prediction_accuracy > 0.7 else 
                                 'average' if learning_metrics.prediction_accuracy > 0.5 else 'poor',
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        # Identify strengths
        if learning_metrics.win_rate > 0.6:
            insights['strengths'].append(f"High win rate: {learning_metrics.win_rate*100:.1f}%")
        
        if learning_metrics.sharpe_ratio > 1.0:
            insights['strengths'].append(f"Good risk-adjusted returns: Sharpe {learning_metrics.sharpe_ratio:.2f}")
        
        if learning_metrics.confidence_calibration > 0.8:
            insights['strengths'].append("Well-calibrated confidence scores")
        
        # Identify weaknesses
        if learning_metrics.max_drawdown > 0.15:
            insights['weaknesses'].append(f"High drawdown: {learning_metrics.max_drawdown*100:.1f}%")
        
        if learning_metrics.avg_winner_loser_ratio < 1.5:
            insights['weaknesses'].append("Low winner/loser ratio - need better targets")
        
        if learning_metrics.prediction_accuracy < 0.6:
            insights['weaknesses'].append("Low prediction accuracy - model needs improvement")
        
        # Generate recommendations
        if learning_metrics.max_drawdown > 0.1:
            insights['recommendations'].append("Implement stricter stop losses")
        
        if learning_metrics.confidence_calibration < 0.7:
            insights['recommendations'].append("Recalibrate confidence scoring system")
        
        if learning_metrics.win_rate < 0.5:
            insights['recommendations'].append("Tighten entry criteria to improve win rate")
        
        return insights
    
    async def _identify_improvement_actions(self, learning_metrics, reasoning_patterns, 
                                          performance_insights) -> List[Dict[str, Any]]:
        """Identify specific improvement actions based on analysis."""
        actions = []
        
        # Actions based on performance
        if hasattr(learning_metrics, 'prediction_accuracy') and learning_metrics.prediction_accuracy < 0.6:
            actions.append({
                'type': 'model_adjustment',
                'action': 'reduce_confidence_multiplier',
                'reason': 'Low prediction accuracy',
                'priority': 'high',
                'auto_apply': True
            })
        
        if hasattr(learning_metrics, 'max_drawdown') and learning_metrics.max_drawdown > 0.15:
            actions.append({
                'type': 'risk_management',
                'action': 'tighten_stop_losses',
                'reason': 'High maximum drawdown',
                'priority': 'high',
                'auto_apply': True
            })
        
        # Actions based on reasoning patterns
        if reasoning_patterns and not reasoning_patterns.get('error'):
            most_reliable = reasoning_patterns.get('most_reliable_signals', {})
            
            # Increase weight for highly reliable signals
            for signal, stats in most_reliable.items():
                if stats.get('avg_accuracy', 0) > 0.8 and stats.get('sample_count', 0) >= 10:
                    actions.append({
                        'type': 'weight_adjustment',
                        'action': 'increase_signal_weight',
                        'signal': signal,
                        'reason': f'High reliability: {stats["avg_accuracy"]*100:.1f}%',
                        'priority': 'medium',
                        'auto_apply': True
                    })
        
        # Actions based on performance insights
        recommendations = performance_insights.get('recommendations', [])
        for rec in recommendations:
            if 'stop losses' in rec.lower():
                actions.append({
                    'type': 'parameter_adjustment',
                    'action': 'reduce_stop_loss_percent',
                    'reason': rec,
                    'priority': 'medium',
                    'auto_apply': True
                })
        
        return actions
    
    async def _apply_automatic_improvements(self, improvement_actions: List[Dict[str, Any]]) -> None:
        """Apply improvements that can be automatically implemented."""
        applied_count = 0
        
        for action in improvement_actions:
            if not action.get('auto_apply', False):
                continue
            
            try:
                if action['type'] == 'model_adjustment':
                    await self._apply_model_adjustment(action)
                    applied_count += 1
                    
                elif action['type'] == 'weight_adjustment':
                    await self._apply_weight_adjustment(action)
                    applied_count += 1
                    
                elif action['type'] == 'parameter_adjustment':
                    await self._apply_parameter_adjustment(action)
                    applied_count += 1
                
            except Exception as e:
                logger.error(f"Error applying improvement action {action['action']}: {e}")
        
        logger.info(f"Applied {applied_count} automatic improvements")
    
    async def _apply_model_adjustment(self, action: Dict[str, Any]) -> None:
        """Apply model adjustments."""
        if action['action'] == 'reduce_confidence_multiplier':
            # Reduce confidence multiplier by 5%
            current_weights = self.learning_engine.model_weights
            current_weights['confidence_base_multiplier'] *= 0.95
            self.learning_engine.model_weights = current_weights
            self.learning_engine._save_model_weights()
            logger.info("Reduced confidence multiplier by 5%")
    
    async def _apply_weight_adjustment(self, action: Dict[str, Any]) -> None:
        """Apply weight adjustments."""
        if action['action'] == 'increase_signal_weight':
            signal = action['signal']
            current_weights = self.learning_engine.model_weights
            
            # Map signal names to weight keys
            weight_key_map = {
                'technical_rsi': 'rsi_weight',
                'technical_vwap': 'vwap_weight',
                'technical_macd': 'macd_weight',
                'technical_volume': 'volume_weight',
                'sentiment_': 'sentiment_weight'
            }
            
            weight_key = None
            for pattern, key in weight_key_map.items():
                if pattern in signal:
                    weight_key = key
                    break
            
            if weight_key and weight_key in current_weights:
                current_weights[weight_key] = min(current_weights[weight_key] * 1.1, 2.0)  # Cap at 2.0
                self.learning_engine.model_weights = current_weights
                self.learning_engine._save_model_weights()
                logger.info(f"Increased {weight_key} by 10%")
    
    async def _apply_parameter_adjustment(self, action: Dict[str, Any]) -> None:
        """Apply parameter adjustments."""
        if action['action'] == 'reduce_stop_loss_percent':
            # This would adjust the default stop loss in the configuration
            # For now, we'll log the recommendation
            logger.info("Recommendation: Reduce default stop loss percentage")
    
    def _create_test_strategies(self, adaptive_thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Create strategy configurations for backtesting."""
        base_strategy = {
            'name': 'Current_AI_Strategy',
            'min_confidence': adaptive_thresholds.get('min_confidence_score', 7.0),
            'rsi_oversold': adaptive_thresholds.get('rsi_oversold', 30),
            'rsi_overbought': adaptive_thresholds.get('rsi_overbought', 70),
            'volume_spike_threshold': adaptive_thresholds.get('volume_spike_multiplier', 2.0),
            'min_signals_required': 2
        }
        
        # Create variations for testing
        conservative_strategy = base_strategy.copy()
        conservative_strategy.update({
            'name': 'Conservative_Strategy',
            'min_confidence': base_strategy['min_confidence'] + 0.5,
            'min_signals_required': 3
        })
        
        aggressive_strategy = base_strategy.copy()
        aggressive_strategy.update({
            'name': 'Aggressive_Strategy',
            'min_confidence': max(base_strategy['min_confidence'] - 0.5, 6.0),
            'min_signals_required': 1
        })
        
        return [base_strategy, conservative_strategy, aggressive_strategy]
    
    def _get_test_ticker_list(self) -> List[str]:
        """Get list of tickers for backtesting."""
        # Return a focused list of liquid tickers for testing
        return ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'SHOP']
    
    def _analyze_backtest_results(self, comparison_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze backtest results for insights."""
        insights = {
            'best_performing_strategy': comparison_results.get('best_strategy'),
            'performance_differences': {},
            'optimization_opportunities': [],
            'risk_assessment': {}
        }
        
        # Analyze performance differences
        rankings = comparison_results.get('strategy_rankings', [])
        if len(rankings) >= 2:
            best = rankings[0]
            worst = rankings[-1]
            
            insights['performance_differences'] = {
                'return_difference': best['total_return'] - worst['total_return'],
                'win_rate_difference': best['win_rate'] - worst['win_rate'],
                'sharpe_difference': best['sharpe_ratio'] - worst['sharpe_ratio']
            }
        
        # Identify optimization opportunities
        for ranking in rankings:
            if ranking['win_rate'] < 0.5:
                insights['optimization_opportunities'].append(
                    f"{ranking['strategy_name']}: Improve win rate ({ranking['win_rate']*100:.1f}%)"
                )
            
            if ranking['max_drawdown'] > 0.15:
                insights['optimization_opportunities'].append(
                    f"{ranking['strategy_name']}: Reduce drawdown ({ranking['max_drawdown']*100:.1f}%)"
                )
        
        return insights
    
    async def _update_strategy_from_backtest(self, comparison_results: Dict[str, Any]) -> None:
        """Update strategy parameters based on backtest results."""
        best_strategy = comparison_results.get('best_strategy')
        
        if best_strategy and best_strategy != 'Current_AI_Strategy':
            logger.info(f"Updating strategy parameters based on {best_strategy} performance")
            
            # Get the best strategy's configuration
            detailed_results = comparison_results.get('detailed_results', {})
            best_config = detailed_results.get(best_strategy, {}).get('config', {})
            
            # Update adaptive thresholds in learning engine
            if best_config:
                # This would update the configuration
                # For now, we'll log the recommended changes
                logger.info(f"Recommended strategy update: {best_config}")
    
    async def _save_learning_results(self, results: Dict[str, Any]) -> None:
        """Save comprehensive learning results."""
        try:
            # Convert learning metrics to dict if needed
            if hasattr(results.get('learning_engine_results'), '__dict__'):
                results['learning_engine_results'] = results['learning_engine_results'].__dict__
            
            with open('data/learning_results.json', 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info("Learning results saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving learning results: {e}")
    
    def get_learning_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive learning status summary."""
        try:
            learning_status = self.learning_engine.get_learning_status()
            active_decisions = self.decision_logger.get_active_decisions()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'learning_engine': learning_status,
                'active_decisions': len(active_decisions),
                'last_learning_cycle': self.last_learning_cycle.isoformat() if self.last_learning_cycle else None,
                'last_backtest': self.last_backtest.isoformat() if self.last_backtest else None,
                'next_learning_cycle': self._get_next_learning_time().isoformat(),
                'next_backtest': self._get_next_backtest_time().isoformat(),
                'system_health': self._assess_system_health(learning_status)
            }
            
        except Exception as e:
            logger.error(f"Error getting learning status: {e}")
            return {'error': str(e)}
    
    def _get_next_learning_time(self) -> datetime:
        """Get next scheduled learning cycle time."""
        if self.last_learning_cycle:
            return self.last_learning_cycle + timedelta(hours=self.learning_interval_hours)
        else:
            return datetime.now() + timedelta(hours=1)
    
    def _get_next_backtest_time(self) -> datetime:
        """Get next scheduled backtest time."""
        if self.last_backtest:
            return self.last_backtest + timedelta(days=self.backtest_interval_days)
        else:
            return datetime.now() + timedelta(hours=2)
    
    def _assess_system_health(self, learning_status: Dict[str, Any]) -> str:
        """Assess overall system health."""
        if not learning_status.get('learning_ready', False):
            return 'initializing'
        
        current_metrics = learning_status.get('current_metrics', {})
        
        if not current_metrics:
            return 'no_data'
        
        accuracy = current_metrics.get('prediction_accuracy', 0)
        win_rate = current_metrics.get('win_rate', 0)
        
        if accuracy > 0.7 and win_rate > 0.6:
            return 'excellent'
        elif accuracy > 0.6 and win_rate > 0.5:
            return 'good'
        elif accuracy > 0.5 and win_rate > 0.4:
            return 'average'
        else:
            return 'needs_attention'
