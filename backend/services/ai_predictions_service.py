"""
AI Price Predictions Service - Real-time ML predictions for API
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AIPredictionsService:
    """Service for getting AI predictions data for frontend API."""
    
    def __init__(self):
        """Initialize AI predictions service."""
        pass
    
    def get_predictions_dashboard_data(self) -> Dict[str, Any]:
        """Get complete predictions data for dashboard."""
        try:
            # Get predictions from AI learning engine
            predictions = self.get_ai_predictions()
            
            if predictions:
                return {
                    'success': True,
                    'predictions': predictions,
                    'summary': self.get_prediction_summary(predictions),
                    'performance': self.get_model_performance_data(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': True,
                    'predictions': [],
                    'summary': {},
                    'performance': {},
                    'message': "AI predictions loading... Check back in a few minutes!",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting AI predictions dashboard data: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_ai_predictions(self) -> List[Dict[str, Any]]:
        """Fetch AI predictions from learning engine."""
        try:
            # Get real AI predictions from file storage
            import sys
            import os
            
            # Import from same directory
            current_dir = os.path.dirname(__file__)
            sys.path.insert(0, current_dir)
            
            from ai_learning_engine import AILearningEngine
            ai_engine = AILearningEngine()
            
            # Use the actual method from AI engine
            predictions_data = ai_engine._load_predictions()
            
            if predictions_data and len(predictions_data) > 0:
                return self.format_predictions_from_data(predictions_data)
            else:
                # Return empty list if no real predictions available
                logger.info("No AI predictions available yet - system still learning")
                return []
        except Exception as e:
            logger.error(f"Error loading AI predictions: {e}")
            return []

    def format_predictions_from_data(self, raw_predictions) -> List[Dict[str, Any]]:
        """Format predictions from JSON data for API response."""
        formatted = []
        for pred_data in raw_predictions:
            try:
                formatted.append({
                    'symbol': pred_data.get('ticker', 'Unknown'),
                    'confidence': pred_data.get('confidence_score', 0) * 10,  # Convert to 1-10 scale
                    'direction': pred_data.get('predicted_direction', 'neutral'),
                    'target_price': pred_data.get('target_price', 0),
                    'current_price': pred_data.get('current_price', 0),
                    'timeframe': f"{pred_data.get('predicted_timeframe_hours', 1):.0f}h",
                    'reasoning': ' | '.join(pred_data.get('reasoning_factors', [])[:2]),  # First 2 reasons
                    'technical_score': pred_data.get('technical_signals', {}).get('overall_score', 0) * 10,
                    'momentum_score': pred_data.get('technical_signals', {}).get('momentum_score', 0) * 10,
                    'volume_score': pred_data.get('technical_signals', {}).get('volume_score', 0) * 10,
                    'expected_move': self.calculate_expected_move(
                        pred_data.get('current_price', 0),
                        pred_data.get('target_price', 0)
                    ),
                    'timestamp': pred_data.get('timestamp', datetime.now().isoformat())
                })
            except Exception as e:
                logger.error(f"Error formatting prediction: {e}")
                continue
        
        return formatted

    def calculate_expected_move(self, current_price: float, target_price: float) -> float:
        """Calculate expected percentage move."""
        if current_price > 0:
            return ((target_price - current_price) / current_price) * 100
        return 0.0

    def get_prediction_summary(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate prediction summary metrics."""
        if not predictions:
            return {}
            
        total_predictions = len(predictions)
        high_confidence = len([p for p in predictions if p.get('confidence', 0) >= 8.0])
        avg_confidence = sum(p.get('confidence', 0) for p in predictions) / total_predictions if total_predictions > 0 else 0
        bullish_predictions = len([p for p in predictions if p.get('direction', '') == 'bullish'])
        
        return {
            'total_predictions': total_predictions,
            'high_confidence_count': high_confidence,
            'high_confidence_percent': (high_confidence / total_predictions * 100) if total_predictions > 0 else 0,
            'avg_confidence': round(avg_confidence, 1),
            'bullish_count': bullish_predictions,
            'bullish_percent': (bullish_predictions / total_predictions * 100) if total_predictions > 0 else 0,
            'bearish_count': total_predictions - bullish_predictions,
            'bearish_percent': ((total_predictions - bullish_predictions) / total_predictions * 100) if total_predictions > 0 else 0
        }

    def get_model_performance_data(self) -> Dict[str, Any]:
        """Get REAL model performance metrics from AI learning engine."""
        try:
            import sys
            import os
            
            # Import from same directory
            current_dir = os.path.dirname(__file__)
            sys.path.insert(0, current_dir)
            
            from ai_learning_engine import AILearningEngine
            from database_manager import DatabaseManager
            
            logger.info("📊 Getting REAL model performance from AI engine")
            
            # Get real performance from AI learning engine
            ai_engine = AILearningEngine()
            db = DatabaseManager()
            
            # Get actual learning status
            learning_status = ai_engine.get_learning_status()
            
            # Get predictions from file
            predictions_data = ai_engine._load_predictions()
            
            if not predictions_data:
                logger.warning("No predictions for performance calculation")
                return {
                    'accuracy': 0.0,
                    'precision': 0.0,
                    'total_predictions': 0,
                    'correct_predictions': 0,
                    'training_samples': learning_status.get('total_outcomes', 0),
                    'model_version': 'v2.1',
                    'last_update': 'No data yet',
                    'learning_progress': learning_status.get('learning_progress', 0.0),
                    'status': 'initializing'
                }
            
            # Use learning status for real metrics
            total_predictions = len(predictions_data)
            training_samples = learning_status.get('total_outcomes', 0)
            accuracy = learning_status.get('accuracy', 0.0) * 100
            
            return {
                'accuracy': round(accuracy, 1),
                'precision': round(accuracy, 1),  # Simplified for now
                'total_predictions': total_predictions,
                'correct_predictions': int(total_predictions * accuracy / 100),
                'training_samples': training_samples,
                'model_version': 'v2.1',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'learning_progress': round(learning_status.get('learning_progress', 0.0), 1),
                'status': 'active' if training_samples > 0 else 'initializing'
            }
            
        except Exception as e:
            logger.error(f"Error getting real model performance: {e}")
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'total_predictions': 0,
                'correct_predictions': 0,
                'training_samples': 0,
                'model_version': 'v1.0',
                'last_update': 'Error loading data',
                'learning_progress': 0.0,
                'status': 'error',
                'error': str(e)
            }

    def get_top_predictions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top predictions by confidence score."""
        predictions = self.get_ai_predictions()
        if not predictions:
            return []
        
        # Sort by confidence score descending
        sorted_predictions = sorted(predictions, key=lambda x: x.get('confidence', 0), reverse=True)
        return sorted_predictions[:limit]

    def get_predictions_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get prediction for specific symbol."""
        predictions = self.get_ai_predictions()
        for pred in predictions:
            if pred.get('symbol', '').upper() == symbol.upper():
                return pred
        return None

    def get_high_confidence_signals(self, min_confidence: float = 8.0) -> List[Dict[str, Any]]:
        """Get only high confidence trading signals."""
        predictions = self.get_ai_predictions()
        return [pred for pred in predictions if pred.get('confidence', 0) >= min_confidence]

# Global service instance
ai_predictions_service = AIPredictionsService()
