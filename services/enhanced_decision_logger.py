"""
Enhanced Decision Logger - Captures detailed AI reasoning for learning.
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger

from services.config import Config


@dataclass
class DecisionContext:
    """Context information for a trading decision."""
    ticker: str
    market_data: Dict[str, Any]
    technical_indicators: Dict[str, Any]
    sentiment_data: Dict[str, Any]
    market_conditions: Dict[str, Any]
    time_context: Dict[str, Any]
    portfolio_context: Dict[str, Any]


@dataclass
class AIReasoning:
    """Detailed AI reasoning process."""
    decision_id: str
    timestamp: datetime
    context: DecisionContext
    reasoning_steps: List[Dict[str, Any]]
    confidence_breakdown: Dict[str, float]
    risk_assessment: Dict[str, Any]
    final_decision: str  # 'buy', 'sell', 'hold', 'exit'
    confidence_score: float
    expected_outcome: Dict[str, Any]
    alternatives_considered: List[Dict[str, Any]]
    key_factors: List[str]
    risk_factors: List[str]


@dataclass
class DecisionOutcome:
    """Actual outcome vs AI expectations."""
    decision_id: str
    actual_outcome: Dict[str, Any]
    expectation_vs_reality: Dict[str, Any]
    accuracy_metrics: Dict[str, float]
    lessons_learned: List[str]
    timestamp: datetime


class EnhancedDecisionLogger:
    """Comprehensive decision logging for AI learning."""
    
    def __init__(self):
        """Initialize the enhanced decision logger."""
        self.config = Config()
        self.decisions_file = 'data/ai_decisions.json'
        self.decision_outcomes_file = 'data/decision_outcomes.json'
        self.reasoning_patterns_file = 'data/reasoning_patterns.json'
        
        # Active decisions tracking
        self.active_decisions: Dict[str, AIReasoning] = {}
        
    async def start_decision_logging(self, ticker: str, context: DecisionContext) -> str:
        """Start logging a new trading decision."""
        decision_id = f"{ticker}_{int(datetime.now().timestamp())}"
        
        # Initialize AI reasoning structure
        reasoning = AIReasoning(
            decision_id=decision_id,
            timestamp=datetime.now(),
            context=context,
            reasoning_steps=[],
            confidence_breakdown={},
            risk_assessment={},
            final_decision='pending',
            confidence_score=0.0,
            expected_outcome={},
            alternatives_considered=[],
            key_factors=[],
            risk_factors=[]
        )
        
        self.active_decisions[decision_id] = reasoning
        
        logger.info(f"Started decision logging for {ticker} - ID: {decision_id}")
        return decision_id
    
    async def log_reasoning_step(self, decision_id: str, step_type: str, 
                                step_data: Dict[str, Any], confidence_impact: float = 0.0) -> None:
        """Log a single reasoning step in the AI decision process."""
        if decision_id not in self.active_decisions:
            logger.warning(f"Decision ID {decision_id} not found in active decisions")
            return
        
        reasoning = self.active_decisions[decision_id]
        
        step = {
            'step_number': len(reasoning.reasoning_steps) + 1,
            'step_type': step_type,
            'timestamp': datetime.now().isoformat(),
            'data': step_data,
            'confidence_impact': confidence_impact,
            'reasoning': step_data.get('reasoning', '')
        }
        
        reasoning.reasoning_steps.append(step)
        
        # Update confidence breakdown
        if step_type not in reasoning.confidence_breakdown:
            reasoning.confidence_breakdown[step_type] = 0.0
        reasoning.confidence_breakdown[step_type] += confidence_impact
        
        logger.debug(f"Logged reasoning step for {decision_id}: {step_type} "
                    f"(confidence impact: {confidence_impact:+.2f})")
    
    async def log_technical_analysis(self, decision_id: str, 
                                   technical_data: Dict[str, Any]) -> None:
        """Log technical analysis reasoning."""
        rsi_data = technical_data.get('rsi', {})
        if rsi_data.get('present'):
            await self.log_reasoning_step(
                decision_id, 
                'technical_rsi',
                {
                    'rsi_value': rsi_data.get('value'),
                    'is_oversold': rsi_data.get('is_oversold'),
                    'is_overbought': rsi_data.get('is_overbought'),
                    'reasoning': f"RSI at {rsi_data.get('value'):.1f} - "
                               f"{'oversold' if rsi_data.get('is_oversold') else 'normal'} conditions"
                },
                1.2 if rsi_data.get('is_oversold') else -0.5 if rsi_data.get('is_overbought') else 0.0
            )
        
        vwap_data = technical_data.get('vwap', {})
        if vwap_data.get('present'):
            await self.log_reasoning_step(
                decision_id,
                'technical_vwap',
                {
                    'price_vs_vwap': vwap_data.get('price_vs_vwap'),
                    'is_bounce': vwap_data.get('is_bounce'),
                    'reasoning': f"Price {'above' if vwap_data.get('price_vs_vwap', 0) > 0 else 'below'} VWAP"
                },
                1.0 if vwap_data.get('is_bounce') else 0.0
            )
        
        macd_data = technical_data.get('macd', {})
        if macd_data.get('present'):
            await self.log_reasoning_step(
                decision_id,
                'technical_macd',
                {
                    'macd_value': macd_data.get('macd'),
                    'signal_value': macd_data.get('signal'),
                    'is_bullish_cross': macd_data.get('is_bullish_cross'),
                    'reasoning': f"MACD {'bullish crossover' if macd_data.get('is_bullish_cross') else 'neutral'}"
                },
                0.8 if macd_data.get('is_bullish_cross') else 0.0
            )
        
        volume_data = technical_data.get('volume_data', {})
        if volume_data.get('spike'):
            await self.log_reasoning_step(
                decision_id,
                'technical_volume',
                {
                    'volume_ratio': volume_data.get('volume_ratio'),
                    'avg_volume': volume_data.get('avg_volume'),
                    'current_volume': volume_data.get('current_volume'),
                    'reasoning': f"Volume spike detected: {volume_data.get('volume_ratio', 0):.1f}x average"
                },
                0.6
            )
    
    async def log_sentiment_analysis(self, decision_id: str, 
                                   sentiment_data: Dict[str, Any]) -> None:
        """Log sentiment analysis reasoning."""
        sentiment_score = sentiment_data.get('sentiment_score', 0)
        news_sentiment = sentiment_data.get('news_sentiment', 'neutral')
        
        confidence_impact = 0.0
        if news_sentiment == 'bullish' and sentiment_score > 0.3:
            confidence_impact = sentiment_score * 1.5
        elif news_sentiment == 'bearish' and sentiment_score < -0.3:
            confidence_impact = abs(sentiment_score) * -1.5
        
        await self.log_reasoning_step(
            decision_id,
            'sentiment_analysis',
            {
                'sentiment_score': sentiment_score,
                'news_sentiment': news_sentiment,
                'news_count': sentiment_data.get('news_count', 0),
                'social_sentiment': sentiment_data.get('social_sentiment', {}),
                'reasoning': f"Market sentiment: {news_sentiment} (score: {sentiment_score:.2f})"
            },
            confidence_impact
        )
    
    async def log_risk_assessment(self, decision_id: str, 
                                risk_data: Dict[str, Any]) -> None:
        """Log risk assessment reasoning."""
        if decision_id not in self.active_decisions:
            return
        
        reasoning = self.active_decisions[decision_id]
        reasoning.risk_assessment = risk_data
        
        # Log specific risk factors
        for risk_factor, risk_value in risk_data.items():
            if risk_factor == 'portfolio_risk':
                await self.log_reasoning_step(
                    decision_id,
                    'risk_portfolio',
                    {
                        'current_exposure': risk_value.get('current_exposure'),
                        'max_exposure': risk_value.get('max_exposure'),
                        'reasoning': f"Portfolio exposure: {risk_value.get('current_exposure', 0)*100:.1f}%"
                    },
                    -0.5 if risk_value.get('current_exposure', 0) > 0.8 else 0.0
                )
            
            elif risk_factor == 'volatility_risk':
                await self.log_reasoning_step(
                    decision_id,
                    'risk_volatility',
                    {
                        'current_volatility': risk_value.get('current_volatility'),
                        'historical_volatility': risk_value.get('historical_volatility'),
                        'reasoning': f"Volatility assessment: {risk_value.get('assessment', 'normal')}"
                    },
                    -0.3 if risk_value.get('assessment') == 'high' else 0.1
                )
    
    async def log_market_context(self, decision_id: str, 
                               market_data: Dict[str, Any]) -> None:
        """Log market context reasoning."""
        market_trend = market_data.get('market_trend', 'neutral')
        vix_level = market_data.get('vix_level', 'normal')
        time_of_day = market_data.get('time_of_day', 'normal')
        
        confidence_impact = 0.0
        if market_trend == 'bullish' and vix_level == 'low':
            confidence_impact = 0.4
        elif market_trend == 'bearish' or vix_level == 'high':
            confidence_impact = -0.3
        
        await self.log_reasoning_step(
            decision_id,
            'market_context',
            {
                'market_trend': market_trend,
                'vix_level': vix_level,
                'time_of_day': time_of_day,
                'sector_performance': market_data.get('sector_performance', {}),
                'reasoning': f"Market conditions: {market_trend} trend, VIX {vix_level}"
            },
            confidence_impact
        )
    
    async def log_alternative_considered(self, decision_id: str, 
                                       alternative: Dict[str, Any]) -> None:
        """Log an alternative decision that was considered."""
        if decision_id not in self.active_decisions:
            return
        
        reasoning = self.active_decisions[decision_id]
        reasoning.alternatives_considered.append({
            'alternative': alternative.get('action', 'unknown'),
            'reasoning': alternative.get('reasoning', ''),
            'confidence_score': alternative.get('confidence_score', 0.0),
            'why_rejected': alternative.get('why_rejected', ''),
            'timestamp': datetime.now().isoformat()
        })
    
    async def finalize_decision(self, decision_id: str, final_decision: str, 
                              final_confidence: float, expected_outcome: Dict[str, Any],
                              key_factors: List[str], risk_factors: List[str]) -> None:
        """Finalize and save the decision reasoning."""
        if decision_id not in self.active_decisions:
            logger.warning(f"Decision ID {decision_id} not found")
            return
        
        reasoning = self.active_decisions[decision_id]
        reasoning.final_decision = final_decision
        reasoning.confidence_score = final_confidence
        reasoning.expected_outcome = expected_outcome
        reasoning.key_factors = key_factors
        reasoning.risk_factors = risk_factors
        
        # Calculate total confidence from steps
        total_confidence_impact = sum(reasoning.confidence_breakdown.values())
        base_confidence = 5.0  # Starting point
        calculated_confidence = base_confidence + total_confidence_impact
        
        # Log confidence calculation breakdown
        await self.log_reasoning_step(
            decision_id,
            'confidence_calculation',
            {
                'base_confidence': base_confidence,
                'confidence_breakdown': reasoning.confidence_breakdown,
                'total_impact': total_confidence_impact,
                'final_confidence': final_confidence,
                'reasoning': f"Final confidence: {final_confidence:.1f}/10 "
                           f"(calculated: {calculated_confidence:.1f})"
            },
            0.0
        )
        
        # Save to persistent storage
        await self._save_decision_reasoning(reasoning)
        
        # Remove from active decisions
        del self.active_decisions[decision_id]
        
        logger.info(f"Finalized decision {decision_id}: {final_decision} "
                   f"(confidence: {final_confidence:.1f})")
    
    async def log_decision_outcome(self, decision_id: str, 
                                 actual_outcome: Dict[str, Any]) -> None:
        """Log the actual outcome of a decision for learning."""
        # Load the original decision
        decision_reasoning = await self._load_decision_by_id(decision_id)
        if not decision_reasoning:
            logger.warning(f"Could not find decision {decision_id} for outcome logging")
            return
        
        expected = decision_reasoning.get('expected_outcome', {})
        
        # Calculate accuracy metrics
        accuracy_metrics = {}
        
        # Price direction accuracy
        expected_direction = expected.get('direction', 'unknown')
        actual_direction = actual_outcome.get('direction', 'unknown')
        accuracy_metrics['direction_accuracy'] = 1.0 if expected_direction == actual_direction else 0.0
        
        # Price magnitude accuracy
        expected_move = expected.get('price_move_percent', 0)
        actual_move = actual_outcome.get('price_move_percent', 0)
        if expected_move != 0:
            magnitude_error = abs(expected_move - actual_move) / abs(expected_move)
            accuracy_metrics['magnitude_accuracy'] = max(0.0, 1.0 - magnitude_error)
        else:
            accuracy_metrics['magnitude_accuracy'] = 0.5
        
        # Timing accuracy
        expected_duration = expected.get('duration_hours', 24)
        actual_duration = actual_outcome.get('duration_hours', 24)
        if expected_duration > 0:
            timing_error = abs(expected_duration - actual_duration) / expected_duration
            accuracy_metrics['timing_accuracy'] = max(0.0, 1.0 - timing_error)
        else:
            accuracy_metrics['timing_accuracy'] = 0.5
        
        # Overall accuracy
        accuracy_metrics['overall_accuracy'] = (
            accuracy_metrics['direction_accuracy'] * 0.5 +
            accuracy_metrics['magnitude_accuracy'] * 0.3 +
            accuracy_metrics['timing_accuracy'] * 0.2
        )
        
        # Generate lessons learned
        lessons_learned = self._generate_lessons_learned(
            decision_reasoning, actual_outcome, accuracy_metrics
        )
        
        # Create outcome record
        outcome = DecisionOutcome(
            decision_id=decision_id,
            actual_outcome=actual_outcome,
            expectation_vs_reality={
                'expected': expected,
                'actual': actual_outcome,
                'accuracy_metrics': accuracy_metrics
            },
            accuracy_metrics=accuracy_metrics,
            lessons_learned=lessons_learned,
            timestamp=datetime.now()
        )
        
        # Save outcome
        await self._save_decision_outcome(outcome)
        
        logger.info(f"Logged outcome for decision {decision_id}: "
                   f"overall accuracy {accuracy_metrics['overall_accuracy']*100:.1f}%")
    
    def _generate_lessons_learned(self, decision_reasoning: Dict, 
                                actual_outcome: Dict, accuracy_metrics: Dict) -> List[str]:
        """Generate specific lessons learned from decision vs outcome."""
        lessons = []
        
        # Direction lessons
        if accuracy_metrics['direction_accuracy'] == 0.0:
            expected_dir = decision_reasoning.get('expected_outcome', {}).get('direction')
            actual_dir = actual_outcome.get('direction')
            lessons.append(f"Direction prediction failed: expected {expected_dir}, got {actual_dir}")
            
            # Analyze what signals might have been wrong
            confidence_breakdown = decision_reasoning.get('confidence_breakdown', {})
            strongest_signal = max(confidence_breakdown.items(), key=lambda x: abs(x[1]))[0] if confidence_breakdown else 'unknown'
            lessons.append(f"Strongest signal '{strongest_signal}' may need recalibration")
        
        # Magnitude lessons
        if accuracy_metrics['magnitude_accuracy'] < 0.5:
            expected_move = decision_reasoning.get('expected_outcome', {}).get('price_move_percent', 0)
            actual_move = actual_outcome.get('price_move_percent', 0)
            if abs(expected_move) > abs(actual_move):
                lessons.append("Overestimated price movement magnitude - may need to reduce expectations")
            else:
                lessons.append("Underestimated price movement magnitude - may have missed stronger signals")
        
        # Confidence lessons
        confidence_score = decision_reasoning.get('confidence_score', 5.0)
        overall_accuracy = accuracy_metrics['overall_accuracy']
        
        if confidence_score >= 8.0 and overall_accuracy < 0.6:
            lessons.append("High confidence but poor outcome - confidence calibration needs adjustment")
        elif confidence_score <= 6.0 and overall_accuracy > 0.8:
            lessons.append("Low confidence but good outcome - may be too conservative")
        
        # Risk factor lessons
        risk_factors = decision_reasoning.get('risk_factors', [])
        if actual_outcome.get('max_adverse_excursion', 0) > 0.05:  # 5% adverse move
            if 'high_volatility' not in risk_factors:
                lessons.append("Experienced high adverse excursion - should have flagged volatility risk")
        
        return lessons
    
    async def get_reasoning_patterns(self) -> Dict[str, Any]:
        """Analyze reasoning patterns for insights."""
        try:
            with open(self.decisions_file, 'r') as f:
                decisions = json.load(f)
            
            with open(self.decision_outcomes_file, 'r') as f:
                outcomes = json.load(f)
        except FileNotFoundError:
            return {'error': 'No decision data available'}
        
        # Analyze patterns
        patterns = {
            'most_reliable_signals': {},
            'least_reliable_signals': {},
            'best_confidence_ranges': {},
            'common_failure_patterns': {},
            'successful_combinations': {}
        }
        
        # Group decisions by outcome quality
        for outcome in outcomes:
            decision_id = outcome['decision_id']
            decision = next((d for d in decisions if d['decision_id'] == decision_id), None)
            if not decision:
                continue
            
            accuracy = outcome['accuracy_metrics']['overall_accuracy']
            confidence_breakdown = decision.get('confidence_breakdown', {})
            
            # Track signal reliability
            for signal, impact in confidence_breakdown.items():
                if signal not in patterns['most_reliable_signals']:
                    patterns['most_reliable_signals'][signal] = []
                patterns['most_reliable_signals'][signal].append(accuracy)
        
        # Calculate average accuracy for each signal
        for signal, accuracies in patterns['most_reliable_signals'].items():
            patterns['most_reliable_signals'][signal] = {
                'avg_accuracy': sum(accuracies) / len(accuracies),
                'sample_count': len(accuracies)
            }
        
        # Save patterns
        with open(self.reasoning_patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        return patterns
    
    async def _save_decision_reasoning(self, reasoning: AIReasoning) -> None:
        """Save decision reasoning to persistent storage."""
        try:
            # Load existing decisions
            decisions = []
            try:
                with open(self.decisions_file, 'r') as f:
                    decisions = json.load(f)
            except FileNotFoundError:
                pass
            
            # Convert to dict
            reasoning_dict = asdict(reasoning)
            reasoning_dict['timestamp'] = reasoning.timestamp.isoformat()
            reasoning_dict['context']['timestamp'] = reasoning.context.time_context.get('timestamp', datetime.now().isoformat())
            
            decisions.append(reasoning_dict)
            
            # Save
            with open(self.decisions_file, 'w') as f:
                json.dump(decisions, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving decision reasoning: {e}")
    
    async def _save_decision_outcome(self, outcome: DecisionOutcome) -> None:
        """Save decision outcome to persistent storage."""
        try:
            # Load existing outcomes
            outcomes = []
            try:
                with open(self.decision_outcomes_file, 'r') as f:
                    outcomes = json.load(f)
            except FileNotFoundError:
                pass
            
            # Convert to dict
            outcome_dict = asdict(outcome)
            outcome_dict['timestamp'] = outcome.timestamp.isoformat()
            
            outcomes.append(outcome_dict)
            
            # Save
            with open(self.decision_outcomes_file, 'w') as f:
                json.dump(outcomes, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving decision outcome: {e}")
    
    async def _load_decision_by_id(self, decision_id: str) -> Optional[Dict]:
        """Load a specific decision by ID."""
        try:
            with open(self.decisions_file, 'r') as f:
                decisions = json.load(f)
            
            for decision in decisions:
                if decision.get('decision_id') == decision_id:
                    return decision
            
            return None
            
        except FileNotFoundError:
            return None
    
    def get_active_decisions(self) -> Dict[str, Dict]:
        """Get currently active decisions."""
        return {
            decision_id: {
                'ticker': reasoning.context.ticker,
                'timestamp': reasoning.timestamp.isoformat(),
                'steps_logged': len(reasoning.reasoning_steps),
                'current_confidence': sum(reasoning.confidence_breakdown.values())
            }
            for decision_id, reasoning in self.active_decisions.items()
        }
