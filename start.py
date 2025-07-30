#!/usr/bin/env python3
"""
Railway deployment entry point - Simplified
"""
import os
import sys
import time
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Change to backend directory for relative imports
os.chdir(str(backend_dir))

try:
    # Import required modules
    import uvicorn
    from fastapi import FastAPI
    from datetime import datetime
    from loguru import logger
    
    # Set up basic logging
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time} | {level} | {message}")
    
    # Create simple FastAPI app for health check
    app = FastAPI(title="Signal Flow Trading System", version="1.0.0")
    
    @app.get("/")
    async def root():
        return {"status": "Signal Flow Trading Bot is running", "timestamp": datetime.now()}
    
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "mode": "paper_trading",
            "environment": "railway"
        }
    
    @app.get("/api/holdings")
    async def get_holdings():
        # Basic holdings endpoint that returns empty for now
        return {"holdings": [], "total_value": 0.0}
    
    @app.get("/api/portfolio")
    async def get_portfolio():
        # Basic portfolio endpoint
        return {
            "equity": 100000.0,
            "buying_power": 100000.0,
            "cash": 100000.0,
            "portfolio_value": 100000.0
        }
    
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Starting Signal Flow on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
        
except Exception as e:
    print(f"Error starting application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
