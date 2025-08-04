#!/usr/bin/env python3
"""
Railway deployment entry point - Full Trading System
"""
import os
import sys
import subprocess
from pathlib import Path

# Add backend directory to Python path  
backend_dir = Path(__file__).parent / "backend"
production_script = backend_dir / "scripts" / "production_api.py"

# Execute the production API script directly
if __name__ == "__main__":
    try:
        # Change to backend directory
        os.chdir(str(backend_dir))
        sys.path.insert(0, str(backend_dir))
        
        # Run uvicorn server directly with the production API
        import uvicorn
        uvicorn.run(
            "scripts.production_api:app",
            host="0.0.0.0", 
            port=int(os.environ.get("PORT", 8000)),
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
