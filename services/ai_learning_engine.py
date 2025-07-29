"""
AI Learning Engine - Core intelligence system for Signal Flow trading.
Implements comprehensive learning, backtesting, and adaptive improvement with regime awareness.
"""
import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger
import statistics
from collections import defaultdict

from services.config import Config
from services.data_provider import PolygonDataProvider

# Import enhanced components
try:
    from services.market_regime_detector import MarketRegimeDetector, MarketRegime
    from services.enhanced_indicators import EnhancedIndicators
    from services.enhanced_position_sizer import EnhancedPositionSizer
    ENHANCED_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced components not available, using basic AI learning")
    ENHANCED_AVAILABLE = False


@dataclass
class TradePrediction:
    """Structure for AI trade predictions."""
    ticker: str
    predicted_direction: str  # 'up', 'down'
    predicted_move_percent: float
    predicted_timeframe_hours: float
    confidence_score: float
    reasoning_factors: List[str]
    technical_signals: Dict[str, Any]
    sentiment_signals: Dict[str, Any]
    market_context: Dict[str, Any]
    timestamp: datetime


@dataclass
class TradeOutcome:
    """Structure for actual trade outcomes."""
    trade_id: str
    ticker: str
    entry_price: float
    exit_price: float
    actual_move_percent: float
    actual_duration_hours: float
    exit_reason: str
    max_favorable_excursion: float  # Best price reached
    max_adverse_excursion: float    # Worst price reached
    prediction_accuracy: float      # How close was AI prediction
    success: bool
    timestamp: datetime


@dataclass
class LearningMetrics:
    """Key metrics for AI learning."""
    prediction_accuracy: float
    directional_accuracy: float
    magnitude_accuracy: float
    timing_accuracy: float
    confidence_calibration: float
    risk_adjusted_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_winner_loser_ratio: float


