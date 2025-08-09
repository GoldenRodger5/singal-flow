#!/usr/bin/env python3
"""
Production Trading System Launcher
Starts the autonomous paper trading system with full monitoring.
"""

import os
import sys
import asyncio
import subprocess
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def print_banner():
    print("""
🚀 SIGNAL FLOW AUTONOMOUS TRADING SYSTEM
=========================================
📈 Paper Trading Mode: ACTIVE
🤖 Autonomous Trading: ENABLED
💰 Account: Alpaca Paper Trading
📊 Real-time Data: Polygon.io
🗄️  Database: MongoDB Atlas
=========================================
""")

def verify_production_safety():
    """Verify production safety before starting."""
    print("🔒 PRODUCTION SAFETY VERIFICATION")
    print("-" * 40)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    checks = []
    
    # Check paper trading is enabled
    paper_trading = os.getenv('PAPER_TRADING', 'false').lower() == 'true'
    paper_url = 'paper-api.alpaca.markets' in os.getenv('ALPACA_BASE_URL', '')
    
    if paper_trading:
        checks.append("✅ PAPER_TRADING=true")
    else:
        checks.append("❌ PAPER_TRADING not enabled - DANGEROUS!")
        
    if paper_url:
        checks.append("✅ Using paper-api.alpaca.markets")
    else:
        checks.append("❌ NOT using paper API - DANGEROUS!")
        
    # Check autonomous settings
    auto_execute = os.getenv('AUTO_EXECUTE_SIGNALS', 'false').lower() == 'true'
    if auto_execute:
        checks.append("✅ AUTO_EXECUTE_SIGNALS=true")
    else:
        checks.append("⚠️ AUTO_EXECUTE_SIGNALS=false (manual mode)")
    
    for check in checks:
        print(check)
    
    # Safety gate
    if not (paper_trading and paper_url):
        print("\n❌ SAFETY CHECK FAILED!")
        print("❌ System configured for LIVE trading - ABORTING!")
        return False
        
    print("\n✅ SAFETY CHECK PASSED - Paper trading confirmed")
    return True

def start_production_system():
    """Start all production components."""
    print("\n🔄 STARTING PRODUCTION COMPONENTS")
    print("-" * 40)
    
    processes = []
    
    try:
        # Start API server
        print("Starting API server...")
        api_process = subprocess.Popen([
            sys.executable, 
            "backend/scripts/production_api.py"
        ], cwd=project_root)
        processes.append(("API Server", api_process))
        
        # Start main trading system  
        print("Starting trading system...")
        trading_process = subprocess.Popen([
            sys.executable,
            "start.py"
        ], cwd=project_root)
        processes.append(("Trading System", trading_process))
        
        print(f"✅ {len(processes)} components started")
        
        # Monitor processes
        print("\n📊 MONITORING SYSTEM STATUS")
        print("-" * 40)
        print("Press Ctrl+C to shutdown system")
        
        # Keep running and monitor
        while True:
            import time
            time.sleep(10)
            
            # Check process health
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} process died with code {process.poll()}")
                    
            print(f"🟢 {datetime.now().strftime('%H:%M:%S')} - System running")
            
    except KeyboardInterrupt:
        print("\n🛑 SHUTDOWN SIGNAL RECEIVED")
        print("-" * 40)
        
        # Graceful shutdown
        for name, process in processes:
            print(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=10)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️ Force killing {name}...")
                process.kill()
                
        print("✅ All systems stopped safely")

def main():
    print_banner()
    
    # Safety verification
    if not verify_production_safety():
        print("\n❌ PRODUCTION START ABORTED")
        return 1
        
    # Start system
    try:
        start_production_system()
        return 0
    except Exception as e:
        print(f"\n❌ PRODUCTION START FAILED: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
