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

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "uptime": time.time() - start_time,
        "mode": "paper_trading",
        "environment": "railway"
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

def start_health_server():
    """Start health check server in background."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

def start_trading_system():
    """Start the main trading system."""
    try:
        # Import and start trading system
        from services.config import Config
        
        logger.info("🚀 Starting Signal Flow Trading System on Railway")
        logger.info(f"📅 Start time: {datetime.now()}")
        logger.info("🔄 Mode: Paper Trading (Safe)")
        
        # Initialize configuration
        config = Config()
        
        # Start the main trading application
        logger.info("✅ Starting main trading application...")
        
        # Import main application
        import main
        
        logger.info("✅ Trading system initialized successfully")
        logger.info("🎯 System will run continuously until stopped")
        
        # Keep the system running
        try:
            while True:
                time.sleep(60)  # Check every minute
                logger.debug("🔄 System health check - running normally")
                    
        except KeyboardInterrupt:
            logger.info("Graceful shutdown requested")
        except Exception as e:
            logger.error(f"Trading system error: {e}")
            # Auto-restart on error
            time.sleep(30)
            start_trading_system()
            
    except Exception as e:
        logger.error(f"Failed to start trading system: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Record start time
    start_time = time.time()
    
    # Setup logging
    setup_cloud_logging()
    
    logger.info("🌟 Signal Flow - Railway Deployment Starting")
    
    # Start health check server in background
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    logger.info(f"💚 Health check server started on port {os.environ.get('PORT', 8000)}")
    
    # Give health server time to start
    time.sleep(2)
    
    # Start main trading system
    start_trading_system()
