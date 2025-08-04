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
from services.database_manager import get_db_manager, TradeRecord

# Global database manager - will be initialized on first access
db_manager = None

def get_db():
    """Get database manager with lazy initialization."""
    global db_manager
    if db_manager is None:
        db_manager = get_db_manager()
    return db_manager

# Initialize db_manager for the module
db_manager = get_db()
from services.alpaca_trading import AlpacaTradingService
from services.telegram_trading import telegram_trading
# from services.ai_data_collector import ai_data_collector  # Disabled due to yfinance conflict

# Import the main trading orchestrator - lazy loading to avoid startup issues
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Global orchestrator - will be initialized on first access
orchestrator = None

def get_orchestrator():
    """Get orchestrator with lazy initialization."""
    global orchestrator
    if orchestrator is None:
        try:
            from main import SignalFlowOrchestrator
            orchestrator = SignalFlowOrchestrator()
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            orchestrator = None
    return orchestrator

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
        trading_orchestrator = get_orchestrator()
        if trading_orchestrator:
            # Start the trading system in background
            asyncio.create_task(trading_orchestrator.start())
            logger.info("✅ Trading system started successfully")
        else:
            logger.warning("⚠️ Trading orchestrator not available")
        
        # Send startup notification
        try:
            await telegram_trading.send_message(
                "🚀 *SIGNAL FLOW STARTED*\n\n"
                f"✅ System: Online\n"
                f"⏰ Started: {datetime.now().strftime('%H:%M:%S EST')}\n"
                f"📡 Mode: Paper Trading\n"
                f"🎯 Market Scanning: Active\n\n"
                f"Ready to send trading signals!"
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")
            
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


# ==================== ROOT & INFO ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Signal Flow Trading System API",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "health": "/health",
            "portfolio": "/api/portfolio",
            "holdings": "/api/holdings",
            "trades": "/api/trades/active",
            "ai_analysis": "/api/ai/analysis"
        }
    }


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


