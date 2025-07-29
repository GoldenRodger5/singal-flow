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

def start_health_server():
    """Start health check server in background."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

def start_trading_system():
    """Start the main trading system."""
    try:
        # Import and start trading system
        from services.system_orchestrator import TradingSystemOrchestrator
        from utils.config import Config
        
        logger.info("🚀 Starting Signal Flow Trading System on Railway")
        logger.info(f"📅 Start time: {datetime.now()}")
        logger.info("🔄 Mode: Paper Trading (Safe)")
        
        # Initialize configuration
        config = Config()
        
        # Create and start orchestrator
        orchestrator = TradingSystemOrchestrator(config)
        
        logger.info("✅ Trading system initialized successfully")
        logger.info("🎯 System will run continuously until stopped")
        
        # Start the orchestrator
        orchestrator.start()
        
        # Keep the system running
        try:
            while True:
                time.sleep(60)  # Check every minute
                if not orchestrator.is_running():
                    logger.warning("Trading system stopped, restarting...")
                    orchestrator.start()
                    
        except KeyboardInterrupt:
            logger.info("Graceful shutdown requested")
            orchestrator.stop()
            
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
