"""
Enhanced Decision Logger - MongoDB Version
Captures detailed AI reasoning for learning using MongoDB persistence.
"""
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


class EnhancedDecisionLogger:
    """Enhanced decision logger with MongoDB persistence for AI learning."""
    
    def __init__(self):
        self.config = Config()
        self.current_reasoning = None
        logger.info("Enhanced Decision Logger initialized with MongoDB persistence")
    
    async def _get_db_manager(self):
        """Get database manager instance."""
        # Import here to avoid circular imports
        from services.database_manager import DatabaseManager
        return DatabaseManager()
    
    async def start_reasoning_session(self, context: DecisionContext) -> str:
        """Start a new reasoning session."""
        decision_id = f"decision_{int(datetime.now().timestamp() * 1000)}"
        
        self.current_reasoning = AIReasoning(
            decision_id=decision_id,
            timestamp=datetime.now(),
            context=context,
            reasoning_steps=[],
            confidence_breakdown={},
            risk_assessment={},
            final_decision="",
            confidence_score=0.0,
            expected_outcome={},
            alternatives_considered=[],
            key_factors=[],
            risk_factors=[]
        )
        
        logger.info(f"Started reasoning session: {decision_id}")
        return decision_id
    
    async def log_reasoning_step(self, step_name: str, analysis: Dict[str, Any], 
                               confidence: float, reasoning: str) -> None:
        """Log a step in the reasoning process."""
        if not self.current_reasoning:
            logger.warning("No active reasoning session")
            return
        
        step = {
            'step_name': step_name,
            'timestamp': datetime.now(),
            'analysis': analysis,
            'confidence': confidence,
            'reasoning': reasoning,
            'step_order': len(self.current_reasoning.reasoning_steps)
        }
        
        self.current_reasoning.reasoning_steps.append(step)
        self.current_reasoning.confidence_breakdown[step_name] = confidence
        
        logger.debug(f"Logged reasoning step: {step_name} (confidence: {confidence:.2f})")
    
    async def add_risk_factor(self, factor: str, severity: str, impact: float) -> None:
        """Add a risk factor to current reasoning."""
        if not self.current_reasoning:
            return
        
        risk_item = {
            'factor': factor,
            'severity': severity,
            'impact': impact,
            'timestamp': datetime.now()
        }
        
        self.current_reasoning.risk_assessment[factor] = risk_item
        self.current_reasoning.risk_factors.append(factor)
    
    async def add_key_factor(self, factor: str, weight: float) -> None:
        """Add a key decision factor."""
        if not self.current_reasoning:
            return
        
        self.current_reasoning.key_factors.append({
            'factor': factor,
            'weight': weight,
            'timestamp': datetime.now()
        })
    
    async def consider_alternative(self, alternative: str, pros: List[str], 
                                 cons: List[str], confidence: float) -> None:
        """Log an alternative that was considered."""
        if not self.current_reasoning:
            return
        
        alt = {
            'alternative': alternative,
            'pros': pros,
            'cons': cons,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
        
        self.current_reasoning.alternatives_considered.append(alt)
    
    async def finalize_decision(self, decision: str, confidence: float, 
                              expected_outcome: Dict[str, Any]) -> bool:
        """Finalize the reasoning and save to MongoDB."""
        if not self.current_reasoning:
            logger.error("No active reasoning session to finalize")
            return False
        
        self.current_reasoning.final_decision = decision
        self.current_reasoning.confidence_score = confidence
        self.current_reasoning.expected_outcome = expected_outcome
        
        try:
            # Get database manager
            db_manager = await self._get_db_manager()
            
            # Convert to dict for MongoDB storage
            decision_data = asdict(self.current_reasoning)
            
            # Ensure datetime objects are properly handled
            decision_data['timestamp'] = self.current_reasoning.timestamp
            
            # Add metadata for tracking
            decision_data['system_version'] = 'enhanced_mongodb'
            decision_data['logger_type'] = 'enhanced_decision_logger'
            
            # Save to MongoDB using ai_decisions collection
            success = await db_manager.save_ai_decision(decision_data)
            
            if success:
                logger.info(f"✅ Decision reasoning saved to MongoDB: {self.current_reasoning.decision_id}")
                self.current_reasoning = None
                return True
            else:
                logger.error(f"❌ Failed to save decision reasoning to MongoDB")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving decision to MongoDB: {e}")
            return False
    
    async def log_decision_outcome(self, decision_id: str, actual_outcome: Dict[str, Any], 
                                 outcome_timestamp: Optional[datetime] = None) -> bool:
        """Log the actual outcome of a decision for learning."""
        if not outcome_timestamp:
            outcome_timestamp = datetime.now()
        
        try:
            # Get database manager
            db_manager = await self._get_db_manager()
            
            # Update the existing decision with outcome data
            result = await db_manager.async_db.ai_decisions.update_one(
                {'decision_id': decision_id},
                {
                    '$set': {
                        'actual_outcome': actual_outcome,
                        'outcome_timestamp': outcome_timestamp,
                        'outcome_logged': True,
                        'outcome_logger_version': 'enhanced_mongodb'
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Decision outcome logged for {decision_id}")
                return True
            else:
                logger.warning(f"⚠️ No decision found with ID {decision_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to log decision outcome: {e}")
            return False
    
    async def get_learning_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze decision patterns for AI learning using MongoDB aggregation."""
        try:
            # Get database manager
            db_manager = await self._get_db_manager()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # MongoDB aggregation pipeline for pattern analysis
            pipeline = [
                {'$match': {'timestamp': {'$gte': cutoff_date}}},
                {'$group': {
                    '_id': '$final_decision',
                    'count': {'$sum': 1},
                    'avg_confidence': {'$avg': '$confidence_score'},
                    'outcomes': {'$push': '$actual_outcome'}
                }},
                {'$sort': {'count': -1}}
            ]
            
            cursor = db_manager.async_db.ai_decisions.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            patterns = {
                'decision_distribution': results,
                'total_decisions': sum(r['count'] for r in results),
                'analysis_period_days': days,
                'generated_at': datetime.now(),
                'data_source': 'mongodb_aggregation'
            }
            
            logger.info(f"📊 Analyzed {patterns['total_decisions']} decisions over {days} days")
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze learning patterns: {e}")
            return {}
    
    async def get_accuracy_metrics(self, days: int = 30) -> Dict[str, float]:
        """Calculate decision accuracy metrics from MongoDB data."""
        try:
            # Get database manager
            db_manager = await self._get_db_manager()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get decisions with outcomes
            cursor = db_manager.async_db.ai_decisions.find({
                'timestamp': {'$gte': cutoff_date},
                'outcome_logged': True,
                'actual_outcome': {'$exists': True}
            })
            
            decisions_with_outcomes = await cursor.to_list(length=None)
            
            if not decisions_with_outcomes:
                return {'accuracy': 0.0, 'sample_size': 0}
            
            # Calculate accuracy metrics
            correct_predictions = 0
            total_predictions = len(decisions_with_outcomes)
            confidence_sum = 0
            
            for decision in decisions_with_outcomes:
                expected = decision.get('expected_outcome', {})
                actual = decision.get('actual_outcome', {})
                confidence = decision.get('confidence_score', 0)
                
                confidence_sum += confidence
                
                # Enhanced accuracy calculation
                if expected.get('direction') == actual.get('direction'):
                    correct_predictions += 1
                    
                    # Bonus for magnitude accuracy
                    expected_magnitude = expected.get('expected_return', 0)
                    actual_magnitude = actual.get('actual_return', 0)
                    
                    if expected_magnitude > 0 and actual_magnitude > 0:
                        if abs(expected_magnitude - actual_magnitude) / expected_magnitude < 0.5:
                            # Within 50% of expected magnitude
                            correct_predictions += 0.5
            
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
            avg_confidence = confidence_sum / total_predictions if total_predictions > 0 else 0.0
            
            metrics = {
                'accuracy': accuracy,
                'correct_predictions': correct_predictions,
                'total_predictions': total_predictions,
                'sample_size': total_predictions,
                'average_confidence': avg_confidence,
                'confidence_accuracy_ratio': accuracy / avg_confidence if avg_confidence > 0 else 0,
                'analysis_period_days': days,
                'calculated_at': datetime.now()
            }
            
            logger.info(f"📈 Accuracy: {accuracy:.2%}, Confidence: {avg_confidence:.2%} ({total_predictions} decisions)")
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate accuracy metrics: {e}")
            return {'accuracy': 0.0, 'sample_size': 0}
    
    async def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decisions for analysis."""
        try:
            # Get database manager
            db_manager = await self._get_db_manager()
            
            cursor = db_manager.async_db.ai_decisions.find().sort('timestamp', -1).limit(limit)
            decisions = await cursor.to_list(length=limit)
            
            return decisions
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent decisions: {e}")
            return []
    
    async def clear_old_decisions(self, days: int = 90) -> int:
        """Clear old decisions beyond retention period."""
        try:
            # Get database manager
            db_manager = await self._get_db_manager()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            result = await db_manager.async_db.ai_decisions.delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            
            deleted_count = result.deleted_count
            logger.info(f"🧹 Cleared {deleted_count} old decisions (older than {days} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to clear old decisions: {e}")
            return 0
