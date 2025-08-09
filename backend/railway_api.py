#!/usr/bin/env python3
"""
Railway Deployment Entry Point for SignalFlow Trading System
Simplified startup with better error handling for cloud deployment
"""
import os
import sys
import uvicorn
from pathlib import Path

# Set up paths for Railway environment
project_root = Path(__file__).parent.parent
backend_path = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

# Set environment for production
os.environ['ENVIRONMENT'] = 'production'
os.environ['PYTHONPATH'] = f"{backend_path}:{project_root}"

def main():
    """Main entry point for Railway deployment."""
    print("🚀 Starting SignalFlow Trading System on Railway...")
    print(f"📁 Project Root: {project_root}")
    print(f"🔧 Backend Path: {backend_path}")
    print(f"🌐 Port: {os.getenv('PORT', 8000)}")
    
    try:
        # Import and run the production API
        uvicorn.run(
            "scripts.production_api:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            workers=1,
            timeout_keep_alive=120,  # Increased from 30 to 120 seconds
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Railway startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
