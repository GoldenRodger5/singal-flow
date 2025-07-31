#!/usr/bin/env python3
"""
Minimal Railway test script
"""
import os
import sys
from datetime import datetime

print(f"🚀 Railway Test Started - {datetime.now()}")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print(f"PORT environment variable: {os.getenv('PORT', 'NOT SET')}")

# Test basic imports
try:
    import fastapi
    print(f"✅ FastAPI version: {fastapi.__version__}")
except ImportError as e:
    print(f"❌ FastAPI import failed: {e}")

try:
    import uvicorn
    print(f"✅ Uvicorn imported successfully")
except ImportError as e:
    print(f"❌ Uvicorn import failed: {e}")

# Test basic FastAPI app
try:
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"message": "Railway test successful"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    print("✅ FastAPI app created successfully")
    
    # Start server if PORT is set (Railway environment)
    if os.getenv('PORT'):
        import uvicorn
        print(f"🚀 Starting server on port {os.getenv('PORT')}")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=int(os.getenv('PORT')),
            log_level="info"
        )
    else:
        print("🏃 Running in test mode (no PORT env var)")

except Exception as e:
    print(f"❌ FastAPI test failed: {e}")
    sys.exit(1)

print("✅ All tests passed")
