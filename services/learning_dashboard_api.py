"""
Learning Dashboard API - Provides comprehensive monitoring of AI learning progress.
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from services.learning_manager import LearningManager
from services.ai_learning_engine import AILearningEngine
from services.enhanced_decision_logger import EnhancedDecisionLogger


app = FastAPI(title="Signal Flow AI Learning Dashboard", version="1.0.0")

# Initialize components
learning_manager = LearningManager()
learning_engine = AILearningEngine()
decision_logger = EnhancedDecisionLogger()


@app.get("/api/learning/status")
async def get_learning_status():
    """Get comprehensive learning system status."""
    try:
        status = learning_manager.get_learning_status_summary()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting learning status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/metrics")
async def get_learning_metrics():
    """Get detailed learning metrics."""
    try:
        learning_status = learning_engine.get_learning_status()
        
        # Load recent metrics
        with open('data/learning_metrics.json', 'r') as f:
            recent_metrics = json.load(f)
        
        return JSONResponse(content={
            'current_status': learning_status,
            'recent_metrics': recent_metrics,
            'timestamp': datetime.now().isoformat()
        })
    except FileNotFoundError:
        return JSONResponse(content={
            'current_status': learning_engine.get_learning_status(),
            'recent_metrics': None,
            'message': 'No learning metrics available yet'
        })
    except Exception as e:
        logger.error(f"Error getting learning metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/performance")
async def get_performance_analytics():
    """Get comprehensive performance analytics."""
    try:
        # Load trade outcomes
        with open('data/trade_outcomes.json', 'r') as f:
            outcomes = json.load(f)
        
        # Load predictions
        with open('data/ai_predictions.json', 'r') as f:
            predictions = json.load(f)
        
        # Calculate analytics
        analytics = _calculate_performance_analytics(outcomes, predictions)
        
        return JSONResponse(content=analytics)
    except FileNotFoundError:
        return JSONResponse(content={
            'error': 'No performance data available yet',
            'total_trades': 0,
            'message': 'Start trading to see performance analytics'
        })
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/decisions")
async def get_decision_analytics():
    """Get decision-making analytics."""
    try:
        # Get reasoning patterns
        patterns = await decision_logger.get_reasoning_patterns()
        
        # Get active decisions
        active_decisions = decision_logger.get_active_decisions()
        
        # Load decision history
        with open('data/ai_decisions.json', 'r') as f:
            decision_history = json.load(f)
        
        # Calculate decision analytics
        decision_analytics = _calculate_decision_analytics(decision_history, active_decisions)
        
        return JSONResponse(content={
            'reasoning_patterns': patterns,
            'active_decisions': active_decisions,
            'decision_analytics': decision_analytics,
            'timestamp': datetime.now().isoformat()
        })
    except FileNotFoundError:
        return JSONResponse(content={
            'reasoning_patterns': {},
            'active_decisions': decision_logger.get_active_decisions(),
            'decision_analytics': {},
            'message': 'No decision history available yet'
        })
    except Exception as e:
        logger.error(f"Error getting decision analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/insights")
async def get_daily_insights():
    """Get daily insights and recommendations."""
    try:
        with open('data/daily_insights.json', 'r') as f:
            insights = json.load(f)
        
        return JSONResponse(content=insights)
    except FileNotFoundError:
        # Generate insights if not available
        insights = await learning_manager.generate_daily_insights()
        return JSONResponse(content=insights)
    except Exception as e:
        logger.error(f"Error getting daily insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/model-weights")
async def get_model_weights():
    """Get current AI model weights and their evolution."""
    try:
        current_weights = learning_engine.model_weights
        
        # Load weight history if available
        weight_history = []
        try:
            with open('data/weight_history.json', 'r') as f:
                weight_history = json.load(f)
        except FileNotFoundError:
            pass
        
        return JSONResponse(content={
            'current_weights': current_weights,
            'weight_history': weight_history,
            'last_updated': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting model weights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/backtest-results")
async def get_backtest_results():
    """Get latest backtesting results."""
    try:
        with open('data/backtest_results.json', 'r') as f:
            backtest_results = json.load(f)
        
        # Load strategy comparison if available
        comparison_results = {}
        try:
            with open('data/strategy_comparison.json', 'r') as f:
                comparison_results = json.load(f)
        except FileNotFoundError:
            pass
        
        return JSONResponse(content={
            'latest_backtest': backtest_results,
            'strategy_comparison': comparison_results,
            'timestamp': datetime.now().isoformat()
        })
    except FileNotFoundError:
        return JSONResponse(content={
            'message': 'No backtest results available yet',
            'recommendation': 'Backtesting will run automatically after collecting sufficient data'
        })
    except Exception as e:
        logger.error(f"Error getting backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learning/trigger-learning")
async def trigger_manual_learning():
    """Manually trigger a learning cycle."""
    try:
        logger.info("Manual learning cycle triggered via API")
        results = await learning_manager.run_comprehensive_learning()
        
        return JSONResponse(content={
            'status': 'success',
            'message': 'Learning cycle completed',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in manual learning trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learning/trigger-backtest")
async def trigger_manual_backtest():
    """Manually trigger strategy validation through backtesting."""
    try:
        logger.info("Manual backtest triggered via API")
        results = await learning_manager.run_strategy_validation()
        
        return JSONResponse(content={
            'status': 'success',
            'message': 'Backtest completed',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in manual backtest trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/predictions/{ticker}")
async def get_ticker_predictions(ticker: str):
    """Get prediction history for a specific ticker."""
    try:
        with open('data/ai_predictions.json', 'r') as f:
            predictions = json.load(f)
        
        with open('data/trade_outcomes.json', 'r') as f:
            outcomes = json.load(f)
        
        # Filter for ticker
        ticker_predictions = [p for p in predictions if p['ticker'] == ticker.upper()]
        ticker_outcomes = [o for o in outcomes if o['ticker'] == ticker.upper()]
        
        # Match predictions with outcomes
        matched_data = []
        for pred in ticker_predictions:
            pred_id = pred.get('id')
            matching_outcome = next((o for o in ticker_outcomes if o.get('trade_id') == pred_id), None)
            
            matched_data.append({
                'prediction': pred,
                'outcome': matching_outcome,
                'accuracy': matching_outcome.get('prediction_accuracy') if matching_outcome else None
            })
        
        # Calculate ticker-specific metrics
        ticker_metrics = _calculate_ticker_metrics(matched_data)
        
        return JSONResponse(content={
            'ticker': ticker.upper(),
            'total_predictions': len(ticker_predictions),
            'total_outcomes': len(ticker_outcomes),
            'metrics': ticker_metrics,
            'prediction_history': matched_data[-20:],  # Last 20 predictions
            'timestamp': datetime.now().isoformat()
        })
    except FileNotFoundError:
        return JSONResponse(content={
            'ticker': ticker.upper(),
            'message': 'No prediction data available for this ticker'
        })
    except Exception as e:
        logger.error(f"Error getting ticker predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/signal-performance")
async def get_signal_performance():
    """Get performance analytics for different signals."""
    try:
        with open('data/reasoning_patterns.json', 'r') as f:
            patterns = json.load(f)
        
        # Analyze signal performance
        signal_performance = _analyze_signal_performance(patterns)
        
        return JSONResponse(content={
            'signal_performance': signal_performance,
            'timestamp': datetime.now().isoformat()
        })
    except FileNotFoundError:
        return JSONResponse(content={
            'message': 'No signal performance data available yet'
        })
    except Exception as e:
        logger.error(f"Error getting signal performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/learning-curve")
async def get_learning_curve():
    """Get AI learning curve over time."""
    try:
        # Load historical learning results
        learning_curve_data = []
        
        # This would load historical learning metrics
        # For now, we'll return current status
        current_status = learning_engine.get_learning_status()
        
        return JSONResponse(content={
            'learning_curve': learning_curve_data,
            'current_status': current_status,
            'message': 'Learning curve data will be available after multiple learning cycles',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting learning curve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_performance_analytics(outcomes: List[Dict], predictions: List[Dict]) -> Dict[str, Any]:
    """Calculate comprehensive performance analytics."""
    if not outcomes:
        return {'total_trades': 0, 'message': 'No trade data available'}
    
    # Basic metrics
    total_trades = len(outcomes)
    successful_trades = len([o for o in outcomes if o.get('success', False)])
    win_rate = successful_trades / total_trades if total_trades > 0 else 0
    
    # P&L metrics
    total_pnl = sum(o.get('actual_move_percent', 0) for o in outcomes)
    avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
    
    # Accuracy metrics
    accuracies = [o.get('prediction_accuracy', 0) for o in outcomes if o.get('prediction_accuracy') is not None]
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
    
    # Time-based analytics
    current_time = datetime.now()
    
    # Last 7 days
    week_ago = current_time - timedelta(days=7)
    recent_outcomes = [
        o for o in outcomes 
        if datetime.fromisoformat(o.get('timestamp', '1970-01-01')) >= week_ago
    ]
    
    recent_win_rate = len([o for o in recent_outcomes if o.get('success', False)]) / len(recent_outcomes) if recent_outcomes else 0
    recent_avg_accuracy = sum(o.get('prediction_accuracy', 0) for o in recent_outcomes) / len(recent_outcomes) if recent_outcomes else 0
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl_percent': total_pnl,
        'avg_trade_pnl_percent': avg_trade_pnl,
        'avg_prediction_accuracy': avg_accuracy,
        'recent_performance': {
            'last_7_days_trades': len(recent_outcomes),
            'last_7_days_win_rate': recent_win_rate,
            'last_7_days_avg_accuracy': recent_avg_accuracy
        },
        'improvement_trend': recent_win_rate - win_rate,  # Positive = improving
        'accuracy_trend': recent_avg_accuracy - avg_accuracy
    }


def _calculate_decision_analytics(decision_history: List[Dict], active_decisions: Dict) -> Dict[str, Any]:
    """Calculate decision-making analytics."""
    if not decision_history:
        return {'total_decisions': 0}
    
    total_decisions = len(decision_history)
    
    # Analyze decision types
    decision_types = {}
    confidence_distribution = {}
    
    for decision in decision_history:
        final_decision = decision.get('final_decision', 'unknown')
        confidence = decision.get('confidence_score', 0)
        
        decision_types[final_decision] = decision_types.get(final_decision, 0) + 1
        
        # Confidence buckets
        conf_bucket = f"{int(confidence)}-{int(confidence)+1}"
        confidence_distribution[conf_bucket] = confidence_distribution.get(conf_bucket, 0) + 1
    
    # Average reasoning steps
    avg_reasoning_steps = sum(len(d.get('reasoning_steps', [])) for d in decision_history) / total_decisions
    
    return {
        'total_decisions': total_decisions,
        'decision_types': decision_types,
        'confidence_distribution': confidence_distribution,
        'avg_reasoning_steps': avg_reasoning_steps,
        'active_decisions_count': len(active_decisions)
    }


def _calculate_ticker_metrics(matched_data: List[Dict]) -> Dict[str, Any]:
    """Calculate metrics for a specific ticker."""
    if not matched_data:
        return {}
    
    outcomes = [m['outcome'] for m in matched_data if m['outcome']]
    
    if not outcomes:
        return {'predictions_only': len(matched_data)}
    
    return {
        'total_trades': len(outcomes),
        'win_rate': len([o for o in outcomes if o.get('success', False)]) / len(outcomes),
        'avg_accuracy': sum(o.get('prediction_accuracy', 0) for o in outcomes) / len(outcomes),
        'avg_move_percent': sum(o.get('actual_move_percent', 0) for o in outcomes) / len(outcomes),
        'avg_duration_hours': sum(o.get('actual_duration_hours', 0) for o in outcomes) / len(outcomes)
    }


def _analyze_signal_performance(patterns: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze performance of different signals."""
    signal_performance = {}
    
    most_reliable = patterns.get('most_reliable_signals', {})
    
    for signal, stats in most_reliable.items():
        if stats.get('sample_count', 0) >= 5:  # Minimum sample size
            signal_performance[signal] = {
                'reliability_score': stats.get('avg_accuracy', 0),
                'sample_count': stats.get('sample_count', 0),
                'confidence': 'high' if stats.get('sample_count', 0) >= 20 else 'medium' if stats.get('sample_count', 0) >= 10 else 'low'
            }
    
    return signal_performance


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
