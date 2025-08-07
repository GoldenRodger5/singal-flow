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


def get_ai_predictions():
    """Fetch AI predictions from learning engine."""
    try:
        # Get real AI predictions only
        from services.ai_learning_engine import AILearningEngine
        ai_engine = AILearningEngine()
        predictions = ai_engine.get_latest_predictions()
        
        if predictions and len(predictions) > 0:
            return predictions
        else:
            # Return empty list if no real predictions available
            logger.info("No AI predictions available yet - system still learning")
            return []
    except Exception as e:
        logger.error(f"Error loading AI predictions: {e}")
        return []


def show_prediction_summary(predictions):
    """Display prediction summary metrics."""
    if not predictions:
        return
        
    # Calculate summary metrics
    total_predictions = len(predictions)
    high_confidence = len([p for p in predictions if p.get('confidence', 0) >= 8.0])
    avg_confidence = sum(p.get('confidence', 0) for p in predictions) / total_predictions if total_predictions > 0 else 0
    bullish_predictions = len([p for p in predictions if p.get('direction', '') == 'bullish'])
    
    # Display metrics
    pred_col1, pred_col2, pred_col3, pred_col4 = st.columns(4)
    
    with pred_col1:
        st.metric(
            "🎯 Total Predictions", 
            f"{total_predictions}",
            help="Number of active AI predictions"
        )
        
    with pred_col2:
        st.metric(
            "⭐ High Confidence", 
            f"{high_confidence}",
            delta=f"{(high_confidence/total_predictions*100):.0f}%" if total_predictions > 0 else "0%",
            help="Predictions with confidence ≥ 8.0"
        )
        
    with pred_col3:
        st.metric(
            "📊 Avg Confidence", 
            f"{avg_confidence:.1f}",
            help="Average confidence score across all predictions"
        )
        
    with pred_col4:
        bullish_percent = (bullish_predictions / total_predictions * 100) if total_predictions > 0 else 0
        st.metric(
            "📈 Bullish Signals", 
            f"{bullish_percent:.0f}%",
            help="Percentage of bullish predictions"
        )


def show_detailed_predictions(predictions):
    """Display detailed prediction information."""
    st.markdown("### 🔮 Detailed Predictions")
    
    # Sort by confidence score descending
    predictions = sorted(predictions, key=lambda x: x.get('confidence', 0), reverse=True)
    
    for pred in predictions[:10]:  # Show top 10 predictions
        symbol = pred.get('symbol', 'Unknown')
        confidence = pred.get('confidence', 0)
        direction = pred.get('direction', 'neutral')
        target_price = pred.get('target_price', 0)
        current_price = pred.get('current_price', 0)
        timeframe = pred.get('timeframe', '1h')
        
        # Calculate expected move
        if current_price > 0:
            expected_move = ((target_price - current_price) / current_price) * 100
        else:
            expected_move = 0
            
        # Color coding based on direction
        if direction == 'bullish':
            direction_emoji = "📈"
            direction_color = "green"
        elif direction == 'bearish':
            direction_emoji = "📉"
            direction_color = "red"
        else:
            direction_emoji = "➡️"
            direction_color = "gray"
            
        with st.expander(f"{direction_emoji} {symbol} - Confidence: {confidence:.1f}/10"):
            pred_detail_col1, pred_detail_col2, pred_detail_col3 = st.columns(3)
            
            with pred_detail_col1:
                st.write("**Prediction Details:**")
                st.write(f"• Symbol: {symbol}")
                st.write(f"• Direction: {direction.title()}")
                st.write(f"• Confidence: {confidence:.1f}/10")
                st.write(f"• Timeframe: {timeframe}")
                
            with pred_detail_col2:
                st.write("**Price Targets:**")
                st.write(f"• Current Price: ${current_price:.4f}")
                st.write(f"• Target Price: ${target_price:.4f}")
                st.write(f"• Expected Move: {expected_move:+.1f}%")
                
                if confidence >= 8.0:
                    st.success("🎯 High Confidence Signal")
                elif confidence >= 6.5:
                    st.warning("⚠️ Medium Confidence")
                else:
                    st.info("ℹ️ Low Confidence")
                    
            with pred_detail_col3:
                st.write("**AI Analysis:**")
                
                # Show reasoning if available
                reasoning = pred.get('reasoning', 'AI analysis in progress...')
                st.write(f"• {reasoning}")
                
                # Show technical factors
                technical_score = pred.get('technical_score', 0)
                momentum_score = pred.get('momentum_score', 0)
                volume_score = pred.get('volume_score', 0)
                
                st.write(f"• Technical: {technical_score:.1f}/10")
                st.write(f"• Momentum: {momentum_score:.1f}/10")
                st.write(f"• Volume: {volume_score:.1f}/10")


