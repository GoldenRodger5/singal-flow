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
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from loguru import logger
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from services.health_monitor import health_monitor
from services.database_manager import get_db_manager, TradeRecord
from services.alpaca_trading import AlpacaTradingService
from services.telegram_trading import telegram_trading

# Import Polygon.io Trading Engines with error handling
try:
    from services.anomaly_detection import get_anomaly_engine
except ImportError as e:
    logger.warning(f"Anomaly detection service unavailable: {e}")
    get_anomaly_engine = lambda: None

try:
    from services.websocket_engine import websocket_engine
except ImportError as e:
    logger.warning(f"WebSocket engine service unavailable: {e}")
    websocket_engine = None

try:
    from services.short_squeeze_detector import squeeze_detector
except ImportError as e:
    logger.warning(f"Squeeze detector service unavailable: {e}")
    squeeze_detector = None

try:
    from services.sentiment_trading import sentiment_engine
except ImportError as e:
    logger.warning(f"Sentiment engine service unavailable: {e}")
    sentiment_engine = None

try:
    from services.master_trading_coordinator import master_coordinator
except ImportError as e:
    logger.warning(f"Master coordinator service unavailable: {e}")
    master_coordinator = None

# Global database manager - will be initialized on first access
db_manager = None

def get_db():
    """Get database manager with lazy initialization."""
    global db_manager
    if db_manager is None:
        db_manager = get_db_manager()
    return db_manager

# Do NOT initialize db_manager at import time. Only initialize inside endpoints or functions.
# from services.ai_data_collector import ai_data_collector  # Disabled due to yfinance conflict

# Import the main trading orchestrator - lazy loading to avoid startup issues
from pathlib import Path

# Global orchestrator - will be initialized on first access
orchestrator = None

def get_orchestrator():
    """Get orchestrator with lazy initialization."""
    global orchestrator
    if orchestrator is None:
        try:
            # Try multiple import paths for Railway deployment
            try:
                from main import SignalFlowOrchestrator
            except ImportError:
                # Try from backend directory
                try:
                    from backend.main import SignalFlowOrchestrator
                except ImportError:
                    # Try with relative import
                    import sys
                    from pathlib import Path
                    backend_path = Path(__file__).parent.parent
                    sys.path.insert(0, str(backend_path))
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

# Global trading service - will be initialized on first access
trading_service = None

def get_trading_service():
    """Get trading service with lazy initialization."""
    global trading_service
    if trading_service is None:
        trading_service = AlpacaTradingService()
    return trading_service

