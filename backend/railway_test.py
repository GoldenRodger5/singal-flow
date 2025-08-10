#!/usr/bin/env python3
"""
Railway Cloud Deployment Script - MINIMAL TEST VERSION
Test basic FastAPI functionality without heavy service imports
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from loguru import logger
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Global variables
start_time = time.time()

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

# Health check API for Railway
app = FastAPI(title="Signal Flow Trading Bot - Test", version="1.0.0")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Signal Flow Trading Bot is running", "timestamp": datetime.now(), "mode": "test"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint for Railway."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time() - start_time,
        "mode": "test_deployment",
        "environment": "railway"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify deployment."""
    return {
        "message": "Railway deployment test successful",
        "timestamp": datetime.now().isoformat(),
        "environment_vars": {
            "PORT": os.getenv('PORT', 'Not Set'),
            "RAILWAY_ENVIRONMENT": os.getenv('RAILWAY_ENVIRONMENT', 'Not Set')
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize on FastAPI startup."""
    global start_time
    
    start_time = time.time()
    setup_cloud_logging()
    
    logger.info("🌟 Signal Flow - Railway Test Deployment Starting")

if __name__ == "__main__":
    # For Railway deployment
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting FastAPI test server on port {port}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="info",
        access_log=True
    )