def show_model_performance():
    """Display AI model performance metrics."""
    st.markdown("### 📊 Model Performance")
    
    try:
        # Get performance metrics
        performance = get_model_performance_data()
        
        perf_col1, perf_col2 = st.columns(2)
        
        with perf_col1:
            st.write("**Recent Performance (7 days):**")
            st.write(f"• Accuracy: {performance.get('accuracy', 0):.1f}%")
            st.write(f"• Precision: {performance.get('precision', 0):.1f}%")
            st.write(f"• Total Predictions: {performance.get('total_predictions', 0)}")
            st.write(f"• Correct Predictions: {performance.get('correct_predictions', 0)}")
            
        with perf_col2:
            st.write("**Learning Status:**")
            st.write(f"• Training Data Points: {performance.get('training_samples', 0):,}")
            st.write(f"• Model Version: {performance.get('model_version', 'v1.0')}")
            st.write(f"• Last Updated: {performance.get('last_update', 'N/A')}")
            
            # Show learning progress
            learning_progress = performance.get('learning_progress', 0)
            st.progress(learning_progress / 100, text=f"Learning Progress: {learning_progress:.0f}%")
            
    except Exception as e:
        logger.error(f"Error showing model performance: {e}")
        st.warning("Model performance data not available")


def get_sample_predictions():
    """Get real predictions from AI learning engine - NO SAMPLE DATA."""
    try:
        from services.ai_learning_engine import AILearningEngine
        
        logger.info("🤖 Getting REAL predictions from AI learning engine")
        
        # Get real predictions from the learning engine
        learning_engine = AILearningEngine()
        real_predictions = learning_engine.get_recent_predictions()
        
        if not real_predictions:
            logger.warning("No real predictions available yet")
            return []
        
        # Convert to dashboard format
        formatted_predictions = []
        for pred in real_predictions:
            formatted_predictions.append({
                'symbol': pred.ticker,
                'confidence': pred.confidence_score * 10,  # Convert to 1-10 scale
                'direction': pred.predicted_direction,
                'target_price': getattr(pred, 'target_price', 0),
                'current_price': getattr(pred, 'current_price', 0),
                'timeframe': f"{pred.predicted_timeframe_hours:.0f}h",
                'reasoning': ' | '.join(pred.reasoning_factors[:2]),  # First 2 reasons
                'technical_score': pred.technical_signals.get('overall_score', 0) * 10,
                'momentum_score': pred.technical_signals.get('momentum_score', 0) * 10,
                'volume_score': pred.technical_signals.get('volume_score', 0) * 10
            })
        
        return formatted_predictions
        
    except Exception as e:
        logger.error(f"Error getting real predictions: {e}")
        # Return empty list instead of sample data in production
        return []


def get_model_performance_data():
    """Get REAL model performance metrics from AI learning engine."""
    try:
        from services.ai_learning_engine import AILearningEngine
        from services.database_manager import DatabaseManager
        
        logger.info("📊 Getting REAL model performance from database")
        
        # Get real performance from AI learning engine
        ai_engine = AILearningEngine()
        db = DatabaseManager()
        
        # Get recent predictions and outcomes
        recent_predictions = ai_engine.get_recent_predictions(days=7)
        recent_outcomes = ai_engine.get_recent_outcomes(days=7)
        
        if not recent_predictions:
            logger.warning("No recent predictions for performance calculation")
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'total_predictions': 0,
                'correct_predictions': 0,
                'training_samples': 0,
                'model_version': 'v1.0',
                'last_update': 'No data yet',
                'learning_progress': 0.0
            }
        
        # Calculate real accuracy
        matched_predictions = []
        for pred in recent_predictions:
            for outcome in recent_outcomes:
                if (pred.ticker == outcome.ticker and 
                    abs((pred.timestamp - outcome.timestamp).total_seconds()) < 3600):  # Within 1 hour
                    matched_predictions.append((pred, outcome))
                    break
        
        if matched_predictions:
            correct = sum(1 for pred, outcome in matched_predictions 
                         if pred.predicted_direction == ('up' if outcome.actual_move > 0 else 'down'))
            accuracy = (correct / len(matched_predictions)) * 100
            precision = accuracy  # Simplified for now
        else:
            accuracy = 0.0
            precision = 0.0
        
        # Get training data count
        all_outcomes = ai_engine.get_all_outcomes()
        training_samples = len(all_outcomes)
        
        # Calculate learning progress (based on minimum samples needed)
        min_samples_needed = 100
        learning_progress = min(100, (training_samples / min_samples_needed) * 100)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'total_predictions': len(recent_predictions),
            'correct_predictions': len(matched_predictions),
            'training_samples': training_samples,
            'model_version': 'v2.1',
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'learning_progress': learning_progress
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
            'learning_progress': 0.0
        }