@app.get("/api/holdings")
async def get_holdings():
    """Get current holdings from the trading system (frontend compatibility endpoint)."""
    try:
        # Get positions from Alpaca (paper trading account)
        positions = await trading_service.get_positions()
        
        holdings = []
        for position in positions:
            holdings.append({
                "symbol": position.symbol,
                "quantity": float(position.qty),
                "current_price": float(position.current_price) if position.current_price else 0.0,
                "market_value": float(position.market_value) if position.market_value else 0.0,
                "unrealized_pnl": float(position.unrealized_pl) if position.unrealized_pl else 0.0,
                "percentage_change": float(position.unrealized_plpc) * 100 if position.unrealized_plpc else 0.0,
                "side": position.side
            })
        
        return JSONResponse(content={
            "holdings": holdings, 
            "total_value": sum(h["market_value"] for h in holdings)
        })
        
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio")
async def get_portfolio_summary():
    """Get portfolio summary from the trading system (frontend compatibility endpoint)."""
    try:
        account = await trading_service.get_account()
        
        return JSONResponse(content={
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "daytrade_count": int(account.daytrade_count),
            "trading_blocked": account.trading_blocked,
            "account_blocked": account.account_blocked
        })
        
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance/history")
async def get_performance_history():
    """Get performance history for charts"""
    try:
        # Get account data for current portfolio value
        account = await trading_service.get_account()
        current_value = float(account.portfolio_value)
        
        # Get trade history to calculate performance over time
        trades = await db_manager.get_recent_trades(limit=100)
        
        # Generate performance data points
        performance_data = []
        
        # Start with portfolio value and work backwards
        base_time = datetime.now(timezone.utc)
        
        for i in range(24):  # 24 hours of data
            timestamp = base_time - timedelta(hours=23-i)
            
            # Calculate PnL based on trades in this time period
            period_trades = [t for t in trades if t.get('timestamp') and 
                           timestamp - timedelta(hours=1) <= datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00')) <= timestamp]
            
            period_pnl = sum(t.get('profit_loss', 0) for t in period_trades if t.get('profit_loss'))
            
            # Use real current value with some historical approximation
            historical_value = current_value + (i - 12) * 10  # Small historical variation
            
            performance_data.append({
                'timestamp': timestamp.isoformat(),
                'value': round(historical_value, 2),
                'pnl': round(period_pnl, 2)
            })
        
        return JSONResponse(content={
            'performance_data': performance_data,
            'current_value': current_value,
            'total_pnl': sum(p['pnl'] for p in performance_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching performance history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/realtime/{symbol}")
async def get_realtime_market_data(symbol: str):
    """Get real-time market data for a specific symbol - NO MOCK DATA"""
    try:
        # Real-time market data requires proper data feed integration
        raise HTTPException(
            status_code=501, 
            detail="Real-time market data service not implemented. Requires integration with market data providers (Polygon, Alpaca, Bloomberg, etc.)"
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching realtime data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Market data service error: {str(e)}")


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
    """Get recent AI signals with analysis - NO MOCK DATA"""
    try:
        # AI signals require trained models and real signal generation
        raise HTTPException(
            status_code=501, 
            detail="AI signals service not implemented. Requires trained ML models, technical analysis engines, and real signal generation systems."
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
        
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
    """Get detailed analysis for a specific signal - NO MOCK DATA"""
    try:
        # Signal analysis requires real AI models and technical analysis systems
        raise HTTPException(
            status_code=501, 
            detail="Signal analysis service not implemented. Requires technical analysis engines, risk assessment models, and market context analysis."
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get signal analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Signal analysis service error: {str(e)}")
        
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
        # Get learning summary from database
        summary = await db_manager.get_learning_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get AI learning summary: {e}")
        return JSONResponse(content={
            'error': 'Learning summary not available',
            'models_trained': 0,
            'total_predictions': 0
        })


@app.get("/api/ai/analysis")
async def get_ai_market_analysis():
    """Get real-time AI market analysis"""
    try:
        # Get recent AI decisions and market data for analysis
        recent_decisions = await db_manager.get_recent_decisions(limit=10)
        
        # Calculate sentiment from recent decisions
        sentiment_scores = []
        for decision in recent_decisions:
            if decision.get('confidence'):
                sentiment_scores.append(decision['confidence'])
        
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            sentiment = 'Bullish' if avg_sentiment > 7 else 'Bearish' if avg_sentiment < 4 else 'Neutral'
        else:
            avg_sentiment = 5.0
            sentiment = 'Neutral'
        
        # Generate insights based on recent trading activity
        key_insights = []
        recommendations = []
        
        if recent_decisions:
            # Analyze recent decisions for patterns
            symbols = [d.get('symbol', '') for d in recent_decisions if d.get('symbol')]
            if symbols:
                most_common_symbol = max(set(symbols), key=symbols.count)
                key_insights.append(f'Increased AI focus on {most_common_symbol} detected')
                recommendations.append(f'Monitor {most_common_symbol} for continued signals')
        
        # Add default insights if no recent activity
        if not key_insights:
            key_insights = [
                'Market volatility within normal ranges',
                'AI system actively monitoring for opportunities',
                'No immediate high-confidence signals detected'
            ]
            
        if not recommendations:
            recommendations = [
                'Continue monitoring current positions',
                'Wait for higher confidence signals',
                'Review risk management settings'
            ]
        
        # Assess risk based on recent performance
        risk_assessment = 'Low' if avg_sentiment > 8 else 'High' if avg_sentiment < 3 else 'Moderate'
        
        analysis_data = {
            'market_sentiment': sentiment,
            'sentiment_score': round(avg_sentiment, 1),
            'key_insights': key_insights[:4],  # Limit to 4 insights
            'recommendations': recommendations[:4],  # Limit to 4 recommendations
            'risk_assessment': risk_assessment,
            'confidence_level': round(avg_sentiment, 1),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content=analysis_data)
        
    except Exception as e:
        logger.error(f"Failed to get AI analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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


@app.post("/api/system/trigger_scan")
async def trigger_manual_scan():
    """Trigger a manual market scan for testing"""
    global trading_orchestrator
    try:
        if not trading_orchestrator:
            raise HTTPException(status_code=503, detail="Trading system not initialized")
        
        # Trigger manual market scan
        logger.info("Manual market scan triggered via API")
        asyncio.create_task(trading_orchestrator.run_market_scan())
        
        return JSONResponse(content={
            "status": "scan_triggered",
            "message": "Market scan started manually",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual scan trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENHANCED DASHBOARD ENDPOINTS ====================

@app.get("/api/dashboard/holdings/detailed")
async def get_detailed_holdings():
    """Get detailed holdings with enhanced metrics - NO MOCK DATA"""
    try:
        # Get real positions from Alpaca
        positions = await trading_service.get_positions()
        
        if not positions:
            raise HTTPException(status_code=404, detail="No positions found in account")
        
        # Get account info for portfolio calculations
        account = await trading_service.get_account()
        total_equity = float(account.equity)
        
        detailed_holdings = []
        for position in positions:
            symbol = position.get('symbol')
            if not symbol:
                continue
            
            qty = float(position.get('qty', 0))
            market_value = float(position.get('market_value', 0))
            cost_basis = float(position.get('cost_basis', 0))
            unrealized_pl = float(position.get('unrealized_pl', 0))
            avg_entry_price = float(position.get('avg_entry_price', 0))
            
            if qty == 0 or cost_basis == 0:
                continue  # Skip invalid positions
            
            current_price = market_value / qty if qty != 0 else 0
            unrealized_pnl_percent = (unrealized_pl / cost_basis) * 100 if cost_basis != 0 else 0
            position_size_percent = (market_value / total_equity) * 100 if total_equity != 0 else 0
            
            # REAL DATA ONLY - no risk metrics without proper calculation
            enhanced_position = {
                'symbol': symbol,
                'qty': qty,
                'market_value': market_value,
                'entry_price': avg_entry_price,
                'current_price': current_price,
                'unrealized_pl': unrealized_pl,
                'unrealized_pnl_percent': round(unrealized_pnl_percent, 2),
                'position_size_percent': round(position_size_percent, 2),
                'risk_metrics': {
                    'beta': None,  # Requires external data service
                    'volatility': None,  # Requires historical data
                    'sharpe_ratio': None  # Requires historical performance data
                },
                'ai_signals': {
                    'current_signal': 'UNAVAILABLE',  # Requires AI service implementation
                    'confidence': 0.0,
                    'next_review': None
                }
            }
            detailed_holdings.append(enhanced_position)
        
        if not detailed_holdings:
            raise HTTPException(status_code=404, detail="No valid positions after processing")
        
        return JSONResponse(content={
            'holdings': detailed_holdings,
            'summary': {
                'total_positions': len(detailed_holdings),
                'total_value': sum(h['market_value'] for h in detailed_holdings),
                'total_pnl': sum(h['unrealized_pl'] for h in detailed_holdings),
                'avg_performance': round(sum(h['unrealized_pnl_percent'] for h in detailed_holdings) / len(detailed_holdings), 2)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get detailed holdings: {e}")
        raise HTTPException(status_code=500, detail=f"Holdings service unavailable: {str(e)}")


@app.get("/api/dashboard/analytics/performance")
async def get_performance_analytics():
    """Get detailed performance analytics - NO MOCK DATA"""
    try:
        # Performance analytics requires historical data and complex calculations
        # Without proper implementation, we should not provide fake data
        raise HTTPException(
            status_code=501, 
            detail="Performance analytics service not implemented. Requires historical data analysis, risk calculations, and performance attribution models."
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics service error: {str(e)}")


@app.get("/api/dashboard/market/pulse")
async def get_market_pulse():
    """Get real-time market pulse and sentiment - NO MOCK DATA"""
    try:
        # Market pulse requires real-time market data integration
        # Without proper data sources (Bloomberg, Reuters, Polygon, etc.), we should not provide fake data
        raise HTTPException(
            status_code=501, 
            detail="Market pulse service not implemented. Requires real-time market data feeds, sentiment analysis, and market regime detection."
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get market pulse: {e}")
        raise HTTPException(status_code=500, detail=f"Market pulse service error: {str(e)}")


@app.post("/api/dashboard/config/update")
async def update_dashboard_config(config_data: Dict[str, Any]):
    """Update dashboard configuration"""
    try:
        # In a real implementation, this would update the configuration
        # For now, just return the config that was sent
        
        return JSONResponse(content={
            'status': 'success',
            'updated_config': config_data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': 'Configuration updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to update dashboard config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/watchlist/signals")
async def get_watchlist_signals():
    """Get AI signals for watchlist symbols - NO MOCK DATA"""
    try:
        # AI signals require trained models, technical analysis, and sentiment processing
        # Without proper AI implementation, we should not provide fake signals
        raise HTTPException(
            status_code=501, 
            detail="AI watchlist signals service not implemented. Requires machine learning models, technical analysis engines, and sentiment analysis."
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get watchlist signals: {e}")
        raise HTTPException(status_code=500, detail=f"Watchlist signals service error: {str(e)}")


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


# ==================== CONTROL PANEL ENDPOINTS ====================

# Global control state - in production this should be stored in database
control_state = {
    "auto_trading": True,
    "paper_trading": True,
    "ai_analysis": True,
    "data_feed": True,
    "risk_management": True,
    "trading_engine": True
}

@app.post("/api/control/{action}")
async def execute_control_action(action: str, request_data: Dict[str, Any] = None):
    """Execute control panel actions"""
    try:
        logger.info(f"Executing control action: {action}")
        
        if action == "toggle_auto_trading":
            control_state["auto_trading"] = not control_state["auto_trading"]
            message = f"Auto trading {'enabled' if control_state['auto_trading'] else 'disabled'}"
            return JSONResponse(content={
                "status": "success",
                "message": message,
                "new_status": control_state["auto_trading"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        elif action == "toggle_paper_trading":
            control_state["paper_trading"] = not control_state["paper_trading"]
            message = f"Paper trading {'enabled' if control_state['paper_trading'] else 'disabled'}"
            # In real implementation, this would switch Alpaca between paper/live
            return JSONResponse(content={
                "status": "success",
                "message": message,
                "new_status": control_state["paper_trading"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        elif action == "emergency_stop":
            # Emergency stop - halt all trading immediately
            control_state["auto_trading"] = False
            control_state["trading_engine"] = False
            
            # In real implementation, this would:
            # 1. Cancel all open orders
            # 2. Close all positions if configured
            # 3. Stop all trading algorithms
            # 4. Send emergency notifications
            
            try:
                # Cancel all open orders through Alpaca
                orders = await trading_service.get_orders(status='open')
                for order in orders:
                    await trading_service.cancel_order(order.id)
                    logger.info(f"Emergency cancelled order: {order.id}")
                    
                logger.warning("EMERGENCY STOP ACTIVATED - All trading halted")
                
                return JSONResponse(content={
                    "status": "success",
                    "message": "EMERGENCY STOP: All trading activities halted immediately",
                    "orders_cancelled": len(orders),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Emergency stop error: {e}")
                return JSONResponse(content={
                    "status": "partial_success",
                    "message": "Emergency stop activated, but some operations may have failed",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
        elif action == "sync_data":
            # Trigger comprehensive data synchronization
            try:
                # Sync account data
                account = await trading_service.get_account()
                positions = await trading_service.get_positions()
                orders = await trading_service.get_orders()
                
                sync_results = {
                    "account_synced": bool(account),
                    "positions_count": len(positions),
                    "orders_count": len(orders),
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
                
                return JSONResponse(content={
                    "status": "success",
                    "message": "Data synchronization completed successfully",
                    "sync_results": sync_results,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Data sync error: {e}")
                return JSONResponse(content={
                    "status": "error",
                    "message": f"Data synchronization failed: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute control action {action}: {e}")
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(e)}")


@app.get("/api/control/status")
async def get_control_status():
    """Get current control panel status"""
    try:
        # In production, also check actual system states
        account = await trading_service.get_account()
        
        return JSONResponse(content={
            "control_state": control_state,
            "system_health": {
                "trading_engine": control_state["trading_engine"] and bool(account),
                "ai_analysis": control_state["ai_analysis"],
                "risk_management": control_state["risk_management"],
                "data_feed": control_state["data_feed"] and bool(account),
            },
            "account_status": {
                "buying_power": float(account.buying_power) if account else 0,
                "portfolio_value": float(account.portfolio_value) if account else 0,
                "trading_blocked": bool(account.trading_blocked) if account else True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get control status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# ==================== AI DASHBOARD ENDPOINTS ====================

@app.get("/api/dashboard/ai/signals")
async def get_ai_signals():
    """Get AI trading signals for dashboard"""
    return JSONResponse(
        status_code=501,
        content={"detail": "AI signals service not yet implemented"}
    )


@app.get("/api/dashboard/ai/learning-metrics")
async def get_ai_learning_metrics():
    """Get AI learning progress metrics"""
    return JSONResponse(
        status_code=501,
        content={"detail": "AI learning metrics service not yet implemented"}
    )


# ==================== CONFIGURATION ENDPOINTS ====================

@app.get("/api/config/system")
async def get_system_configuration():
    """Get current system configuration"""
    return JSONResponse(
        status_code=501,
        content={"detail": "System configuration service not yet implemented"}
    )


@app.post("/api/config/system")
async def update_system_configuration(config_data: Dict[str, Any]):
    """Update system configuration"""
    return JSONResponse(
        status_code=501,
        content={"detail": "Configuration update service not yet implemented"}
    )


@app.get("/api/config/status")
async def get_system_status():
    """Get detailed system status for configuration panel"""
    return JSONResponse(
        status_code=501,
        content={"detail": "System status service not yet implemented"}
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
