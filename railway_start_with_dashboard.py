#!/usr/bin/env python3
"""
Railway Cloud Deployment Script with Streamlit Dashboard
Starts both the trading system and web dashboard
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
import subprocess

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

@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect to Streamlit dashboard."""
    dashboard_port = int(os.environ.get("STREAMLIT_PORT", 8501))
    return {
        "message": "Dashboard available on port 8501",
        "dashboard_url": f"/dashboard-app",
        "port": dashboard_port
    }

def start_health_server():
    """Start health check server in background."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

def start_streamlit_dashboard():
    """Start Streamlit dashboard in background."""
    try:
        logger.info("🎨 Starting Streamlit dashboard...")
        
        # Install streamlit if not available
        try:
            import streamlit
        except ImportError:
            logger.info("Installing Streamlit...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'streamlit', 'plotly'], check=True)
        
        # Start Streamlit
        dashboard_port = int(os.environ.get("STREAMLIT_PORT", 8501))
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', 
            'railway_dashboard.py',
            '--server.port', str(dashboard_port),
            '--server.address', '0.0.0.0',
            '--server.headless', 'true',
            '--server.enableCORS', 'false',
            '--server.enableXsrfProtection', 'false'
        ]
        
        logger.info(f"🎨 Dashboard will be available on port {dashboard_port}")
        subprocess.run(cmd)
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")

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
    
    logger.info("🌟 Signal Flow - Railway Deployment with Dashboard Starting")
    
    # Determine which service to run based on environment
    service_type = os.environ.get("RAILWAY_SERVICE_TYPE", "trading")
    
    if service_type == "dashboard":
        # Run only dashboard service
        logger.info("🎨 Starting Dashboard Service")
        start_streamlit_dashboard()
    else:
        # Run trading system with health check
        logger.info("🚀 Starting Trading System Service")
        
        # Start health check server in background
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        logger.info(f"💚 Health check server started on port {os.environ.get('PORT', 8000)}")
        
        # Give health server time to start
        time.sleep(2)
        
        # Start main trading system
        start_trading_system()
