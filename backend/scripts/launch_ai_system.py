#!/usr/bin/env python3
"""
Signal Flow AI Trading System Launcher
Starts the main trading system and learning dashboard.
"""
import asyncio
import subprocess
import sys
import signal
import os
from datetime import datetime
from loguru import logger

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.logger_setup import setup_logger


class SignalFlowLauncher:
    """Launcher for the complete Signal Flow AI system."""
    
    def __init__(self):
        """Initialize the launcher."""
        setup_logger()
        self.processes = []
        self.is_running = False
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def start_trading_system(self):
        """Start the main trading system."""
        logger.info("Starting Signal Flow Trading System...")
        
        # Start main trading system
        main_process = subprocess.Popen([
            sys.executable, 'main.py'
        ], cwd=project_root)
        
        self.processes.append(('Trading System', main_process))
        return main_process
    
    def start_learning_dashboard(self):
        """Start the learning dashboard API."""
        logger.info("Starting AI Learning Dashboard...")
        
        # Start learning dashboard
        dashboard_process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 
            'services.learning_dashboard_api:app',
            '--host', '0.0.0.0',
            '--port', '8001',
            '--reload'
        ], cwd=project_root)
        
        self.processes.append(('Learning Dashboard', dashboard_process))
        return dashboard_process
    
    def check_dependencies(self):
        """Check if all dependencies are installed."""
        logger.info("Checking dependencies...")
        
        required_modules = [
            'asyncio', 'fastapi', 'uvicorn', 'pandas', 'numpy',
            'requests', 'loguru', 'python-dotenv', 'schedule'
        ]
        
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module.replace('-', '_'))
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            logger.error(f"Missing required modules: {missing_modules}")
            logger.info("Install with: pip install " + " ".join(missing_modules))
            return False
        
        logger.info("All dependencies satisfied")
        return True
    
    def check_configuration(self):
        """Check if configuration is valid."""
        logger.info("Checking configuration...")
        
        try:
            from services.config import Config
            config = Config()
            
            validation = config.validate_config()
            
            if not validation['valid']:
                logger.error(f"Configuration validation failed: {validation['missing_keys']}")
                logger.info("Please check your .env file and ensure all required API keys are set")
                return False
            
            logger.info(f"Configuration valid - Environment: {validation['environment']}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration check failed: {e}")
            return False
    
    def show_startup_info(self):
        """Show startup information."""
        print("\n" + "="*70)
        print("🚀 SIGNAL FLOW AI TRADING SYSTEM")
        print("="*70)
        print("💡 Comprehensive AI-powered trading with continuous learning")
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📊 LEARNING DASHBOARD:")
        print("   URL: http://localhost:8001/docs")
        print("   Monitor AI learning progress, performance metrics, and insights")
        print("\n🔧 API ENDPOINTS:")
        print("   • GET /api/learning/status - Learning system status")
        print("   • GET /api/learning/metrics - Detailed learning metrics")
        print("   • GET /api/learning/performance - Performance analytics")
        print("   • GET /api/learning/insights - Daily insights & recommendations")
        print("   • POST /api/learning/trigger-learning - Manual learning cycle")
        print("   • POST /api/learning/trigger-backtest - Manual backtest")
        print("\n💰 TRADING MODES:")
        print("   • Auto Trading: Enabled" if os.getenv('AUTO_TRADING_ENABLED', 'false').lower() == 'true' else "   • Auto Trading: Disabled")
        print("   • Interactive Trading: Enabled" if os.getenv('INTERACTIVE_TRADING_ENABLED', 'true').lower() == 'true' else "   • Interactive Trading: Disabled")
        print("   • Paper Trading: Enabled" if os.getenv('PAPER_TRADING', 'true').lower() == 'true' else "   • Paper Trading: Disabled (LIVE TRADING)")
        print("\n🧠 AI LEARNING FEATURES:")
        print("   • Real-time decision logging with detailed reasoning")
        print("   • Adaptive confidence scoring based on historical performance")
        print("   • Continuous model weight optimization to prevent overfitting")
        print("   • Historical backtesting with strategy comparison")
        print("   • Daily insights and performance analytics")
        print("   • Automatic strategy improvements based on learning")
        print("\n📈 EXPECTED IMPROVEMENTS:")
        print("   • Prediction accuracy improves over time")
        print("   • Risk-adjusted returns optimize automatically")
        print("   • Confidence scores become better calibrated")
        print("   • Entry criteria adapt to market conditions")
        print("="*70)
        print("🔴 Press Ctrl+C to stop the system")
        print("="*70 + "\n")
    
    def monitor_processes(self):
        """Monitor running processes."""
        while self.is_running:
            for name, process in self.processes:
                if process.poll() is not None:
                    logger.error(f"{name} process has terminated unexpectedly")
                    self.shutdown()
                    return
            
            asyncio.sleep(5)
    
    def shutdown(self):
        """Shutdown all processes."""
        logger.info("Shutting down Signal Flow AI system...")
        self.is_running = False
        
        for name, process in self.processes:
            if process.poll() is None:
                logger.info(f"Terminating {name}...")
                process.terminate()
                
                # Give process time to terminate gracefully
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {name}...")
                    process.kill()
        
        logger.info("All processes terminated")
    
    async def run(self):
        """Run the complete system."""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check dependencies and configuration
        if not self.check_dependencies():
            return False
        
        if not self.check_configuration():
            return False
        
        # Show startup information
        self.show_startup_info()
        
        try:
            # Start all components
            self.start_trading_system()
            await asyncio.sleep(2)  # Give trading system time to start
            
            self.start_learning_dashboard()
            await asyncio.sleep(2)  # Give dashboard time to start
            
            self.is_running = True
            
            logger.info("🚀 Signal Flow AI Trading System is now running!")
            logger.info("📊 Learning Dashboard available at: http://localhost:8001/docs")
            logger.info("🧠 AI learning will begin after collecting trade data")
            
            # Monitor processes
            while self.is_running:
                for name, process in self.processes:
                    if process.poll() is not None:
                        logger.error(f"{name} process has terminated unexpectedly")
                        self.shutdown()
                        return False
                
                await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error running system: {e}")
            self.shutdown()
            return False
        
        return True


async def main():
    """Main entry point."""
    launcher = SignalFlowLauncher()
    
    try:
        success = await launcher.run()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        launcher.shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        launcher.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
