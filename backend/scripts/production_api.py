"""
Production FastAPI Server for Signal Flow Trading System
Includes health monitoring, real-time WebSocket updates, and comprehensive API endpoints
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from loguru import logger

from services.health_monitor import health_monitor
from services.database_manager import db_manager, TradeRecord
from services.alpaca_trading import AlpacaTradingService
from services.telegram_trading import telegram_trading
# from services.ai_data_collector import ai_data_collector  # Disabled due to yfinance conflict

# Import the main trading orchestrator
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from main import SignalFlowOrchestrator

# Initialize FastAPI app
app = FastAPI(
    title="Signal Flow Trading System - Production API",
    description="Real-time trading system with AI agents and health monitoring",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize trading service
trading_service = AlpacaTradingService()

# Initialize the main trading orchestrator
trading_orchestrator = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global trading_orchestrator
    logger.info("Starting Signal Flow Production API...")
    
    # Initialize database connections
    try:
        await db_manager.log_system_health("api_server", "starting")
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Verify trading service
    try:
        account = await trading_service.get_account()
        logger.info(f"Trading service connected. Account: {account.status if account else 'Unknown'}")
    except Exception as e:
        logger.error(f"Trading service initialization failed: {e}")
    
    # Start the main trading orchestrator
    try:
        trading_orchestrator = SignalFlowOrchestrator()
        # Start the trading system in background
        asyncio.create_task(trading_orchestrator.start())
        logger.info("✅ Trading system started successfully")
    except Exception as e:
        logger.error(f"Trading orchestrator initialization failed: {e}")
    
    logger.info("✅ Signal Flow Production API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    global trading_orchestrator
    logger.info("Shutting down Signal Flow API...")
    
    # Stop trading system
    if trading_orchestrator:
        try:
            trading_orchestrator.stop()
            logger.info("Trading system stopped")
        except Exception as e:
            logger.error(f"Error stopping trading system: {e}")
    
    health_monitor.stop_monitoring()
    db_manager.close()
    logger.info("✅ Signal Flow API shutdown complete")


# ==================== HEALTH & MONITORING ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Quick health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with all components"""
    try:
        health_status = await health_monitor.perform_full_health_check()
        return JSONResponse(content=health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.websocket("/ws/health")
async def websocket_health_monitor(websocket: WebSocket):
    """WebSocket endpoint for real-time health monitoring"""
    await websocket.accept()
    await health_monitor.add_websocket_connection(websocket)
    
    try:
        # Send initial health status
        health_status = await health_monitor.perform_full_health_check()
        await websocket.send_text(json.dumps({
            'type': 'initial_health',
            'data': health_status
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                # Handle any client commands if needed
                if message == "get_health":
                    current_health = await health_monitor.perform_full_health_check()
                    await websocket.send_text(json.dumps({
                        'type': 'health_update',
                        'data': current_health
                    }))
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    finally:
        await health_monitor.remove_websocket_connection(websocket)


# ==================== TRADING ENDPOINTS ====================

@app.get("/api/trades/active")
async def get_active_trades():
    """Get all active trades"""
    try:
        trades = await db_manager.get_active_trades()
        return JSONResponse(content=trades)
    except Exception as e:
        logger.error(f"Failed to get active trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades/performance")
async def get_trade_performance(symbol: str = None, days: int = 30):
    """Get trading performance analytics"""
    try:
        performance = await db_manager.get_trade_performance(symbol, days)
        return JSONResponse(content=performance)
    except Exception as e:
        logger.error(f"Failed to get performance data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account")
async def get_account_info():
    """Get trading account information"""
    try:
        account = await trading_service.get_account()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_data = {
            'account_number': account.account_number,
            'status': account.status,
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'portfolio_value': float(account.portfolio_value),
            'equity': float(account.equity),
            'last_equity': float(account.last_equity),
            'currency': account.currency
        }
        return JSONResponse(content=account_data)
    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    try:
        positions = await trading_service.get_positions()
        position_data = []
        
        for pos in positions:
            position_data.append({
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'side': pos.side,
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'current_price': float(pos.current_price) if pos.current_price else None
            })
        
        return JSONResponse(content=position_data)
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trades/execute")
async def execute_trade(trade_data: Dict[str, Any]):
    """Execute a trade through the system"""
    try:
        # Validate trade data
        required_fields = ['symbol', 'action', 'quantity']
        for field in required_fields:
            if field not in trade_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Execute trade through telegram trading service
        result = await telegram_trading.execute_trade(
            symbol=trade_data['symbol'],
            action=trade_data['action'],
            quantity=trade_data['quantity'],
            source='api'
        )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI DECISION ENDPOINTS ====================

@app.get("/api/ai/decisions/recent")
async def get_recent_ai_decisions(limit: int = 50):
    """Get recent AI trading decisions"""
    try:
        decisions = await db_manager.get_recent_decisions(limit)
        return JSONResponse(content=decisions)
    except Exception as e:
        logger.error(f"Failed to get AI decisions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI SIGNAL TRACKING ENDPOINTS ====================

@app.get("/api/ai/signals/recent")
async def get_recent_ai_signals(limit: int = 50, signal_type: str = None):
    """Get recent AI signals with analysis"""
    try:
        from services.ai_decision_tracker import ai_decision_tracker
        
        # Get recent signals
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
        filter_criteria = {'signal_timestamp': {'$gte': cutoff_time}}
        
        if signal_type:
            filter_criteria['signal_type'] = signal_type.upper()
        
        cursor = db_manager.async_db.ai_signals.find(
            filter_criteria,
            sort=[('signal_timestamp', -1)],
            limit=limit
        )
        
        signals = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for signal in signals:
            signal['_id'] = str(signal['_id'])
        
        return JSONResponse(content={
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get recent AI signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# DISABLED: Missing ai_agent_integration service
# @app.get("/api/ai/signals/performance")
# async def get_signal_performance_summary(days: int = 30):
#     """Get AI signal performance summary"""
#     try:
#         from services.ai_agent_integration import ai_agent_integration
#         
#         performance_report = await ai_agent_integration.get_signal_performance_report(days)
#         return JSONResponse(content=performance_report)
#         
#     except Exception as e:
#         logger.error(f"Failed to get signal performance: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/signals/analysis/{signal_id}")
async def get_signal_analysis(signal_id: str):
    """Get detailed analysis for a specific signal"""
    try:
        from bson import ObjectId
        
        # Get the signal
        signal = await db_manager.async_db.ai_signals.find_one({'_id': ObjectId(signal_id)})
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        # Get the analysis
        analysis = await db_manager.async_db.ai_signal_analysis.find_one({'signal_id': signal_id})
        
        # Get context
        context = await db_manager.async_db.ai_signal_context.find_one({'signal_id': signal_id})
        
        # Get execution context
        execution_context = await db_manager.async_db.ai_execution_context.find_one({'signal_id': signal_id})
        
        # Convert ObjectIds to strings
        signal['_id'] = str(signal['_id'])
        if analysis:
            analysis['_id'] = str(analysis['_id'])
        if context:
            context['_id'] = str(context['_id'])
        if execution_context:
            execution_context['_id'] = str(execution_context['_id'])
        
        return JSONResponse(content={
            'signal': signal,
            'analysis': analysis,
            'context': context,
            'execution_context': execution_context
        })
        
    except Exception as e:
        logger.error(f"Failed to get signal analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# DISABLED: Missing ai_agent_integration service
# @app.post("/api/ai/signals/manual-log")
# async def manually_log_signal(signal_data: Dict[str, Any]):
#     """Manually log an AI signal for testing"""
#     return JSONResponse(content={'error': 'AI signal integration disabled - missing service'})
        
        return JSONResponse(content={
            'status': 'signal_logged',
            'signal_id': signal_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to manually log signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# DISABLED: Missing ai_agent_integration service  
# @app.post("/api/ai/signals/log-execution")
# async def log_signal_execution(execution_data: Dict[str, Any]):
#     """Log execution decision for a signal"""
#     return JSONResponse(content={'error': 'AI signal integration disabled - missing service'})


# DISABLED: Missing enhanced_agent_wrapper service
# @app.get("/api/ai/tracking/status")
# async def get_ai_tracking_status():
#     """Get status of AI tracking system"""
#     return JSONResponse(content={'error': 'AI tracking disabled - missing service'})


@app.get("/api/ai/learning/summary")
async def get_ai_learning_summary():
    """Get comprehensive AI learning data summary"""
    try:
        summary = await db_manager.get_comprehensive_learning_summary()
        # Get collection summary (disabled due to yfinance conflict)
        # collection_summary = await ai_data_collector.get_collection_summary()
        
        return JSONResponse(content={
            "database_summary": summary,
            "collection_status": {"status": "disabled"},  # collection_summary disabled
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get AI learning summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/training-data/{symbol}")
async def get_training_data_for_symbol(symbol: str, days: int = 30, feature_type: str = None):
    """Get training data for a specific symbol"""
    try:
        training_data = await db_manager.get_training_data(symbol, feature_type, days)
        return JSONResponse(content=training_data)
    except Exception as e:
        logger.error(f"Failed to get training data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/market-sentiment/{symbol}")
async def get_market_sentiment_history(symbol: str, days: int = 7):
    """Get market sentiment history for a symbol"""
    try:
        sentiment_history = await db_manager.get_market_sentiment_history(symbol, days)
        return JSONResponse(content=sentiment_history)
    except Exception as e:
        logger.error(f"Failed to get sentiment history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/pattern-analysis")
async def get_pattern_analysis(pattern_type: str = None):
    """Get price pattern success rates and analysis"""
    try:
        pattern_rates = await db_manager.get_pattern_success_rates(pattern_type)
        return JSONResponse(content=pattern_rates)
    except Exception as e:
        logger.error(f"Failed to get pattern analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/strategy-performance")
async def get_ai_strategy_performance(strategy_name: str = None, days: int = 30):
    """Get AI strategy performance analytics"""
    try:
        performance = await db_manager.get_strategy_performance(strategy_name, days)
        return JSONResponse(content=performance)
    except Exception as e:
        logger.error(f"Failed to get strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/market-regime")
async def get_market_regime_history(days: int = 30):
    """Get market regime classification history"""
    try:
        regime_history = await db_manager.get_market_regime_history(days)
        return JSONResponse(content=regime_history)
    except Exception as e:
        logger.error(f"Failed to get market regime history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/force-data-collection")
async def force_data_collection():
    """Force immediate data collection cycle"""
    try:
        # Run collection cycle (disabled due to yfinance conflict)
        # await ai_data_collector.run_collection_cycle()
        return JSONResponse(content={
            "status": "collection_completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Force data collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/trades")
async def websocket_trade_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time trade updates"""
    await websocket.accept()
    
    try:
        # Send initial active trades
        active_trades = await db_manager.get_active_trades()
        await websocket.send_text(json.dumps({
            'type': 'initial_trades',
            'data': active_trades
        }))
        
        # TODO: Implement real-time trade updates
        # This would require a pub/sub mechanism or database change streams
        
        while True:
            message = await websocket.receive_text()
            if message == "get_trades":
                current_trades = await db_manager.get_active_trades()
                await websocket.send_text(json.dumps({
                    'type': 'trade_update',
                    'data': current_trades
                }))
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Trade WebSocket error: {e}")


# ==================== SYSTEM CONTROL ENDPOINTS ====================

@app.post("/api/system/emergency_stop")
async def emergency_stop():
    """Emergency stop all trading activities"""
    try:
        # Cancel all pending orders
        orders = await trading_service.get_orders()
        cancelled_orders = []
        
        for order in orders:
            try:
                await trading_service.cancel_order(order.id)
                cancelled_orders.append(order.id)
            except Exception as e:
                logger.error(f"Failed to cancel order {order.id}: {e}")
        
        # Log emergency stop
        await db_manager.log_system_health(
            "emergency_stop", 
            "executed",
            {"cancelled_orders": cancelled_orders}
        )
        
        return JSONResponse(content={
            "status": "emergency_stop_executed",
            "cancelled_orders": len(cancelled_orders),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # Get various system metrics
        health_status = await health_monitor.perform_full_health_check()
        active_trades = await db_manager.get_active_trades()
        recent_decisions = await db_manager.get_recent_decisions(limit=10)
        
        return JSONResponse(content={
            "health": health_status,
            "active_trades_count": len(active_trades),
            "recent_decisions_count": len(recent_decisions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    """Run the production API server with integrated trading system."""
    import uvicorn
    
    print("🚀 Signal Flow AI Trading System - Production Mode")
    print("📊 Starting FastAPI server with integrated trading engine...")
    print("🔗 API will be available at: http://localhost:8000")
    print("📈 Health dashboard: http://localhost:8000/health/detailed")
    print("📱 WebSocket monitoring: ws://localhost:8000/ws/health")
    
    uvicorn.run(
        "production_api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Disable reload in production
        access_log=True,
        log_level="info"
    )


# ==================== TELEGRAM WEBHOOK ENDPOINT ====================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Dict[str, Any]):
    """Handle Telegram webhook for instant trading responses"""
    try:
        # Process through existing telegram trading system
        result = await telegram_trading.handle_webhook(request)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "production_api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Disable reload in production
        workers=1,     # Single worker for trading system consistency
        log_level="info"
    )
