#!/usr/bin/env python3
"""
Launch Real Trading Dashboard
Complete trading interface with live data and real buy/sell controls
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the real trading dashboard."""
    print("🚀 Launching Signal Flow Real Trading Dashboard...")
    
    # Set working directory to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit found")
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit", "plotly"], check=True)
        print("✅ Streamlit installed")
    
    # Launch dashboard
    dashboard_file = project_root / "real_trading_dashboard.py"
    
    if not dashboard_file.exists():
        print(f"❌ Dashboard file not found: {dashboard_file}")
        return
    
    print("🌐 Starting dashboard on http://localhost:8501")
    print("💡 Use the sidebar controls for real trading actions")
    print("⚠️  This is LIVE TRADING - all actions are real!")
    print()
    
    # Run streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_file),
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("\n✅ Dashboard stopped")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")

if __name__ == "__main__":
    main()
