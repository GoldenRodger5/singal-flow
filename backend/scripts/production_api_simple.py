"""
Simplified Production FastAPI Server - Step 1: Basic Setup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

# Initialize FastAPI app
app = FastAPI(
    title="Signal Flow Trading System - Production API",
    description="Real-time trading system with AI agents and health monitoring",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(content={
        "message": "Signal Flow Trading System API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "environment": "production"
    })

@app.get("/api/status")
async def get_api_status():
    """Basic API status endpoint"""
    return JSONResponse(content={
        "api_status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    })

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting simplified FastAPI server...")
    uvicorn.run(
        "production_api_simple:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info"
    )
