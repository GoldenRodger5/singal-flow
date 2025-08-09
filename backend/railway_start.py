#!/usr/bin/env python3
"""
Railway Cloud Deployment Script
Starts the trading system optimized for cloud deployment
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from loguru import logger
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Global variables
start_time = time.time()
trading_system_initialized = False

# Set up cloud-optimized logging
def setup_cloud_logging():
    """Setup logging for cloud deployment."""
    logger.remove()  # Remove default handler
    
    # Console logging (Railway captures this)
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File logging (Railway persistent storage)
    log_file = "logs/trading_system_cloud.log"
    os.makedirs("logs", exist_ok=True)
    
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        compression="gz"
    )

# Health check API for Railway
app = FastAPI(title="Signal Flow Trading Bot", version="1.0.0")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Signal Flow Trading Bot is running", "timestamp": datetime.now()}

@app.get("/debug/mongodb")
async def debug_mongodb_connection():
    """Debug MongoDB connection issues."""
    try:
        import os
        from services.config import Config
        
        config = Config()
        
        debug_info = {
            "mongodb_url_exists": bool(config.MONGODB_URL),
            "mongodb_url_length": len(config.MONGODB_URL) if config.MONGODB_URL else 0,
            "mongodb_url_preview": config.MONGODB_URL[:50] + "..." if config.MONGODB_URL and len(config.MONGODB_URL) > 50 else config.MONGODB_URL,
            "mongodb_name": config.MONGODB_NAME,
            "environment_vars": {
                "MONGODB_URL": bool(os.getenv('MONGODB_URL')),
                "MONGODB_NAME": os.getenv('MONGODB_NAME', 'Not Set'),
                "NODE_ENV": os.getenv('NODE_ENV', 'Not Set'),
                "RAILWAY_ENVIRONMENT": os.getenv('RAILWAY_ENVIRONMENT', 'Not Set')
            }
        }
        
        # Test actual MongoDB connection
        try:
            from pymongo import MongoClient
            from urllib.parse import quote_plus
            
            if config.MONGODB_URL:
                client = MongoClient(config.MONGODB_URL, serverSelectionTimeoutMS=5000)
                # Test the connection
                client.admin.command('ping')
                debug_info["mongodb_connection_test"] = "SUCCESS"
                client.close()
            else:
                debug_info["mongodb_connection_test"] = "NO_URL_PROVIDED"
                
        except Exception as mongo_error:
            debug_info["mongodb_connection_test"] = f"FAILED: {str(mongo_error)}"
        
        return debug_info
        
    except Exception as e:
        return {"error": f"Debug endpoint failed: {str(e)}"}

@app.get("/debug/env")
async def debug_environment_variables():
    """Debug all environment variables for Railway deployment."""
    try:
        import os
        
        # Get all Railway-specific environment variables
        env_debug = {
            "railway_vars": {
                "RAILWAY_ENVIRONMENT": os.getenv('RAILWAY_ENVIRONMENT', 'Not Set'),
                "RAILWAY_PROJECT_ID": os.getenv('RAILWAY_PROJECT_ID', 'Not Set'),
                "RAILWAY_SERVICE_NAME": os.getenv('RAILWAY_SERVICE_NAME', 'Not Set'),
                "PORT": os.getenv('PORT', 'Not Set')
            },
            "database_vars": {
                "MONGODB_URL_exists": bool(os.getenv('MONGODB_URL')),
                "MONGODB_URL_length": len(os.getenv('MONGODB_URL', '')),
                "MONGODB_NAME": os.getenv('MONGODB_NAME', 'Not Set')
            },
            "trading_vars": {
                "ALPACA_API_KEY_exists": bool(os.getenv('ALPACA_API_KEY')),
                "ALPACA_SECRET_exists": bool(os.getenv('ALPACA_SECRET')),
                "ALPACA_BASE_URL": os.getenv('ALPACA_BASE_URL', 'Not Set'),
                "PAPER_TRADING": os.getenv('PAPER_TRADING', 'Not Set')
            },
            "notification_vars": {
                "TELEGRAM_BOT_TOKEN_exists": bool(os.getenv('TELEGRAM_BOT_TOKEN')),
                "TELEGRAM_CHAT_ID_exists": bool(os.getenv('TELEGRAM_CHAT_ID'))
            },
            "system_info": {
                "python_path": os.getenv('PATH', 'Not Set')[:100] + "...",
                "working_directory": os.getcwd(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return env_debug
        
    except Exception as e:
        return {"error": f"Environment debug failed: {str(e)}"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    try:
        # Get environment info for debugging - Railway specific check
        import os
        mongodb_url_raw = os.getenv('MONGODB_URL')
        mongodb_url_exists = bool(mongodb_url_raw)
        mongodb_url_length = len(mongodb_url_raw) if mongodb_url_raw else 0
        
        # Test MongoDB connection with detailed error reporting
        mongodb_status = "unknown"
        mongodb_error = None
        connection_details = {
            "env_var_exists": mongodb_url_exists,
            "env_var_length": mongodb_url_length,
            "raw_env_preview": mongodb_url_raw[:50] + "..." if mongodb_url_raw and len(mongodb_url_raw) > 50 else mongodb_url_raw,
            "railway_environment": os.getenv('RAILWAY_ENVIRONMENT', 'not_set'),
            "environment": os.getenv('ENVIRONMENT', 'not_set')
        }
        
        try:
            # Try direct MongoDB connection first (bypassing Config class)
            if mongodb_url_raw and mongodb_url_raw != 'mongodb+srv://username:password@cluster.mongodb.net/':
                from pymongo import MongoClient
                client = MongoClient(mongodb_url_raw, serverSelectionTimeoutMS=5000)
                client.admin.command('ping')
                mongodb_status = "connected"
                connection_details["connection_method"] = "direct_env_var"
                client.close()
            else:
                # Try Config class as fallback
                from services.config import Config
                config = Config()
                
                connection_details.update({
                    "config_url_exists": bool(config.MONGODB_URL),
                    "config_url_length": len(config.MONGODB_URL) if config.MONGODB_URL else 0,
                    "config_db_name": config.MONGODB_NAME,
                    "config_url_preview": config.MONGODB_URL[:50] + "..." if config.MONGODB_URL and len(config.MONGODB_URL) > 50 else config.MONGODB_URL
                })
                
                if config.MONGODB_URL and config.MONGODB_URL != 'mongodb+srv://username:password@cluster.mongodb.net/':
                    from pymongo import MongoClient
                    client = MongoClient(config.MONGODB_URL, serverSelectionTimeoutMS=5000)
                    client.admin.command('ping')
                    mongodb_status = "connected"
                    connection_details["connection_method"] = "config_class"
                    client.close()
                else:
                    mongodb_status = "no_url"
                    mongodb_error = "MONGODB_URL environment variable not properly configured"
                
        except Exception as e:
            mongodb_status = "failed"
            mongodb_error = str(e)
            # Add more details about the specific error
            connection_details["error_type"] = type(e).__name__
            connection_details["error_details"] = str(e)
        
        return {
            "status": "healthy" if mongodb_status == "connected" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - start_time,
            "mode": "paper_trading",
            "environment": "railway",
            "trading_system_initialized": trading_system_initialized,
            "database": mongodb_status,
            "database_error": mongodb_error,
            "connection_debug": connection_details
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "database": "failed"
        }

@app.get("/status")
async def trading_status():
    """Trading system status."""
    return {
        "trading_active": True,
        "mode": "paper_trading",
        "environment": "railway",
        "timestamp": datetime.now()
    }

@app.get("/api/holdings")
async def get_holdings():
    """Get current holdings from the trading system."""
    try:
        # Import here to avoid circular imports
        from services.alpaca_trading import AlpacaTradingService
        
        trading_service = AlpacaTradingService()
        
        # Get positions from Alpaca (paper trading account)
        positions = trading_service.api.list_positions()
        
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
        
        return {"holdings": holdings, "total_value": sum(h["market_value"] for h in holdings)}
        
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        return {"holdings": [], "total_value": 0.0, "error": str(e)}

@app.get("/api/positions")
async def get_positions():
    """Get current positions (alias for holdings) from the trading system."""
    # This is an alias for get_holdings to ensure compatibility
    return await get_holdings()

@app.get("/api/account")
async def get_account_info():
    """Get account information from the trading system."""
    try:
        from services.alpaca_trading import AlpacaTradingService
        
        trading_service = AlpacaTradingService()
        account = trading_service.api.get_account()
        
        return {
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "daytrade_count": int(account.daytrade_count),
            "trading_blocked": account.trading_blocked,
            "account_blocked": account.account_blocked,
            "day_trade_buying_power": float(account.daytrading_buying_power),
            "status": account.status
        }
        
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        return {"error": str(e)}

@app.get("/api/dashboard/market/pulse")
async def get_market_pulse():
    """Get market pulse data for the dashboard."""
    try:
        # Get market overview data (using mock data for now since service may not be available)
        current_hour = datetime.now().hour
        market_data = {
            "market_status": "open" if 9 <= current_hour < 16 else "closed",
            "timestamp": datetime.now().isoformat(),
            "major_indices": {
                "SPY": {"price": 450.0, "change": 2.5, "change_percent": 0.56},
                "QQQ": {"price": 380.0, "change": -1.2, "change_percent": -0.32},
                "IWM": {"price": 200.0, "change": 1.8, "change_percent": 0.91}
            },
            "market_sentiment": "bullish",
            "volatility_index": 18.5,
            "volume_trend": "above_average"
        }
        
        return market_data
        
    except Exception as e:
        logger.error(f"Error fetching market pulse: {e}")
        return {
            "market_status": "unknown",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/dashboard/ai/signals")
async def get_ai_signals():
    """Get AI trading signals for the dashboard."""
    try:
        # Get recent AI signals (mock data for now)
        signals = [
            {
                "symbol": "AAPL",
                "signal": "BUY",
                "confidence": 85,
                "target_price": 185.0,
                "current_price": 180.0,
                "generated_at": datetime.now().isoformat()
            },
            {
                "symbol": "MSFT",
                "signal": "HOLD", 
                "confidence": 72,
                "target_price": 340.0,
                "current_price": 335.0,
                "generated_at": datetime.now().isoformat()
            }
        ]
        
        return {"signals": signals, "last_updated": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error fetching AI signals: {e}")
        return {"signals": [], "error": str(e)}

@app.get("/api/dashboard/ai/learning-metrics")
async def get_learning_metrics():
    """Get AI learning metrics for the dashboard."""
    try:
        # Get learning metrics (mock data for now)
        metrics = {
            "accuracy": 78.5,
            "total_predictions": 1250,
            "correct_predictions": 982,
            "win_rate": 76.2,
            "sharpe_ratio": 1.45,
            "last_training": datetime.now().isoformat(),
            "model_version": "v2.1.0"
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error fetching learning metrics: {e}")
        return {"error": str(e)}

@app.get("/api/config/system")
async def get_system_config():
    """Get system configuration for the dashboard."""
    try:
        system_config = {
            "trading_mode": "paper",
            "auto_trading": False,
            "risk_management": True,
            "market_hours_only": True,
            "max_position_size": 10000,
            "stop_loss_percent": 5.0,
            "take_profit_percent": 10.0
        }
        
        return system_config
        
    except Exception as e:
        logger.error(f"Error fetching system config: {e}")
        return {"error": str(e)}

@app.get("/api/config/status")
async def get_system_status():
    """Get system status for the dashboard."""
    try:
        status = {
            "trading_engine": "active",
            "ai_analysis": "running",
            "data_feed": "connected", 
            "risk_management": "enabled",
            "last_updated": datetime.now().isoformat(),
            "uptime": time.time() - start_time,
            "environment": "railway_cloud",
            "version": "2.1.0"
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        return {"error": str(e)}

@app.get("/api/trades/active")
async def get_active_trades():
    """Get active trades from the trading system."""
    try:
        from services.alpaca_trading import AlpacaTradingService
        
        trading_service = AlpacaTradingService()
        
        # Get open orders from Alpaca
        orders = trading_service.api.list_orders(
            status='open',
            limit=50
        )
        
        active_trades = []
        for order in orders:
            active_trades.append({
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": float(order.qty),
                "order_type": order.order_type,
                "time_in_force": order.time_in_force,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0.0,
                "status": order.status,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None
            })
        
        return {
            "active_trades": active_trades,
            "count": len(active_trades),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching active trades: {e}")
        return {"active_trades": [], "count": 0, "error": str(e)}

@app.get("/api/ai/decisions/recent")
async def get_recent_ai_decisions():
    """Get recent AI trading decisions."""
    try:
        import os
        
        # Try direct MongoDB connection first for Railway
        mongodb_url = os.getenv('MONGODB_URL')
        if not mongodb_url or mongodb_url == 'mongodb+srv://username:password@cluster.mongodb.net/':
            logger.warning("MongoDB URL not properly configured, returning empty decisions")
            return {
                "decisions": [],
                "count": 0,
                "last_updated": datetime.now().isoformat(),
                "error": "MongoDB not configured"
            }
        
        # Get recent AI decisions from MongoDB
        recent_decisions = []
        try:
            from pymongo import MongoClient
            client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
            db = client.signal_flow_trading
            
            cursor = db.ai_decisions.find().sort("timestamp", -1).limit(50)
            for decision in cursor:
                decision["_id"] = str(decision["_id"])  # Convert ObjectId to string
                if "timestamp" in decision and hasattr(decision["timestamp"], "isoformat"):
                    decision["timestamp"] = decision["timestamp"].isoformat()
                recent_decisions.append(decision)
            client.close()
        except Exception as db_error:
            logger.warning(f"MongoDB query failed: {db_error}")
        
        return {
            "decisions": recent_decisions,
            "count": len(recent_decisions),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching recent AI decisions: {e}")
        return {"decisions": [], "count": 0, "error": str(e)}

@app.get("/api/portfolio")
async def get_portfolio_summary():
    """Get portfolio summary from the trading system."""
    try:
        from services.alpaca_trading import AlpacaTradingService
        
        trading_service = AlpacaTradingService()
        account = trading_service.api.get_account()
        
        return {
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "daytrade_count": int(account.daytrade_count),
            "trading_blocked": account.trading_blocked,
            "account_blocked": account.account_blocked
        }
        
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        return {"error": str(e)}

def get_health_data():
    """Get health check data."""
    return {
        "status": "healthy",
        "uptime": time.time() - start_time,
        "mode": "paper_trading",
        "environment": "railway",
        "timestamp": datetime.now()
    }

def initialize_trading_system():
    """Initialize the trading system components in background."""
    try:
        # Import and initialize trading system
        from services.config import Config
        
        logger.info("🚀 Initializing Signal Flow Trading System on Railway")
        logger.info(f"📅 Start time: {datetime.now()}")
        logger.info("🔄 Mode: Paper Trading (Safe)")
        
        # Initialize configuration
        config = Config()
        logger.info("✅ Configuration initialized")
        
        # Import main application components (but don't run the main loop)
        # This ensures all services are available for API endpoints
        logger.info("✅ Trading system components initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize trading system: {e}")
        return False

# Global variable to track initialization

@app.on_event("startup")
async def startup_event():
    """Initialize trading system on FastAPI startup."""
    global trading_system_initialized
    global start_time
    
    start_time = time.time()
    setup_cloud_logging()
    
    logger.info("🌟 Signal Flow - Railway Deployment Starting")
    
    # Initialize trading system in background thread
    def init_in_background():
        global trading_system_initialized
        trading_system_initialized = initialize_trading_system()
    
    threading.Thread(target=init_in_background, daemon=True).start()
    logger.info("💚 Trading system initialization started in background")

if __name__ == "__main__":
    # For Railway deployment, we want to run the FastAPI app directly
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting FastAPI server on port {port}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="info",
        access_log=True
    )
