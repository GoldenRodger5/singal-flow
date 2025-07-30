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
railway_script = backend_dir / "railway_start.py"

# Execute the railway start script directly
if __name__ == "__main__":
    try:
        # Run the railway_start.py script directly
        os.chdir(str(backend_dir))
        sys.path.insert(0, str(backend_dir))
        exec(open(railway_script).read())
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