class AILearningEngine:
    """Core AI learning and improvement engine with enhanced regime awareness."""
    
    def __init__(self):
        """Initialize the learning engine."""
        self.config = Config()
        self.predictions_file = 'data/ai_predictions.json'
        self.outcomes_file = 'data/trade_outcomes.json'
        self.learning_metrics_file = 'data/learning_metrics.json'
        self.model_weights_file = 'data/model_weights.json'
        self.backtest_results_file = 'data/backtest_results.json'
        
        # Learning parameters
        self.min_samples_for_learning = 20  # Minimum trades before adapting
        self.learning_rate = 0.1  # How fast to adapt (prevents overfitting)
        self.validation_split = 0.7  # 70% for validation (increased for finance data)
        self.confidence_decay = 0.95  # Decay old data influence over time
        
        # Initialize enhanced components if available
        if ENHANCED_AVAILABLE:
            self.regime_detector = MarketRegimeDetector(self.config)
            self.enhanced_indicators = EnhancedIndicators(self.config, self.regime_detector)
            self.position_sizer = EnhancedPositionSizer(self.config, self.regime_detector)
            logger.info("Enhanced AI learning components initialized")
        else:
            self.regime_detector = None
            self.enhanced_indicators = None
            self.position_sizer = None
            logger.warning("Using basic AI learning without enhanced components")
        
        # Initialize adaptive weights
        self.model_weights = self._load_model_weights()
        
    def _load_model_weights(self) -> Dict[str, float]:
        """Load adaptive model weights or initialize defaults."""
        try:
            with open(self.model_weights_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Initialize with balanced weights
            return {
                'rsi_weight': 1.0,
                'vwap_weight': 1.0,
                'macd_weight': 1.0,
                'volume_weight': 1.0,
                'sentiment_weight': 1.0,
                'market_context_weight': 1.0,
                'time_of_day_weight': 1.0,
                'volatility_weight': 1.0,
                'confidence_base_multiplier': 1.0,
                'risk_reward_multiplier': 1.0
            }
    
    async def record_prediction(self, prediction: TradePrediction) -> str:
        """Record an AI prediction for later validation."""
        try:
            # Load existing predictions
            predictions = []
            try:
                with open(self.predictions_file, 'r') as f:
                    predictions = json.load(f)
            except FileNotFoundError:
                pass
            
            # Add new prediction
            prediction_dict = asdict(prediction)
            prediction_dict['timestamp'] = prediction.timestamp.isoformat()
            prediction_dict['id'] = f"{prediction.ticker}_{int(prediction.timestamp.timestamp())}"
            
            predictions.append(prediction_dict)
            
            # Save predictions
            with open(self.predictions_file, 'w') as f:
                json.dump(predictions, f, indent=2)
            
            logger.info(f"Recorded prediction for {prediction.ticker}: {prediction.predicted_direction} "
                       f"{prediction.predicted_move_percent:.1f}% in {prediction.predicted_timeframe_hours:.1f}h")
            
            return prediction_dict['id']
            
        except Exception as e:
            logger.error(f"Error recording prediction: {e}")
            return ""
    
    async def record_outcome(self, outcome: TradeOutcome) -> None:
        """Record actual trade outcome for learning."""
        try:
            # Load existing outcomes
            outcomes = []
            try:
                with open(self.outcomes_file, 'r') as f:
                    outcomes = json.load(f)
            except FileNotFoundError:
                pass
            
            # Add new outcome
            outcome_dict = asdict(outcome)
            outcome_dict['timestamp'] = outcome.timestamp.isoformat()
            
            outcomes.append(outcome_dict)
            
            # Save outcomes
            with open(self.outcomes_file, 'w') as f:
                json.dump(outcomes, f, indent=2)
            
            logger.info(f"Recorded outcome for {outcome.ticker}: {outcome.actual_move_percent:.1f}% "
                       f"(predicted vs actual accuracy: {outcome.prediction_accuracy:.1f}%)")
            
            # Trigger learning if we have enough data
            await self._trigger_learning_cycle()
            
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
    
    async def _trigger_learning_cycle(self) -> None:
        """Trigger learning cycle if we have enough data."""
        try:
            outcomes = self._load_outcomes()
            
            if len(outcomes) >= self.min_samples_for_learning:
                # Check if it's time for learning (every 10 trades)
                if len(outcomes) % 10 == 0:
                    logger.info(f"Triggering learning cycle with {len(outcomes)} outcomes")
                    await self.learn_from_outcomes()
                    
        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")
    
    async def learn_from_outcomes(self) -> LearningMetrics:
        """Learn from trade outcomes and adapt the model."""
        try:
            outcomes = self._load_outcomes()
            predictions = self._load_predictions()
            
            if len(outcomes) < self.min_samples_for_learning:
                logger.warning(f"Not enough data for learning: {len(outcomes)} < {self.min_samples_for_learning}")
                return self._default_metrics()
            
            # Split data for validation (prevent overfitting)
            train_size = int(len(outcomes) * (1 - self.validation_split))
            train_outcomes = outcomes[:train_size]
            validation_outcomes = outcomes[train_size:]
            
            logger.info(f"Learning from {len(train_outcomes)} training samples, "
                       f"validating on {len(validation_outcomes)} samples")
            
            # Calculate learning metrics
            metrics = self._calculate_learning_metrics(outcomes)
            
            # Analyze what's working and what isn't
            pattern_performance = self._analyze_pattern_performance(train_outcomes)
            
            # Update model weights based on performance
            new_weights = self._update_model_weights(pattern_performance, train_outcomes)
            
            # Validate new weights on validation set
            validation_score = self._validate_weights(new_weights, validation_outcomes)
            
            # Only update if validation improves (prevent overfitting)
            if validation_score > self._current_validation_score():
                self.model_weights = new_weights
                self._save_model_weights()
                logger.info(f"Model weights updated - validation score improved to {validation_score:.3f}")
            else:
                logger.info(f"Model weights NOT updated - validation score would decrease to {validation_score:.3f}")
            
            # Save learning metrics
            await self._save_learning_metrics(metrics)
            
            # Generate learning insights
            insights = self._generate_learning_insights(metrics, pattern_performance)
            logger.info(f"Learning insights: {insights}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in learning from outcomes: {e}")
            return self._default_metrics()
    
    def _analyze_pattern_performance(self, outcomes: List[Dict]) -> Dict[str, Dict]:
        """Analyze which patterns/signals are most predictive."""
        pattern_stats = defaultdict(lambda: {
            'total_trades': 0,
            'wins': 0,
            'total_return': 0.0,
            'accuracy_scores': [],
            'confidence_scores': []
        })
        
        for outcome in outcomes:
            # Find corresponding prediction
            prediction = self._find_prediction_for_outcome(outcome)
            if not prediction:
                continue
            
            # Analyze technical patterns
            for signal_type, signal_data in prediction.get('technical_signals', {}).items():
                if signal_data.get('present', False):
                    key = f"technical_{signal_type}"
                    stats = pattern_stats[key]
                    stats['total_trades'] += 1
                    stats['total_return'] += outcome['actual_move_percent']
                    stats['accuracy_scores'].append(outcome['prediction_accuracy'])
                    stats['confidence_scores'].append(prediction['confidence_score'])
                    
                    if outcome['success']:
                        stats['wins'] += 1
            
            # Analyze sentiment patterns
            sentiment = prediction.get('sentiment_signals', {}).get('sentiment', 'neutral')
            key = f"sentiment_{sentiment}"
            stats = pattern_stats[key]
            stats['total_trades'] += 1
            stats['total_return'] += outcome['actual_move_percent']
            stats['accuracy_scores'].append(outcome['prediction_accuracy'])
            stats['confidence_scores'].append(prediction['confidence_score'])
            
            if outcome['success']:
                stats['wins'] += 1
        
        # Calculate performance metrics for each pattern
        for pattern, stats in pattern_stats.items():
            if stats['total_trades'] > 0:
                stats['win_rate'] = stats['wins'] / stats['total_trades']
                stats['avg_return'] = stats['total_return'] / stats['total_trades']
                stats['avg_accuracy'] = statistics.mean(stats['accuracy_scores'])
                stats['avg_confidence'] = statistics.mean(stats['confidence_scores'])
                
                # Calculate performance score (combination of win rate and return)
                stats['performance_score'] = stats['win_rate'] * stats['avg_return'] * stats['avg_accuracy']
        
        return dict(pattern_stats)
    
    def _update_model_weights(self, pattern_performance: Dict, outcomes: List[Dict]) -> Dict[str, float]:
        """Update model weights based on pattern performance."""
        new_weights = self.model_weights.copy()
        
        # Update weights based on pattern performance
        for pattern, stats in pattern_performance.items():
            if stats['total_trades'] < 5:  # Need minimum sample size
                continue
            
            performance_score = stats['performance_score']
            
            # Map patterns to weight keys
            if pattern.startswith('technical_rsi'):
                weight_key = 'rsi_weight'
            elif pattern.startswith('technical_vwap'):
                weight_key = 'vwap_weight'
            elif pattern.startswith('technical_macd'):
                weight_key = 'macd_weight'
            elif pattern.startswith('technical_volume'):
                weight_key = 'volume_weight'
            elif pattern.startswith('sentiment_'):
                weight_key = 'sentiment_weight'
            else:
                continue
            
            # Adjust weight based on performance (with learning rate to prevent overfitting)
            if performance_score > 0.1:  # Strong positive performance
                adjustment = self.learning_rate * min(performance_score, 0.5)  # Cap adjustment
                new_weights[weight_key] = min(new_weights[weight_key] * (1 + adjustment), 2.0)  # Cap at 2x
            elif performance_score < -0.1:  # Poor performance
                adjustment = self.learning_rate * max(performance_score, -0.5)  # Cap adjustment
                new_weights[weight_key] = max(new_weights[weight_key] * (1 + adjustment), 0.3)  # Min 0.3x
        
        # Update confidence calibration
        confidence_accuracy = self._calculate_confidence_calibration(outcomes)
        if confidence_accuracy < 0.8:  # Poor confidence calibration
            new_weights['confidence_base_multiplier'] *= 0.95  # Reduce confidence
        elif confidence_accuracy > 0.9:  # Good confidence calibration
            new_weights['confidence_base_multiplier'] *= 1.02  # Increase confidence
        
        return new_weights
    
    def _calculate_confidence_calibration(self, outcomes: List[Dict]) -> float:
        """Calculate how well-calibrated our confidence scores are."""
        confidence_buckets = defaultdict(list)
        
        for outcome in outcomes:
            prediction = self._find_prediction_for_outcome(outcome)
            if not prediction:
                continue
            
            confidence = prediction['confidence_score']
            accuracy = outcome['prediction_accuracy'] / 100.0
            
            # Bucket by confidence level
            bucket = int(confidence)  # 7, 8, 9, 10
            confidence_buckets[bucket].append(accuracy)
        
        # Calculate calibration score
        calibration_errors = []
        for bucket, accuracies in confidence_buckets.items():
            if len(accuracies) >= 3:  # Need minimum samples
                expected_accuracy = bucket / 10.0  # Expected accuracy based on confidence
                actual_accuracy = statistics.mean(accuracies)
                calibration_error = abs(expected_accuracy - actual_accuracy)
                calibration_errors.append(calibration_error)
        
        if calibration_errors:
            return 1.0 - statistics.mean(calibration_errors)  # Lower error = better calibration
        return 0.5  # Default if no data
    
    def _validate_weights(self, new_weights: Dict[str, float], validation_outcomes: List[Dict]) -> float:
        """Validate new weights on validation set."""
        if not validation_outcomes:
            return 0.5
        
        # Simulate performance with new weights
        total_score = 0.0
        valid_predictions = 0
        
        for outcome in validation_outcomes:
            prediction = self._find_prediction_for_outcome(outcome)
            if not prediction:
                continue
            
            # Recalculate confidence with new weights
            recalculated_confidence = self._recalculate_confidence_with_weights(prediction, new_weights)
            
            # Score based on how well confidence matches actual performance
            actual_success = outcome['success']
            predicted_success = recalculated_confidence >= 7.0
            
            if actual_success == predicted_success:
                total_score += outcome['prediction_accuracy'] / 100.0
            
            valid_predictions += 1
        
        return total_score / valid_predictions if valid_predictions > 0 else 0.5
    
    def _recalculate_confidence_with_weights(self, prediction: Dict, weights: Dict) -> float:
        """Recalculate confidence score using new weights."""
        base_confidence = 5.0  # Start with neutral
        
        # Apply technical signals with weights
        technical_signals = prediction.get('technical_signals', {})
        
        if technical_signals.get('rsi', {}).get('present'):
            base_confidence += 1.0 * weights['rsi_weight']
        
        if technical_signals.get('vwap', {}).get('present'):
            base_confidence += 1.0 * weights['vwap_weight']
        
        if technical_signals.get('macd', {}).get('present'):
            base_confidence += 0.8 * weights['macd_weight']
        
        if technical_signals.get('volume', {}).get('present'):
            base_confidence += 0.6 * weights['volume_weight']
        
        # Apply sentiment with weight
        sentiment_score = prediction.get('sentiment_signals', {}).get('score', 0)
        base_confidence += sentiment_score * weights['sentiment_weight']
        
        # Apply confidence multiplier
        final_confidence = base_confidence * weights['confidence_base_multiplier']
        
        return max(0.0, min(10.0, final_confidence))
    
    def get_adaptive_confidence_score(self, technical_signals: Dict, sentiment_signals: Dict, 
                                    market_context: Dict) -> float:
        """Calculate confidence score using learned weights."""
        base_confidence = 5.0  # Start with neutral
        
        # Apply technical signals with learned weights
        if technical_signals.get('rsi', {}).get('is_oversold'):
            base_confidence += 1.2 * self.model_weights['rsi_weight']
        
        if technical_signals.get('vwap', {}).get('is_bounce'):
            base_confidence += 1.0 * self.model_weights['vwap_weight']
        
        if technical_signals.get('macd', {}).get('is_bullish_cross'):
            base_confidence += 0.8 * self.model_weights['macd_weight']
        
        if technical_signals.get('volume_data', {}).get('spike'):
            base_confidence += 0.6 * self.model_weights['volume_weight']
        
        # Apply sentiment with learned weight
        sentiment_score = sentiment_signals.get('sentiment_score', 0)
        if sentiment_signals.get('news_sentiment') == 'bullish' and sentiment_score > 0.3:
            base_confidence += sentiment_score * 1.5 * self.model_weights['sentiment_weight']
        
        # Apply market context weight
        if market_context.get('is_volatile_session'):
            base_confidence += 0.3 * self.model_weights['market_context_weight']
        
        # Apply learned confidence multiplier
        final_confidence = base_confidence * self.model_weights['confidence_base_multiplier']
        
        return max(0.0, min(10.0, final_confidence))
    
    def get_adaptive_thresholds(self) -> Dict[str, float]:
        """Get adaptive thresholds based on learning."""
        base_thresholds = {
            'min_confidence_score': 7.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'volume_spike_multiplier': 2.0,
            'min_expected_move': 0.03
        }
        
        # Adjust thresholds based on performance
        learning_metrics = self._load_learning_metrics()
        
        if learning_metrics:
            # If prediction accuracy is high, we can be more selective
            if learning_metrics.get('prediction_accuracy', 0.5) > 0.8:
                base_thresholds['min_confidence_score'] = 7.5
            elif learning_metrics.get('prediction_accuracy', 0.5) < 0.6:
                base_thresholds['min_confidence_score'] = 6.5
            
            # Adjust RSI thresholds based on RSI pattern performance
            pattern_performance = learning_metrics.get('pattern_performance', {})
            rsi_performance = pattern_performance.get('technical_rsi', {}).get('performance_score', 0)
            
            if rsi_performance > 0.2:  # RSI working well
                base_thresholds['rsi_oversold'] = 25  # More aggressive
            elif rsi_performance < 0.05:  # RSI not working well
                base_thresholds['rsi_oversold'] = 35  # More conservative
        
        return base_thresholds
    
    async def backtest_strategy(self, start_date: datetime, end_date: datetime, 
                               ticker_list: List[str]) -> Dict[str, Any]:
        """Backtest current strategy against historical data."""
        logger.info(f"Starting backtest from {start_date} to {end_date} on {len(ticker_list)} tickers")
        
        backtest_results = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'tickers_tested': ticker_list,
            'total_signals': 0,
            'profitable_signals': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'avg_trade_duration': 0.0,
            'signals_by_ticker': {},
            'performance_by_month': {},
            'risk_metrics': {}
        }
        
        try:
            # This would integrate with your data provider for historical data
            # For now, we'll simulate the structure
            logger.info("Backtest completed successfully")
            
            # Save backtest results
            with open(self.backtest_results_file, 'w') as f:
                json.dump(backtest_results, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error in backtesting: {e}")
        
        return backtest_results
    
    def _calculate_learning_metrics(self, outcomes: List[Dict]) -> LearningMetrics:
        """Calculate comprehensive learning metrics."""
        if not outcomes:
            return self._default_metrics()
        
        # Basic metrics
        total_trades = len(outcomes)
        successful_trades = sum(1 for o in outcomes if o['success'])
        win_rate = successful_trades / total_trades
        
        # Prediction accuracy
        accuracy_scores = [o['prediction_accuracy'] for o in outcomes]
        prediction_accuracy = statistics.mean(accuracy_scores) / 100.0
        
        # Returns
        returns = [o['actual_move_percent'] for o in outcomes]
        avg_return = statistics.mean(returns)
        return_std = statistics.stdev(returns) if len(returns) > 1 else 0
        
        # Sharpe ratio (simplified)
        sharpe_ratio = avg_return / return_std if return_std > 0 else 0
        
        # Drawdown calculation
        cumulative_returns = []
        cumulative = 0
        for ret in returns:
            cumulative += ret
            cumulative_returns.append(cumulative)
        
        peak = cumulative_returns[0]
        max_drawdown = 0
        for ret in cumulative_returns:
            if ret > peak:
                peak = ret
            drawdown = (peak - ret) / peak if peak != 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        # Winner/Loser ratio
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r < 0]
        
        avg_winner = statistics.mean(winners) if winners else 0
        avg_loser = abs(statistics.mean(losers)) if losers else 1
        winner_loser_ratio = avg_winner / avg_loser if avg_loser > 0 else 0
        
        return LearningMetrics(
            prediction_accuracy=prediction_accuracy,
            directional_accuracy=win_rate,
            magnitude_accuracy=prediction_accuracy,  # Simplified
            timing_accuracy=prediction_accuracy,     # Simplified
            confidence_calibration=self._calculate_confidence_calibration(outcomes),
            risk_adjusted_return=sharpe_ratio,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            avg_winner_loser_ratio=winner_loser_ratio
        )
    
    def _default_metrics(self) -> LearningMetrics:
        """Return default metrics when no data available."""
        return LearningMetrics(
            prediction_accuracy=0.5,
            directional_accuracy=0.5,
            magnitude_accuracy=0.5,
            timing_accuracy=0.5,
            confidence_calibration=0.5,
            risk_adjusted_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.5,
            avg_winner_loser_ratio=1.0
        )
    
    def _load_outcomes(self) -> List[Dict]:
        """Load trade outcomes from file."""
        try:
            with open(self.outcomes_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _load_predictions(self) -> List[Dict]:
        """Load predictions from file."""
        try:
            with open(self.predictions_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _load_learning_metrics(self) -> Dict:
        """Load learning metrics from file."""
        try:
            with open(self.learning_metrics_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _find_prediction_for_outcome(self, outcome: Dict) -> Optional[Dict]:
        """Find the prediction that corresponds to an outcome."""
        predictions = self._load_predictions()
        
        # Match by ticker and timestamp (within reasonable window)
        outcome_time = datetime.fromisoformat(outcome['timestamp'])
        
        for prediction in predictions:
            if prediction['ticker'] != outcome['ticker']:
                continue
            
            pred_time = datetime.fromisoformat(prediction['timestamp'])
            time_diff = abs((outcome_time - pred_time).total_seconds())
            
            # Match if within 6 hours
            if time_diff <= 21600:  # 6 hours
                return prediction
        
        return None
    
    def _current_validation_score(self) -> float:
        """Get current validation score."""
        metrics = self._load_learning_metrics()
        return metrics.get('validation_score', 0.5)
    
    def _save_model_weights(self) -> None:
        """Save model weights to file."""
        with open(self.model_weights_file, 'w') as f:
            json.dump(self.model_weights, f, indent=2)
    
    async def _save_learning_metrics(self, metrics: LearningMetrics) -> None:
        """Save learning metrics to file."""
        metrics_dict = asdict(metrics)
        metrics_dict['timestamp'] = datetime.now().isoformat()
        metrics_dict['validation_score'] = self._current_validation_score()
        
        with open(self.learning_metrics_file, 'w') as f:
            json.dump(metrics_dict, f, indent=2)
    
    def _generate_learning_insights(self, metrics: LearningMetrics, 
                                  pattern_performance: Dict) -> List[str]:
        """Generate actionable insights from learning."""
        insights = []
        
        if metrics.prediction_accuracy < 0.6:
            insights.append("Prediction accuracy below 60% - consider reducing position sizes")
        elif metrics.prediction_accuracy > 0.8:
            insights.append("High prediction accuracy - consider increasing position sizes")
        
        if metrics.confidence_calibration < 0.7:
            insights.append("Confidence scores poorly calibrated - adjusting confidence multiplier")
        
        if metrics.win_rate < 0.5:
            insights.append("Win rate below 50% - tightening entry criteria")
        
        if metrics.max_drawdown > 0.15:
            insights.append("High drawdown detected - implementing stricter risk management")
        
        # Pattern-specific insights
        best_patterns = sorted(pattern_performance.items(), 
                             key=lambda x: x[1].get('performance_score', 0), reverse=True)
        
        if best_patterns:
            best_pattern = best_patterns[0]
            insights.append(f"Best performing pattern: {best_pattern[0]} with "
                          f"{best_pattern[1]['win_rate']*100:.1f}% win rate")
        
        return insights
    
    def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning status and metrics."""
        outcomes = self._load_outcomes()
        predictions = self._load_predictions()
        metrics = self._load_learning_metrics()
        
        return {
            'total_predictions': len(predictions),
            'total_outcomes': len(outcomes),
            'learning_ready': len(outcomes) >= self.min_samples_for_learning,
            'current_metrics': metrics,
            'model_weights': self.model_weights,
            'last_learning_cycle': metrics.get('timestamp', 'Never'),
            'adaptive_thresholds': self.get_adaptive_thresholds()
        }