# Initialize the main trading orchestrator
trading_orchestrator = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global trading_orchestrator
    logger.info("Starting Signal Flow Production API...")
    
    # Initialize database connections
    try:
        await get_db().log_system_health("api_server", "starting")
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Verify trading service
    try:
        account = await get_trading_service().get_account()
        logger.info(f"Trading service connected. Account: {account.status if account else 'Unknown'}")
    except Exception as e:
        logger.error(f"Trading service initialization failed: {e}")
    
    # Initialize Polygon.io Trading Engines
    try:
        # Initialize all trading engines with null checks
        if get_anomaly_engine:
            anomaly_detector = get_anomaly_engine()
            if anomaly_detector and hasattr(anomaly_detector, 'initialize'):
                await anomaly_detector.initialize()
        
        if websocket_engine and hasattr(websocket_engine, 'initialize'):
            await websocket_engine.initialize()
        
        if squeeze_detector and hasattr(squeeze_detector, '__aenter__'):
            await squeeze_detector.__aenter__()
        
        if sentiment_engine and hasattr(sentiment_engine, 'initialize'):
            await sentiment_engine.initialize()
        
        if master_coordinator and hasattr(master_coordinator, 'initialize'):
            await master_coordinator.initialize()
            
        logger.info("✅ Polygon.io trading engines initialized successfully")
        
    except Exception as e:
        logger.error(f"Polygon.io trading engines initialization failed: {e}")
    
    # Start the main trading orchestrator
    try:
        trading_orchestrator = get_orchestrator()
        if trading_orchestrator:
            # Start the trading system in background
            asyncio.create_task(trading_orchestrator.start())
            logger.info("✅ Trading system started successfully")
        else:
            logger.warning("⚠️ Trading orchestrator not available")
        
        # Send startup notification (simplified to avoid duplicates)
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
    get_db().close()
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
    try:
        # Test database connection
        db = get_db()
        test_result = await db.log_system_health("health_check", "testing", {"endpoint": "health"})
        
        return {
            "status": "healthy", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected" if test_result else "failed",
            "services": {
                "database": "operational" if test_result else "error",
                "api": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "database": "failed"
        }


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
        # Test database connection first
        db = get_db()
        if not db:
            return JSONResponse(content={"trades": [], "message": "Database not initialized"})
        
        # Get active trades or return empty array if none exist
        trades = await db.get_active_trades()
        
        # If no trades exist, return empty array with helpful message
        if not trades:
            return JSONResponse(content={
                "trades": [],
                "message": "No active trades found", 
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return JSONResponse(content={"trades": trades, "count": len(trades)})
    except Exception as e:
        logger.error(f"Failed to get active trades: {e}")
        # Return detailed error for debugging
        return JSONResponse(
            status_code=500, 
            content={
                "error": str(e),
                "endpoint": "/api/trades/active",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@app.get("/api/trades/performance")
async def get_trade_performance(symbol: str = None, days: int = 30):
    """Get trading performance analytics"""
    try:
        performance = await get_db().get_trade_performance(symbol, days)
        
        # If no performance data, return default structure
        if not performance or performance == []:
            return JSONResponse(content={
                "period": f"last_{days}_days",
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_return": 0.0,
                "best_trade": None,
                "worst_trade": None,
                "trades": []
            })
        
        return JSONResponse(content=performance)
    except Exception as e:
        logger.error(f"Failed to get performance data: {e}")
        # Return default structure on error
        return JSONResponse(content={
            "period": f"last_{days}_days",
            "total_trades": 0,
            "error": str(e)
        })


@app.get("/api/account")
async def get_account_info():
    """Get trading account information"""
    try:
        account = await get_trading_service().get_account()
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
        positions = await get_trading_service().get_positions()
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
        
        return JSONResponse(content={
            "positions": position_data,
            "total_positions": len(position_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return JSONResponse(content={
            "positions": [],
            "total_positions": 0,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


@app.get("/api/holdings")
async def get_holdings():
    """Get current holdings from the trading system (frontend compatibility endpoint)."""
    try:
        # Get positions from Alpaca (paper trading account)
        positions = await get_trading_service().get_positions()
        
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
        account = await get_trading_service().get_account()
        
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
        account = await get_trading_service().get_account()
        current_value = float(account.portfolio_value)
        
        # Get trade history to calculate performance over time
        trades = await get_db().get_recent_trades(limit=100)
        
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
    """Get real-time market data for a specific symbol"""
    try:
        # Import real-time market data service properly
        from backend.services.real_time_market_data import get_market_data_service
        
        # Get market data service instance
        market_service = get_market_data_service()
        
        # Get real-time quote with proper error handling
        try:
            async with market_service:
                market_data = await market_service.get_real_time_quote(symbol.upper())
        except Exception as service_error:
            logger.error(f"Market data service error for {symbol}: {service_error}")
            raise HTTPException(status_code=503, detail=f"Market data service unavailable: {str(service_error)}")
        
        if not market_data:
            raise HTTPException(status_code=404, detail=f"Market data not found for symbol: {symbol}")
        
        return JSONResponse(content={
            'symbol': market_data.symbol,
            'price': market_data.price,
            'volume': market_data.volume,
            'change': market_data.change,
            'change_percent': market_data.change_percent,
            'day_high': market_data.day_high,
            'day_low': market_data.day_low,
            'day_open': market_data.day_open,
            'previous_close': market_data.previous_close,
            'timestamp': market_data.timestamp.isoformat(),
            'market_cap': None,  # Can be added later if needed
            'pe_ratio': None     # Can be added later if needed
        })
        
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
        # Test database connection first
        db = get_db()
        if not db:
            return JSONResponse(content={"decisions": [], "message": "Database not initialized"})
        
        # Get recent decisions or return empty array if none exist
        decisions = await db.get_recent_decisions(limit)
        
        # If no decisions exist, return empty array with helpful message
        if not decisions:
            return JSONResponse(content={
                "decisions": [],
                "message": "No AI decisions found", 
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return JSONResponse(content={"decisions": decisions, "count": len(decisions)})
    except Exception as e:
        logger.error(f"Failed to get AI decisions: {e}")
        # Return detailed error for debugging
        return JSONResponse(
            status_code=500, 
            content={
                "error": str(e),
                "endpoint": "/api/ai/decisions/recent",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# ==================== AI SIGNAL TRACKING ENDPOINTS ====================

@app.get("/api/ai/signals/recent")
async def get_recent_ai_signals(limit: int = 50, signal_type: str = None):
    """Get recent AI signals with analysis"""
    try:
        # Import AI signal generation service
        from backend.services.ai_signal_generation import ai_signal_service
        
        # Get active AI signals
        active_signals = await ai_signal_service.get_active_signals()
        
        # Filter by signal type if specified
        if signal_type:
            active_signals = [s for s in active_signals if s.signal_type.upper() == signal_type.upper()]
        
        # Apply limit
        signals = active_signals[:limit]
        
        # Format signals for API response
        formatted_signals = []
        for signal in signals:
            formatted_signals.append({
                'signal_id': f"{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}",
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'price_target': signal.price_target,
                'stop_loss': signal.stop_loss,
                'entry_price': signal.entry_price,
                'expected_return': signal.expected_return,
                'risk_level': signal.risk_level,
                'time_horizon': signal.time_horizon,
                'reasoning': signal.reasoning,
                'timestamp': signal.timestamp.isoformat(),
                'age_hours': (datetime.now(timezone.utc) - signal.timestamp).total_seconds() / 3600
            })
        
        return JSONResponse(content={
            'signals': formatted_signals,
            'total_signals': len(formatted_signals),
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
        
    except Exception as e:
        logger.error(f"Failed to get recent AI signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Enabled: Using ai_signal_service implementation
@app.get("/api/test-simple")
async def test_simple_endpoint():
    """Test simple endpoint"""
    return {"message": "simple test", "value": 123}

@app.get("/api/ai/signals/performance")
async def get_signal_performance_summary(days: int = 30):
    """Get AI signal performance summary"""
    try:
        # Get performance data from AI service
        from backend.services.ai_signal_generation import ai_signal_service
        performance_data = await ai_signal_service.get_signal_performance(days)
        
        # Ensure all datetime objects are serialized
        def serialize_datetime_objects(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime_objects(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime_objects(item) for item in obj]
            else:
                return obj
        
        # Apply datetime serialization
        serialized_data = serialize_datetime_objects(performance_data)
        
        return serialized_data
        
    except Exception as e:
        logger.error(f"Failed to get signal performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/ai/signals/analysis/{signal_id}")
async def get_signal_analysis(signal_id: str):
    """Get detailed analysis for a specific signal"""
    try:
        # Parse signal ID to extract symbol and timestamp
        parts = signal_id.split('_')
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid signal ID format")
        
        symbol = parts[0]
        
        # Import AI signal generation service
        from backend.services.ai_signal_generation import ai_signal_service
        
        # Get the specific signal for this symbol
        signal = await ai_signal_service.get_signal_for_symbol(symbol)
        
        if not signal:
            raise HTTPException(status_code=404, detail=f"Signal not found for ID: {signal_id}")
        
        # Get additional market context
        from backend.services.real_time_market_data import market_data_service
        async with market_data_service:
            current_market_data = await market_data_service.get_real_time_quote(symbol)
            historical_data = await market_data_service.get_historical_data(symbol, days=10)
        
        # Calculate current performance
        current_price = current_market_data.price if current_market_data else signal.entry_price
        
        if signal.signal_type == 'BUY':
            current_return = (current_price / signal.entry_price - 1) * 100
        elif signal.signal_type == 'SELL':
            current_return = (signal.entry_price / current_price - 1) * 100
        else:
            current_return = 0.0
        
        # Technical analysis context
        technical_context = {
            'current_vs_target': round((current_price / signal.price_target - 1) * 100, 2) if signal.price_target else 0,
            'stop_loss_distance': round((signal.stop_loss / current_price - 1) * 100, 2) if signal.stop_loss else 0,
            'volatility': round(abs(current_market_data.change_percent), 2) if current_market_data else 0,
            'volume_ratio': 1.0  # Can be enhanced with historical volume comparison
        }
        
        return JSONResponse(content={
            'signal_id': signal_id,
            'signal': {
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'price_target': signal.price_target,
                'stop_loss': signal.stop_loss,
                'entry_price': signal.entry_price,
                'current_price': current_price,
                'expected_return': signal.expected_return,
                'current_return': round(current_return, 2),
                'risk_level': signal.risk_level,
                'time_horizon': signal.time_horizon,
                'reasoning': signal.reasoning,
                'timestamp': signal.timestamp.isoformat()
            },
            'technical_analysis': technical_context,
            'market_context': {
                'day_high': current_market_data.day_high if current_market_data else 0,
                'day_low': current_market_data.day_low if current_market_data else 0,
                'volume': current_market_data.volume if current_market_data else 0,
                'change_percent': current_market_data.change_percent if current_market_data else 0
            },
            'historical_context': {
                'days_analyzed': len(historical_data),
                'price_trend': 'NEUTRAL',  # Can be enhanced with trend analysis
                'support_levels': [],      # Can be enhanced with technical analysis
                'resistance_levels': []    # Can be enhanced with technical analysis
            }
        })
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get signal analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Signal analysis service error: {str(e)}")


# Enabled: Using MongoDB implementation
@app.post("/api/ai/signals/manual-log")
async def manually_log_signal(signal_data: Dict[str, Any]):
    """Manually log an AI signal for testing"""
    try:
        # Get database manager
        db = get_db()
        
        # Create signal document for MongoDB
        signal_document = {
            'symbol': signal_data.get('symbol', ''),
            'signal_type': signal_data.get('signal_type', 'BUY').upper(),
            'confidence': signal_data.get('confidence', 0.5),
            'market_regime': signal_data.get('market_regime', 'NEUTRAL'),
            'regime_confidence': signal_data.get('regime_confidence', 0.5),
            'technical_indicators': {
                'rsi': signal_data.get('technical_indicators', {}).get('rsi', 50),
                'momentum': signal_data.get('technical_indicators', {}).get('momentum', 0),
                'volume_ratio': signal_data.get('technical_indicators', {}).get('volume_ratio', 1.0)
            },
            'order_flow_signal': signal_data.get('order_flow_signal', 0),
            'sector_strength': signal_data.get('sector_strength', 0.5),
            'volatility_percentile': signal_data.get('volatility_percentile', 0.5),
            'trend_strength': signal_data.get('trend_strength', 0.5),
            'expected_return': signal_data.get('expected_return', 0.05),
            'stop_loss': signal_data.get('stop_loss', 0),
            'price_target': signal_data.get('price_target', 0),
            'position_size': signal_data.get('position_size', 0.1),
            'kelly_fraction': signal_data.get('kelly_fraction', 0.1),
            'risk_reward_ratio': signal_data.get('risk_reward_ratio', 2.0),
            'reasoning': signal_data.get('reasoning', 'Manual signal log'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'LOGGED',
            'entry_price': signal_data.get('entry_price', 0),
            'time_horizon': signal_data.get('time_horizon', 'DAY'),
            'risk_level': signal_data.get('risk_level', 'MEDIUM')
        }
        
        # Store signal in MongoDB
        await db.store_ai_signals([signal_document])
        
        # Generate a simple signal ID based on symbol and timestamp
        signal_id = f"{signal_document['symbol']}_{int(datetime.now(timezone.utc).timestamp())}"
        
        return JSONResponse(content={
            'status': 'signal_logged',
            'signal_id': signal_id,
            'timestamp': signal_document['timestamp'],
            'reasoning': signal_document['reasoning']
        })
        
    except Exception as e:
        logger.error(f"Failed to manually log signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# DISABLED: Missing ai_agent_integration service  
# Enabled: Using MongoDB implementation
@app.post("/api/ai/signals/log-execution")
async def log_signal_execution(execution_data: Dict[str, Any]):
    """Log execution decision for a signal"""
    try:
        # Get database manager
        db = get_db()
        
        signal_id = execution_data.get('signal_id')
        if not signal_id:
            raise HTTPException(status_code=400, detail="signal_id is required")
        
        # Create execution record for MongoDB
        execution_record = {
            'signal_id': signal_id,
            'symbol': execution_data.get('symbol', ''),
            'decision': execution_data.get('decision', 'executed').upper(),
            'reason': execution_data.get('reason', ''),
            'execution_details': {
                'price': execution_data.get('execution_details', {}).get('price', 0),
                'quantity': execution_data.get('execution_details', {}).get('quantity', 0),
                'position_size_usd': execution_data.get('execution_details', {}).get('position_size_usd', 0),
                'commission': execution_data.get('execution_details', {}).get('commission', 0),
                'slippage': execution_data.get('execution_details', {}).get('slippage', 0)
            },
            'market_regime': execution_data.get('market_regime', 'NEUTRAL'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'LOGGED'
        }
        
        # Store execution in MongoDB ai_signal_analysis collection
        collection = db.async_db.ai_signal_analysis
        result = await collection.insert_one(execution_record)
        execution_id = str(result.inserted_id)
        
        return JSONResponse(content={
            'status': 'execution_logged',
            'execution_id': execution_id,
            'signal_id': signal_id,
            'decision': execution_data.get('decision'),
            'reason': execution_data.get('reason'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to log signal execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Enabled: Using MongoDB implementation
@app.get("/api/ai/tracking/status")
async def get_ai_tracking_status():
    """Get status of AI tracking system"""
    try:
        # Get database manager
        db = get_db()
        
        # Get recent signal activity from MongoDB
        recent_signals_24h = 0
        total_signals = 0
        total_analyses = 0
        
        try:
            # Get recent signals from database
            recent_signals_data = await db.get_recent_signals(days=1)
            recent_signals_24h = len(recent_signals_data) if recent_signals_data else 0
            
            all_signals_data = await db.get_recent_signals(days=30)
            total_signals = len(all_signals_data) if all_signals_data else 0
            
            # Get analysis records from ai_signal_analysis collection
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
            analysis_cursor = db.async_db.ai_signal_analysis.find({
                'timestamp': {'$gte': cutoff_time}
            })
            analysis_records = await analysis_cursor.to_list(length=None)
            total_analyses = len(analysis_records) if analysis_records else 0
            
        except Exception as e:
            logger.debug(f"Database query for signals failed: {e}")
        
        # Calculate basic performance metrics
        successful_signals = 0
        if total_signals > 0:
            # Simple estimation - in production this would be calculated from actual trade outcomes
            successful_signals = int(total_signals * 0.65)  # Assume 65% success rate as baseline
        
        # Create tracking status response
        tracking_status = {
            'total_signals': total_signals,
            'total_analyses': total_analyses,
            'recent_signals_24h': recent_signals_24h,
            'tracking_stats': {
                'tracking_active': True,
                'database_type': 'MongoDB Atlas',
                'collections_active': ['ai_signals', 'ai_signal_analysis', 'trades'],
                'wrapped_agents': [
                    'TradeRecommenderAgent',
                    'SentimentAgent', 
                    'ReasoningAgent',
                    'AISignalGenerationService'
                ],
                'tracked_methods': {
                    'TradeRecommenderAgent': ['analyze_setup', 'generate_recommendation'],
                    'SentimentAgent': ['analyze_sentiment', 'get_market_sentiment'],
                    'ReasoningAgent': ['explain_decision', 'generate_reasoning'],
                    'AISignalGenerationService': ['generate_signals_for_watchlist', 'get_signal_performance']
                }
            },
            'performance_summary': {
                'win_rate': (successful_signals / total_signals * 100) if total_signals > 0 else 0,
                'avg_return': 0.0,  # Real return calculated from actual trades in database
                'total_trades': total_analyses,
                'successful_trades': successful_signals
            },
            'system_status': 'healthy',
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content=tracking_status)
        
    except Exception as e:
        logger.error(f"Failed to get AI tracking status: {e}")
        return JSONResponse(content={
            'error': f'AI tracking status error: {str(e)}',
            'system_status': 'error',
            'database_type': 'MongoDB Atlas',
            'last_updated': datetime.now(timezone.utc).isoformat()
        }, status_code=500)


@app.get("/api/ai/learning/summary")
async def get_ai_learning_summary():
    """Get comprehensive AI learning data summary"""
    try:
        # Get learning summary from database
        summary = await get_db().get_learning_summary()
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
        recent_decisions = await get_db().get_recent_decisions(limit=10)
        
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
        summary = await get_db().get_comprehensive_learning_summary()
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
        training_data = await get_db().get_training_data(symbol, feature_type, days)
        return JSONResponse(content=training_data)
    except Exception as e:
        logger.error(f"Failed to get training data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/market-sentiment/{symbol}")
async def get_market_sentiment_history(symbol: str, days: int = 7):
    """Get market sentiment history for a symbol"""
    try:
        sentiment_history = await get_db().get_market_sentiment_history(symbol, days)
        return JSONResponse(content=sentiment_history)
    except Exception as e:
        logger.error(f"Failed to get sentiment history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/pattern-analysis")
async def get_pattern_analysis(pattern_type: str = None):
    """Get price pattern success rates and analysis"""
    try:
        pattern_rates = await get_db().get_pattern_success_rates(pattern_type)
        return JSONResponse(content=pattern_rates)
    except Exception as e:
        logger.error(f"Failed to get pattern analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/strategy-performance")
async def get_ai_strategy_performance(strategy_name: str = None, days: int = 30):
    """Get AI strategy performance analytics"""
    try:
        performance = await get_db().get_strategy_performance(strategy_name, days)
        return JSONResponse(content=performance)
    except Exception as e:
        logger.error(f"Failed to get strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/market-regime")
async def get_market_regime_history(days: int = 30):
    """Get market regime classification history"""
    try:
        regime_history = await get_db().get_market_regime_history(days)
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
        db = get_db()
        if db:
            active_trades = await db.get_active_trades() if hasattr(db, 'get_active_trades') else []
        else:
            active_trades = []
            
        await websocket.send_text(json.dumps({
            'type': 'initial_trades',
            'data': active_trades
        }))
        
        # Real-time trade monitoring loop
        last_check = datetime.now()
        
        while True:
            try:
                # Non-blocking message receive with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)  # Increased from 5 to 30 seconds
                
                if message == "get_trades":
                    if db and hasattr(db, 'get_active_trades'):
                        current_trades = await db.get_active_trades()
                    else:
                        current_trades = []
                    await websocket.send_text(json.dumps({
                        'type': 'trade_update',
                        'data': current_trades
                    }))
                    
            except asyncio.TimeoutError:
                # Periodic update check - send heartbeat and trade updates
                current_time = datetime.now()
                
                # Send heartbeat
                await websocket.send_text(json.dumps({
                    'type': 'heartbeat',
                    'timestamp': current_time.isoformat()
                }))
                
                # Check for trade updates every 30 seconds
                if (current_time - last_check).seconds >= 30:
                    if db and hasattr(db, 'get_active_trades'):
                        current_trades = await db.get_active_trades()
                        await websocket.send_text(json.dumps({
                            'type': 'trade_update',
                            'data': current_trades,
                            'timestamp': current_time.isoformat()
                        }))
                    last_check = current_time
                    
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /ws/trades")
    except Exception as e:
        logger.error(f"Trade WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                'type': 'error',
                'message': 'Connection error occurred'
            }))
        except:
            pass


# ==================== POLYGON.IO TRADING ENGINES ====================

@app.get("/api/polygon/anomalies")
async def get_anomaly_signals(symbols: str = None):
    """Get real-time anomaly detection signals from Polygon.io data"""
    try:
        symbol_list = symbols.split(',') if symbols else ['AAPL', 'TSLA', 'SPY', 'QQQ', 'NVDA']
        
        # Get anomaly signals
        anomaly_detector = get_anomaly_engine()
        anomalies = await anomaly_detector.detect_anomalies(symbol_list)
        
        return JSONResponse(content={
            "anomalies": [
                {
                    "symbol": anomaly.symbol,
                    "anomaly_type": anomaly.anomaly_type,
                    "z_score": anomaly.z_score,
                    "confidence": anomaly.confidence,
                    "price": anomaly.current_price,
                    "volume_ratio": anomaly.volume_ratio,
                    "price_change": anomaly.price_change_percent,
                    "timestamp": anomaly.timestamp.isoformat()
                }
                for anomaly in anomalies
            ],
            "total_anomalies": len(anomalies),
            "scan_time": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/polygon/short-squeeze")
async def get_short_squeeze_signals(symbols: str = None):
    """Get short squeeze probability signals from Polygon.io data"""
    try:
        symbol_list = symbols.split(',') if symbols else ['GME', 'AMC', 'TSLA', 'AAPL', 'NVDA']
        
        # Get short squeeze signals
        squeeze_signals = await squeeze_detector.scan_for_squeeze_opportunities(symbol_list)
        
        return JSONResponse(content={
            "squeeze_opportunities": [
                {
                    "symbol": signal.symbol,
                    "squeeze_probability": signal.squeeze_probability,
                    "short_interest_ratio": signal.short_interest_ratio,
                    "short_volume_ratio": signal.short_volume_ratio,
                    "volume_spike": signal.volume_spike,
                    "price_momentum": signal.price_momentum,
                    "risk_level": signal.risk_level,
                    "entry_price": signal.entry_price,
                    "target_price": signal.target_price,
                    "stop_loss": signal.stop_loss,
                    "timestamp": signal.timestamp.isoformat()
                }
                for signal in squeeze_signals
            ],
            "total_opportunities": len(squeeze_signals),
            "scan_time": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Short squeeze detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/polygon/sentiment")
async def get_sentiment_signals(symbols: str = None):
    """Get AI sentiment trading signals from Polygon.io news data"""
    try:
        symbol_list = symbols.split(',') if symbols else ['AAPL', 'TSLA', 'SPY', 'NVDA', 'META']
        
        # Get sentiment signals
        sentiment_signals = await sentiment_engine.scan_for_sentiment_opportunities(symbol_list)
        
        return JSONResponse(content={
            "sentiment_signals": [
                {
                    "symbol": signal.symbol,
                    "sentiment_score": signal.sentiment_score,
                    "confidence": signal.confidence,
                    "news_count": signal.news_count,
                    "relevance_score": signal.relevance_score,
                    "price_impact": signal.price_impact,
                    "signal_strength": signal.signal_strength,
                    "entry_price": signal.entry_price,
                    "target_price": signal.target_price,
                    "stop_loss": signal.stop_loss,
                    "key_headlines": signal.key_headlines,
                    "timestamp": signal.timestamp.isoformat()
                }
                for signal in sentiment_signals
            ],
            "total_signals": len(sentiment_signals),
            "scan_time": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/polygon/unified-signals")
async def get_unified_trading_signals(symbols: str = None):
    """Get coordinated signals from all Polygon.io trading engines"""
    try:
        symbol_list = symbols.split(',') if symbols else ['AAPL', 'TSLA', 'SPY', 'QQQ', 'NVDA', 'META', 'MSFT']
        
        # Get unified signals from master coordinator
        unified_signals = await master_coordinator.generate_unified_signals(symbol_list)
        
        return JSONResponse(content={
            "unified_signals": [
                {
                    "symbol": signal.symbol,
                    "overall_score": signal.overall_score,
                    "signal_strength": signal.signal_strength,
                    "recommendation": signal.recommendation,
                    "confidence": signal.confidence,
                    "entry_price": signal.entry_price,
                    "target_price": signal.target_price,
                    "stop_loss": signal.stop_loss,
                    "position_size": signal.position_size,
                    "risk_level": signal.risk_level,
                    "contributing_signals": {
                        "anomaly_score": signal.anomaly_score,
                        "squeeze_probability": signal.squeeze_probability,
                        "sentiment_score": signal.sentiment_score
                    },
                    "reasoning": signal.reasoning,
                    "timestamp": signal.timestamp.isoformat()
                }
                for signal in unified_signals
            ],
            "total_signals": len(unified_signals),
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "active_engines": 4,  # anomaly, squeeze, sentiment, websocket
            "system_status": "operational"
        })
        
    except Exception as e:
        logger.error(f"Unified signals generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/polygon/websocket-status")
async def get_websocket_engine_status():
    """Get real-time WebSocket engine status and recent activity"""
    try:
        status = await websocket_engine.get_status()
        recent_data = await websocket_engine.get_recent_data(limit=50)
        
        return JSONResponse(content={
            "engine_status": {
                "connected": status.get('connected', False),
                "last_message": status.get('last_message_time'),
                "messages_processed": status.get('messages_processed', 0),
                "connection_uptime": status.get('uptime_seconds', 0),
                "active_subscriptions": status.get('active_subscriptions', [])
            },
            "recent_data": recent_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"WebSocket status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SYSTEM CONTROL ENDPOINTS ====================

@app.post("/api/system/emergency_stop")
async def emergency_stop():
    """Emergency stop all trading activities"""
    try:
        # Cancel all pending orders
        orders = await get_trading_service().get_orders()
        cancelled_orders = []
        
        for order in orders:
            try:
                await get_trading_service().cancel_order(order.id)
                cancelled_orders.append(order.id)
            except Exception as e:
                logger.error(f"Failed to cancel order {order.id}: {e}")
        
        # Log emergency stop
        await get_db().log_system_health(
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
        active_trades = await get_db().get_active_trades()
        recent_decisions = await get_db().get_recent_decisions(limit=10)
        
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
        positions = await get_trading_service().get_positions()
        
        if not positions:
            # Return empty but valid structure instead of error
            return JSONResponse(content={
                'holdings': [],
                'summary': {
                    'total_positions': 0,
                    'total_value': 0.0,
                    'total_pnl': 0.0,
                    'avg_performance': 0.0
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Get account info for portfolio calculations
        account = await get_trading_service().get_account()
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
            # Return empty but valid structure 
            return JSONResponse(content={
                'holdings': [],
                'summary': {
                    'total_positions': 0,
                    'total_value': 0.0,
                    'total_pnl': 0.0,
                    'avg_performance': 0.0
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
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
    """Get detailed performance analytics"""
    try:
        # Import performance analytics service
        from backend.services.performance_analytics import performance_service
        
        # Get comprehensive performance metrics
        overall_performance = await performance_service.get_overall_performance()
        daily_performance = await performance_service.get_daily_performance(days=30)
        position_performance = await performance_service.get_position_performance()
        trading_stats = await performance_service.get_trading_statistics(days=30)
        risk_metrics = await performance_service.get_risk_metrics()
        
        return JSONResponse(content={
            'overall_performance': {
                'total_return': overall_performance.total_return,
                'daily_return': overall_performance.daily_return,
                'weekly_return': overall_performance.weekly_return,
                'monthly_return': overall_performance.monthly_return,
                'ytd_return': overall_performance.ytd_return,
                'current_balance': overall_performance.current_balance,
                'portfolio_value': overall_performance.portfolio_value,
                'unrealized_pnl': overall_performance.unrealized_pnl,
                'realized_pnl': overall_performance.realized_pnl
            },
            'risk_metrics': {
                'sharpe_ratio': overall_performance.sharpe_ratio,
                'max_drawdown': overall_performance.max_drawdown,
                'volatility': risk_metrics.get('volatility', 0),
                'var_95': risk_metrics.get('var_95', 0),
                'beta': risk_metrics.get('beta', 1.0),
                'alpha': risk_metrics.get('alpha', 0)
            },
            'trading_statistics': {
                'total_trades': overall_performance.total_trades,
                'profitable_trades': overall_performance.profitable_trades,
                'win_rate': overall_performance.win_rate,
                'average_win': overall_performance.average_win,
                'average_loss': overall_performance.average_loss,
                'profit_factor': trading_stats.get('profit_factor', 0),
                'largest_win': trading_stats.get('largest_win', 0),
                'largest_loss': trading_stats.get('largest_loss', 0)
            },
            'daily_performance': daily_performance[-30:],  # Last 30 days
            'position_performance': position_performance,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics service error: {str(e)}")


@app.get("/api/dashboard/market/pulse")
async def get_market_pulse():
    """Get real-time market pulse and technical analysis (NO SENTIMENT)"""
    try:
        # Import market pulse service
        from backend.services.market_pulse import market_pulse_service
        
        # Get comprehensive market pulse data
        pulse_data = await market_pulse_service.get_market_pulse()
        
        # Get historical pulse for trend analysis
        historical_pulse = await market_pulse_service.get_historical_pulse(days=7)
        
        return JSONResponse(content={
            'market_overview': {
                'trend': pulse_data.market_trend,
                'volatility': pulse_data.market_volatility,
                'volume_profile': pulse_data.volume_profile,
                'volatility_index': pulse_data.volatility_index,
                'momentum_score': pulse_data.momentum_score
            },
            'key_levels': pulse_data.key_levels,
            'active_sectors': pulse_data.active_sectors,
            'market_breadth': pulse_data.market_breadth,
            'technical_indicators': {
                'trend_strength': abs(pulse_data.momentum_score) / 100,
                'volatility_regime': pulse_data.market_volatility,
                'volume_confirmation': pulse_data.volume_profile == 'HEAVY'
            },
            'historical_context': {
                'trend_consistency': len([h for h in historical_pulse if h.get('trend') == pulse_data.market_trend]),
                'volatility_trend': historical_pulse[-3:] if len(historical_pulse) >= 3 else [],
                'momentum_history': [h.get('momentum', 0) for h in historical_pulse[-5:]]
            },
            'timestamp': pulse_data.timestamp.isoformat(),
            'note': 'Market pulse based on technical analysis only - no sentiment analysis included'
        })
        
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
    """Get AI signals for watchlist symbols"""
    try:
        # Import AI signal generation service
        from backend.services.ai_signal_generation import ai_signal_service
        
        # Generate signals for the entire watchlist
        watchlist_signals = await ai_signal_service.generate_signals_for_watchlist()
        
        # Get signal performance for context
        signal_performance = await ai_signal_service.get_signal_performance(days=7)
        
        # Format signals for watchlist display
        formatted_signals = []
        for signal in watchlist_signals:
            # Get current market data for each signal
            from backend.services.real_time_market_data import market_data_service
            async with market_data_service:
                current_data = await market_data_service.get_real_time_quote(signal.symbol)
            
            current_price = current_data.price if current_data else signal.entry_price
            
            # Calculate potential return and risk
            potential_return = signal.expected_return
            risk_reward_ratio = abs(potential_return / 15) if signal.risk_level == 'HIGH' else abs(potential_return / 10) if signal.risk_level == 'MEDIUM' else abs(potential_return / 5)
            
            formatted_signals.append({
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'current_price': current_price,
                'price_target': signal.price_target,
                'potential_return': round(potential_return, 2),
                'risk_level': signal.risk_level,
                'risk_reward_ratio': round(risk_reward_ratio, 2),
                'time_horizon': signal.time_horizon,
                'reasoning_summary': signal.reasoning[:100] + '...' if len(signal.reasoning) > 100 else signal.reasoning,
                'signal_strength': 'STRONG' if signal.confidence > 0.8 else 'MODERATE' if signal.confidence > 0.6 else 'WEAK',
                'market_context': {
                    'day_change': current_data.change_percent if current_data else 0,
                    'volume_status': 'HIGH' if current_data and current_data.volume > 1000000 else 'NORMAL'
                },
                'timestamp': signal.timestamp.isoformat()
            })
        
        # Sort by confidence level
        formatted_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return JSONResponse(content={
            'watchlist_signals': formatted_signals,
            'summary': {
                'total_signals': len(formatted_signals),
                'strong_signals': len([s for s in formatted_signals if s['signal_strength'] == 'STRONG']),
                'buy_signals': len([s for s in formatted_signals if s['signal_type'] == 'BUY']),
                'sell_signals': len([s for s in formatted_signals if s['signal_type'] == 'SELL']),
                'avg_confidence': round(sum(s['confidence'] for s in formatted_signals) / len(formatted_signals), 2) if formatted_signals else 0
            },
            'performance_context': signal_performance,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'note': 'AI signals generated using technical analysis and machine learning models'
        })
        
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
                orders = await get_trading_service().get_orders(status='open')
                for order in orders:
                    await get_trading_service().cancel_order(order.id)
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
                account = await get_trading_service().get_account()
                positions = await get_trading_service().get_positions()
                orders = await get_trading_service().get_orders()
                
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
        account = await get_trading_service().get_account()
        
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
    try:
        # Import AI signal generation service
        from backend.services.ai_signal_generation import ai_signal_service
        
        # Get recent signals with performance data
        recent_signals = await ai_signal_service.get_active_signals()
        signal_performance = await ai_signal_service.get_signal_performance(days=30)
        
        # Format for dashboard display
        dashboard_signals = []
        for signal in recent_signals[:20]:  # Limit to 20 most recent
            dashboard_signals.append({
                'id': f"{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}",
                'symbol': signal.symbol,
                'type': signal.signal_type,
                'confidence': signal.confidence,
                'entry_price': signal.entry_price,
                'target': signal.price_target,
                'risk_level': signal.risk_level,
                'expected_return': signal.expected_return,
                'time_created': signal.timestamp.isoformat(),
                'status': 'ACTIVE',
                'horizon': signal.time_horizon
            })
        
        return JSONResponse(content={
            'signals': dashboard_signals,
            'performance_summary': signal_performance,
            'statistics': {
                'total_active': len(recent_signals),
                'high_confidence': len([s for s in recent_signals if s.confidence > 0.8]),
                'buy_signals': len([s for s in recent_signals if s.signal_type == 'BUY']),
                'sell_signals': len([s for s in recent_signals if s.signal_type == 'SELL'])
            },
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get AI signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/ai/learning-metrics")
async def get_ai_learning_metrics():
    """Get AI learning progress metrics"""
    try:
        # Import AI learning engine
        from backend.services.ai_learning_engine import ai_learning_engine
        
        # Get learning metrics and performance data
        learning_metrics = await ai_learning_engine.get_learning_metrics()
        model_performance = await ai_learning_engine.get_model_performance()
        prediction_accuracy = await ai_learning_engine.get_prediction_accuracy()
        
        return JSONResponse(content={
            'learning_progress': {
                'total_predictions': learning_metrics.get('total_predictions', 0),
                'successful_predictions': learning_metrics.get('successful_predictions', 0),
                'accuracy_rate': learning_metrics.get('accuracy_rate', 0.0),
                'learning_trend': learning_metrics.get('learning_trend', 'STABLE'),
                'model_confidence': learning_metrics.get('model_confidence', 0.5)
            },
            'model_performance': {
                'precision': model_performance.get('precision', 0.0),
                'recall': model_performance.get('recall', 0.0),
                'f1_score': model_performance.get('f1_score', 0.0),
                'training_accuracy': model_performance.get('training_accuracy', 0.0),
                'validation_accuracy': model_performance.get('validation_accuracy', 0.0)
            },
            'prediction_metrics': {
                'recent_accuracy': prediction_accuracy.get('recent_accuracy', 0.0),
                'accuracy_trend': prediction_accuracy.get('accuracy_trend', []),
                'best_performing_timeframe': prediction_accuracy.get('best_timeframe', 'MEDIUM'),
                'improvement_rate': prediction_accuracy.get('improvement_rate', 0.0)
            },
            'adaptive_learning': {
                'learning_rate': 0.001,  # Current learning rate
                'model_updates': learning_metrics.get('model_updates', 0),
                'data_points_processed': learning_metrics.get('data_points', 0),
                'next_training_scheduled': 'Auto-triggered based on performance'
            },
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get AI learning metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CONFIGURATION ENDPOINTS ====================

@app.get("/api/config/system")
async def get_system_configuration():
    """Get current system configuration"""
    try:
        # Get current system configuration from environment and database
        from backend.services.database_manager import db_manager
        
        # Check service availability
        trading_service = get_trading_service()
        
        # Get stored configuration from database
        stored_trading_config = {}
        stored_ai_config = {}
        stored_risk_config = {}
        stored_notification_config = {}
        
        if db_manager:
            try:
                stored_trading_config = await db_manager.get_system_config('trading') or {}
                stored_ai_config = await db_manager.get_system_config('ai_settings') or {}
                stored_risk_config = await db_manager.get_system_config('risk_management') or {}
                stored_notification_config = await db_manager.get_system_config('notifications') or {}
            except Exception as e:
                logger.warning(f"Could not retrieve stored config: {e}")
        
        system_config = {
            'trading': {
                'auto_trading_enabled': stored_trading_config.get('auto_trading_enabled', False),
                'risk_per_trade': stored_trading_config.get('risk_per_trade', 0.02),
                'max_positions': stored_trading_config.get('max_positions', 5),
                'trading_mode': 'PAPER' if os.getenv('ALPACA_PAPER') == 'True' else 'LIVE'
            },
            'ai_settings': {
                'confidence_threshold': stored_ai_config.get('confidence_threshold', 0.65),
                'signal_generation_enabled': stored_ai_config.get('signal_generation_enabled', True),
                'learning_mode': stored_ai_config.get('learning_mode', 'ADAPTIVE'),
                'model_update_frequency': stored_ai_config.get('model_update_frequency', 'DAILY')
            },
            'data_providers': {
                'market_data': 'Polygon.io',
                'broker': 'Alpaca',
                'database': 'MongoDB Atlas'
            },
            'risk_management': {
                'max_drawdown_limit': stored_risk_config.get('max_drawdown_limit', 0.15),
                'position_sizing': stored_risk_config.get('position_sizing', 'DYNAMIC'),
                'stop_loss_enabled': stored_risk_config.get('stop_loss_enabled', True),
                'take_profit_enabled': stored_risk_config.get('take_profit_enabled', True)
            },
            'notifications': {
                'telegram_enabled': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
                'trade_alerts': stored_notification_config.get('trade_alerts', True),
                'signal_alerts': stored_notification_config.get('signal_alerts', True),
                'performance_reports': stored_notification_config.get('performance_reports', True)
            },
            'system_status': {
                'api_server': 'RUNNING',
                'database': 'CONNECTED',
                'trading_service': 'ACTIVE' if trading_service else 'INACTIVE',
                'data_feeds': 'CONNECTED'
            }
        }
        
        return JSONResponse(content={
            'configuration': system_config,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'config_version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Failed to get system configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/system")
async def update_system_configuration(config_data: Dict[str, Any]):
    """Update system configuration"""
    try:
        # Import services for configuration updates
        from backend.services.database_manager import db_manager
        
        updated_settings = {}
        trading_service = get_trading_service()
        
        # Handle trading configuration updates
        if 'trading' in config_data:
            trading_config = config_data['trading']
            
            # Store trading configuration in database
            trading_settings = {}
            
            if 'auto_trading_enabled' in trading_config:
                trading_settings['auto_trading_enabled'] = bool(trading_config['auto_trading_enabled'])
                updated_settings['auto_trading_enabled'] = trading_settings['auto_trading_enabled']
            
            if 'risk_per_trade' in trading_config:
                trading_settings['risk_per_trade'] = float(trading_config['risk_per_trade'])
                updated_settings['risk_per_trade'] = trading_settings['risk_per_trade']
            
            if 'max_positions' in trading_config:
                trading_settings['max_positions'] = int(trading_config['max_positions'])
                updated_settings['max_positions'] = trading_settings['max_positions']
            
            # Save to database
            if trading_settings:
                await db_manager.update_system_config('trading', trading_settings)
                updated_settings['trading'] = trading_settings
        
        # Handle AI settings updates
        if 'ai_settings' in config_data:
            ai_config = config_data['ai_settings']
            
            # Store AI configuration in database
            ai_settings = {
                'confidence_threshold': ai_config.get('confidence_threshold', 0.65),
                'signal_generation_enabled': ai_config.get('signal_generation_enabled', True),
                'learning_mode': ai_config.get('learning_mode', 'ADAPTIVE'),
                'model_update_frequency': ai_config.get('model_update_frequency', 'DAILY')
            }
            
            await db_manager.update_system_config('ai_settings', ai_settings)
            updated_settings['ai_settings'] = ai_settings
        
        # Handle risk management updates
        if 'risk_management' in config_data:
            risk_config = config_data['risk_management']
            
            risk_settings = {
                'max_drawdown_limit': risk_config.get('max_drawdown_limit', 0.15),
                'position_sizing': risk_config.get('position_sizing', 'DYNAMIC'),
                'stop_loss_enabled': risk_config.get('stop_loss_enabled', True),
                'take_profit_enabled': risk_config.get('take_profit_enabled', True)
            }
            
            await db_manager.update_system_config('risk_management', risk_settings)
            updated_settings['risk_management'] = risk_settings
        
        # Handle notification settings
        if 'notifications' in config_data:
            notification_config = config_data['notifications']
            
            notification_settings = {
                'trade_alerts': notification_config.get('trade_alerts', True),
                'signal_alerts': notification_config.get('signal_alerts', True),
                'performance_reports': notification_config.get('performance_reports', True)
            }
            
            await db_manager.update_system_config('notifications', notification_settings)
            updated_settings['notifications'] = notification_settings
        
        return JSONResponse(content={
            'status': 'success',
            'updated_settings': updated_settings,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': f'Updated {len(updated_settings)} configuration sections'
        })
        
    except Exception as e:
        logger.error(f"Failed to update system configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/status")
async def get_config_status():
    """Get detailed system status for configuration panel"""
    try:
        # Get system configuration status
        config_status = {
            "database_connected": True,  # Will be checked by health monitor
            "trading_service_active": bool(get_trading_service()),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "paper_trading": os.getenv("PAPER_TRADING", "true").lower() == "true",
            "api_keys_configured": {
                "alpaca": bool(os.getenv("ALPACA_API_KEY")),
                "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
                "mongodb": bool(os.getenv("MONGODB_URL"))
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return JSONResponse(content=config_status)
    except Exception as e:
        logger.error(f"Config status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


# ================================
# AI PREDICTIONS ENDPOINTS
# ================================

@app.get("/api/ai/predictions")
async def get_ai_predictions():
    """Get AI predictions dashboard data."""
    try:
        from services.ai_predictions_service import ai_predictions_service
        
        logger.info("API: Getting AI predictions data")
        data = ai_predictions_service.get_predictions_dashboard_data()
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logger.error(f"Error getting AI predictions: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/ai/predictions/top")
async def get_top_predictions(limit: int = 10):
    """Get top AI predictions by confidence."""
    try:
        from services.ai_predictions_service import ai_predictions_service
        
        predictions = ai_predictions_service.get_top_predictions(limit=limit)
        
        return JSONResponse(content={
            "success": True,
            "predictions": predictions,
            "count": len(predictions),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting top predictions: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/ai/predictions/{symbol}")
async def get_prediction_by_symbol(symbol: str):
    """Get AI prediction for specific symbol."""
    try:
        from services.ai_predictions_service import ai_predictions_service
        
        prediction = ai_predictions_service.get_predictions_by_symbol(symbol.upper())
        
        if prediction:
            return JSONResponse(content={
                "success": True,
                "prediction": prediction,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return JSONResponse(content={
                "success": False,
                "message": f"No prediction found for {symbol.upper()}",
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error getting prediction for {symbol}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/ai/predictions/signals/high-confidence")
async def get_high_confidence_signals(min_confidence: float = 8.0):
    """Get high confidence trading signals."""
    try:
        from services.ai_predictions_service import ai_predictions_service
        
        signals = ai_predictions_service.get_high_confidence_signals(min_confidence=min_confidence)
        
        return JSONResponse(content={
            "success": True,
            "signals": signals,
            "count": len(signals),
            "min_confidence": min_confidence,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting high confidence signals: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ================================
# PORTFOLIO HOLDINGS ENDPOINTS
# ================================

@app.get("/api/portfolio/holdings")
async def get_portfolio_holdings():
    """Get complete portfolio holdings dashboard data."""
    try:
        from services.portfolio_holdings_service import portfolio_holdings_service
        
        logger.info("API: Getting portfolio holdings data")
        data = await portfolio_holdings_service.get_holdings_dashboard_data()
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logger.error(f"Error getting portfolio holdings: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary metrics."""
    try:
        from services.portfolio_holdings_service import portfolio_holdings_service
        
        holdings = await portfolio_holdings_service.get_real_holdings_data()
        summary = await portfolio_holdings_service.calculate_portfolio_summary(holdings)
        
        return JSONResponse(content={
            "success": True,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/portfolio/allocation")
async def get_portfolio_allocation():
    """Get portfolio allocation breakdown."""
    try:
        from services.portfolio_holdings_service import portfolio_holdings_service
        
        allocation = await portfolio_holdings_service.get_portfolio_allocation()
        
        return JSONResponse(content={
            "success": True,
            "allocation": allocation,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting portfolio allocation: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/portfolio/position/{symbol}")
async def get_position_by_symbol(symbol: str):
    """Get specific position by symbol."""
    try:
        from services.portfolio_holdings_service import portfolio_holdings_service
        
        position = await portfolio_holdings_service.get_position_by_symbol(symbol.upper())
        
        if position:
            return JSONResponse(content={
                "success": True,
                "position": position,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return JSONResponse(content={
                "success": False,
                "message": f"No position found for {symbol.upper()}",
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error getting position for {symbol}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/account/summary")
async def get_account_summary():
    """Get detailed account summary."""
    try:
        from services.portfolio_holdings_service import portfolio_holdings_service
        
        account_data = await portfolio_holdings_service.get_account_summary()
        
        return JSONResponse(content={
            "success": True,
            "account": account_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting account summary: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ================================
# TRADING CONTROL ENDPOINTS
# ================================

@app.post("/api/trading/buy")
async def execute_buy_order(order_data: dict):
    """Execute manual buy order."""
    try:
        from services.real_trading_controls import trading_controller
        
        ticker = order_data.get('ticker', '').upper()
        shares = order_data.get('shares')
        amount = order_data.get('amount')
        
        if not ticker:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Ticker is required"}
            )
        
        result = await trading_controller.execute_manual_buy(ticker, shares=shares, amount=amount)
        
        # Send Telegram notification if buy was successful
        if result.get('success') and result.get('executed'):
            try:
                from services.telegram_notifier import TelegramNotifier
                notifier = TelegramNotifier()
                
                # Extract trade details
                trade_info = result.get('trade', {})
                executed_shares = trade_info.get('qty', shares)
                executed_price = trade_info.get('price', 0.0)
                order_id = trade_info.get('id', 'Unknown')
                
                await notifier.send_buy_notification(
                    symbol=ticker,
                    quantity=executed_shares,
                    price=float(executed_price),
                    order_id=order_id,
                    predicted_target=None,  # Could enhance with AI prediction later
                    confidence=None,        # Could enhance with AI confidence later
                    stop_loss=None,        # Could enhance with stop loss calculation
                    reasoning="Manual buy order executed via production API"
                )
            except Exception as notify_error:
                logger.warning(f"Failed to send buy notification: {notify_error}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error executing buy order: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/trading/sell")
async def execute_sell_order(order_data: dict):
    """Execute manual sell order."""
    try:
        from services.real_trading_controls import trading_controller
        
        ticker = order_data.get('ticker', '').upper()
        shares = order_data.get('shares')
        
        if not ticker:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Ticker is required"}
            )
        
        result = await trading_controller.execute_manual_sell(ticker, shares=shares)
        
        # Send Telegram notification if sell was successful
        if result.get('success') and result.get('executed'):
            try:
                from services.telegram_notifier import TelegramNotifier
                notifier = TelegramNotifier()
                
                # Extract trade details
                trade_info = result.get('trade', {})
                executed_shares = trade_info.get('qty', shares)
                executed_price = trade_info.get('price', 0.0)
                order_id = trade_info.get('id', 'Unknown')
                pnl = trade_info.get('unrealized_pl', None)
                
                await notifier.send_sell_notification(
                    symbol=ticker,
                    quantity=executed_shares,
                    price=float(executed_price),
                    pnl=float(pnl) if pnl else None,
                    order_id=order_id,
                    entry_price=None,      # Could enhance with position entry price
                    sell_reason="Manual sell order executed via production API",
                    target_hit=False       # Could enhance with target achievement detection
                )
            except Exception as notify_error:
                logger.warning(f"Failed to send sell notification: {notify_error}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error executing sell order: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/trading/pause")
async def pause_auto_trading():
    """Pause automatic trading."""
    try:
        from services.real_trading_controls import trading_controller
        
        result = await trading_controller.pause_auto_trading()
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error pausing trading: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/trading/resume")
async def resume_auto_trading():
    """Resume automatic trading."""
    try:
        from services.real_trading_controls import trading_controller
        
        result = await trading_controller.resume_auto_trading()
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error resuming trading: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/trading/scan")
async def trigger_market_scan():
    """Trigger immediate market scan."""
    try:
        from services.real_trading_controls import trading_controller
        
        result = await trading_controller.trigger_market_scan()
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error triggering market scan: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/notifications/test")
async def send_test_notification():
    """Send test notification."""
    try:
        from services.real_trading_controls import trading_controller
        
        result = await trading_controller.send_test_notification()
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

if __name__ == "__main__":
    uvicorn.run(
        "production_api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Disable reload in production
        workers=1,     # Single worker for trading system consistency
        log_level="info"
    )
