#!/usr/bin/env python3
"""
Signal Flow Pro - Complete Trading System Launcher
Ultra-fast startup with all components
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import threading

def print_banner():
    """Print startup banner."""
    banner = """
    ███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗         ███████╗██╗      ██████╗ ██╗    ██╗
    ██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║         ██╔════╝██║     ██╔═══██╗██║    ██║
    ███████╗██║██║  ███╗██╔██╗ ██║███████║██║         █████╗  ██║     ██║   ██║██║ █╗ ██║
    ╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║         ██╔══╝  ██║     ██║   ██║██║███╗██║
    ███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗    ██║     ███████╗╚██████╔╝╚███╔███╔╝
    ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝    ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ 
    
    🚀 ULTRA-FAST TRADING SYSTEM 🚀
    """
    print(banner)
    print("⚡ Real-time signals • 🔔 Instant notifications • 💰 One-click execution")
    print("="*80)

def check_and_install_dependencies():
    """Quickly check and install all required packages."""
    print("🔧 Checking dependencies...")
    
    required_packages = [
        'streamlit>=1.28.0',
        'plotly>=5.0.0',
        'pandas>=1.5.0',
        'numpy>=1.20.0',
        'sqlite3'  # Built-in
    ]
    
    missing = []
    for package in required_packages:
        package_name = package.split('>=')[0]
        if package_name == 'sqlite3':  # Skip sqlite3 as it's built-in
            continue
        try:
            __import__(package_name)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"📦 Installing: {', '.join(missing)}")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", *missing
        ])
        print("✅ All dependencies ready!")
    else:
        print("✅ All dependencies already installed!")

def start_notification_service():
    """Start the background notification service."""
    print("🔔 Starting notification service...")
    try:
        # Start notification service in background
        notification_process = subprocess.Popen([
            sys.executable, "notification_service.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ Notification service started!")
        return notification_process
    except Exception as e:
        print(f"⚠️  Notification service failed: {e}")
        return None

def launch_trading_ui():
    """Launch the main trading UI."""
    print("🚀 Launching Signal Flow Pro UI...")
    print("📊 Real-time trading interface loading...")
    
    cmd = [
        "streamlit", "run", "enhanced_trading_ui.py",
        "--server.headless", "false",
        "--server.address", "localhost",
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
        "--theme.primaryColor", "#00c851",
        "--theme.backgroundColor", "#0e1117",
        "--theme.secondaryBackgroundColor", "#262730",
        "--theme.textColor", "#fafafa"
    ]
    
    try:
        print("\n" + "="*60)
        print("🎯 SIGNAL FLOW PRO IS READY!")
        print("🌐 Opening in your browser at: http://localhost:8501")
        print("⚡ Ultra-fast execution mode ACTIVE")
        print("🔔 Desktop notifications ENABLED")
        print("💰 One-click trading READY")
        print("="*60)
        print("\n⏳ Starting trading interface...")
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Signal Flow Pro...")
        print("💰 Happy trading! See you next time.")
    except FileNotFoundError:
        print("❌ Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("✅ Streamlit installed! Restarting...")
        subprocess.run(cmd, check=True)

def create_env_file_if_needed():
    """Create .env file with default trading parameters if it doesn't exist."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚙️  Creating default trading configuration...")
        
        default_config = """# Signal Flow Pro Trading Configuration
TICKER_PRICE_MIN=1
TICKER_PRICE_MAX=50
TRADING_START_TIME=09:45
TRADING_END_TIME=11:30
MAX_POSITION_SIZE=10000
MIN_CONFIDENCE_THRESHOLD=7.5
AUTO_EXECUTE_THRESHOLD=9.5
RISK_MULTIPLIER=1.0
NOTIFICATION_ENABLED=true
SOUND_NOTIFICATIONS=true
"""
        
        with open(env_file, 'w') as f:
            f.write(default_config)
        
        print("✅ Default configuration created in .env file")
        print("🔧 You can customize these settings by editing .env")
    else:
        print("✅ Configuration loaded from .env file")

def run_system_check():
    """Run a quick system compatibility check."""
    print("🔍 Running system check...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        print(f"✅ Python {python_version.major}.{python_version.minor} - Compatible")
    else:
        print(f"⚠️  Python {python_version.major}.{python_version.minor} - May have issues (3.8+ recommended)")
    
    # Check available memory (basic)
    try:
        import psutil
        memory = psutil.virtual_memory()
        if memory.available > 1e9:  # 1GB
            print(f"✅ Memory: {memory.available/1e9:.1f}GB available")
        else:
            print(f"⚠️  Memory: {memory.available/1e9:.1f}GB available (low)")
    except ImportError:
        print("ℹ️  Memory check skipped (psutil not installed)")
    
    print("✅ System check complete!")

def main():
    """Main launcher function."""
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Print startup banner
    print_banner()
    
    # Run system check
    run_system_check()
    print()
    
    # Create configuration if needed
    create_env_file_if_needed()
    print()
    
    # Install dependencies
    check_and_install_dependencies()
    print()
    
    # Start notification service
    notification_process = start_notification_service()
    time.sleep(2)  # Give notification service time to start
    print()
    
    try:
        # Launch main UI
        launch_trading_ui()
    finally:
        # Clean up notification service
        if notification_process:
            print("🔕 Stopping notification service...")
            notification_process.terminate()
            print("✅ Cleanup complete!")

if __name__ == "__main__":
    main()
