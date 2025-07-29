#!/usr/bin/env python3
"""
Fast Trading UI Launcher
Ultra-optimized startup for immediate trading
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check and install required packages quickly."""
    required_packages = [
        'streamlit',
        'plotly',
        'pandas',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  Installing missing packages: {', '.join(missing_packages)}")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", *missing_packages
        ])
        print("✅ Dependencies installed!")

def launch_trading_ui():
    """Launch the enhanced trading UI with optimal settings."""
    print("🚀 Starting Signal Flow Pro Trading UI...")
    print("⚡ Ultra-fast execution mode enabled")
    print("📊 Real-time signals and notifications active")
    print("\n" + "="*50)
    print("🎯 READY TO TRADE - UI will open in your browser")
    print("="*50 + "\n")
    
    # Launch Streamlit with optimized settings
    cmd = [
        "streamlit", "run", "enhanced_trading_ui.py",
        "--server.headless", "false",
        "--server.runOnSave", "true",
        "--server.address", "localhost",
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
        "--theme.primaryColor", "#00c851",
        "--theme.backgroundColor", "#0e1117",
        "--theme.secondaryBackgroundColor", "#262730",
        "--theme.textColor", "#fafafa"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Trading UI stopped. Happy trading!")
    except FileNotFoundError:
        print("❌ Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("✅ Streamlit installed! Restarting...")
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Quick setup
    check_dependencies()
    
    # Launch
    launch_trading_ui()
