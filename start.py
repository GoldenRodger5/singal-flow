#!/usr/bin/env python3
"""
Railway deployment entry point
"""
import os
import sys
import time
import threading
from pathlib import Path
from loguru import logger

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Change to backend directory
os.chdir(backend_dir)

if __name__ == "__main__":
    # Import railway start functions after path setup
    from railway_start import setup_cloud_logging, start_health_server, start_trading_system
    
    # Record start time for health checks
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
