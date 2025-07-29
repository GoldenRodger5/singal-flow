#!/usr/bin/env python3
"""
Enhanced Trading System Startup Script
Start the system in different modes based on your needs.
"""
import asyncio
import sys
import os
from pathlib import Path
import argparse
from datetime import datetime

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.config import Config
from services.system_orchestrator import (
    TradingSystemOrchestrator,
    SystemConfiguration,
    SystemMode,
    create_and_start_trading_system
)
from services.automated_trading_manager import AutomationMode
from loguru import logger


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # File logging
    log_file = f"logs/trading_system_{datetime.now().strftime('%Y%m%d')}.log"
    os.makedirs("logs", exist_ok=True)
    
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="30 days"
    )


def check_environment():
    """Check if environment is properly configured."""
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['ANTHROPIC_API_KEY', 'BROKER_API_KEY']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        logger.error(f"❌ Missing required environment variables: {missing_required}")
        logger.error("Please set these in your .env file or environment")
        return False
    
    if missing_optional:
        logger.warning(f"⚠️  Missing optional environment variables: {missing_optional}")
        logger.warning("Some features may be limited")
    
    logger.info("✅ Environment check passed")
    return True


async def start_analysis_mode():
    """Start system in analysis-only mode."""
    logger.info("🔍 Starting in ANALYSIS_ONLY mode")
    
    config = Config()
    orchestrator = await create_and_start_trading_system(
        config,
        mode=SystemMode.ANALYSIS_ONLY,
        automation_mode=AutomationMode.ANALYSIS_ONLY
    )
    
    logger.info("📊 Analysis mode running - generating signals and insights")
    logger.info("💡 No trades will be executed, only analysis provided")
    
    return orchestrator


async def start_paper_trading():
    """Start system in paper trading mode."""
    logger.info("📝 Starting in PAPER_TRADING mode")
    
    config = Config()
    orchestrator = await create_and_start_trading_system(
        config,
        mode=SystemMode.PAPER_TRADING,
        automation_mode=AutomationMode.PAPER_TRADING
    )
    
    logger.info("🎯 Paper trading active - simulated trades will be executed")
    logger.info("💰 No real money at risk - perfect for testing strategies")
    
    return orchestrator


async def start_supervised_trading():
    """Start system in supervised trading mode."""
    logger.info("👥 Starting in SUPERVISED mode")
    
    config = Config()
    orchestrator = await create_and_start_trading_system(
        config,
        mode=SystemMode.LIVE_TRADING,
        automation_mode=AutomationMode.SUPERVISED
    )
    
    logger.info("⚠️  LIVE TRADING with supervision - human approval required")
    logger.info("💸 Real money trades - be careful!")
    
    return orchestrator


async def start_automated_trading():
    """Start system in fully automated mode."""
    logger.info("🤖 Starting in FULLY_AUTOMATED mode")
    
    # Extra confirmation for automated mode
    print("\n" + "="*60)
    print("⚠️  WARNING: FULLY AUTOMATED LIVE TRADING")
    print("="*60)
    print("This mode will execute real trades with real money")
    print("without human approval. Make sure you:")
    print("1. Have thoroughly tested your strategies")
    print("2. Set appropriate safety limits")
    print("3. Monitor the system regularly")
    print("4. Have stop-loss mechanisms in place")
    print("="*60)
    
    confirmation = input("Type 'I UNDERSTAND THE RISKS' to continue: ")
    
    if confirmation != "I UNDERSTAND THE RISKS":
        logger.info("❌ Automated trading cancelled by user")
        return None
    
    config = Config()
    orchestrator = await create_and_start_trading_system(
        config,
        mode=SystemMode.LIVE_TRADING,
        automation_mode=AutomationMode.FULLY_AUTOMATED
    )
    
    logger.info("🚨 FULLY AUTOMATED TRADING ACTIVE")
    logger.info("💸 System will execute real trades automatically")
    
    return orchestrator


async def monitor_system(orchestrator: TradingSystemOrchestrator):
    """Monitor the running system."""
    logger.info("📡 Starting system monitoring...")
    
    try:
        while orchestrator.is_running:
            # Get system status
            status = orchestrator.get_system_status()
            
            # Log key metrics
            logger.info(f"📊 Status: {status['orchestrator']['running']}")
            logger.info(f"⏰ Window: {status['trading_window']['current']}")
            logger.info(f"📈 Trades today: {status['session_stats']['trades_executed']}")
            
            # Check for any issues
            if not status['health']['healthy']:
                logger.warning(f"⚠️  Health issues: {status['health']['issues']}")
            
            # Wait before next check
            await asyncio.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Error in monitoring: {e}")


async def main():
    """Main function to start the trading system."""
    parser = argparse.ArgumentParser(description="Enhanced Trading System")
    parser.add_argument(
        'mode',
        choices=['analysis', 'paper', 'supervised', 'automated'],
        help='Trading mode to start'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--no-monitor',
        action='store_true',
        help='Start without monitoring loop'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Welcome message
    print("\n" + "="*60)
    print("🎯 Enhanced Trading System")
    print("="*60)
    print("🧠 AI-Powered Trading with LLM Routing")
    print("⏰ Time-Window Optimized Strategies")
    print("🤖 Intelligent Automation & Safety")
    print("="*60)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Start system based on mode
    orchestrator = None
    
    try:
        if args.mode == 'analysis':
            orchestrator = await start_analysis_mode()
        elif args.mode == 'paper':
            orchestrator = await start_paper_trading()
        elif args.mode == 'supervised':
            orchestrator = await start_supervised_trading()
        elif args.mode == 'automated':
            orchestrator = await start_automated_trading()
        
        if orchestrator is None:
            logger.error("Failed to start system")
            return 1
        
        logger.info("✅ System started successfully!")
        
        # Show system status
        status = orchestrator.get_system_status()
        logger.info(f"📊 System Status: {status}")
        
        # Start monitoring if requested
        if not args.no_monitor:
            await monitor_system(orchestrator)
        else:
            logger.info("📡 Monitoring disabled - system running in background")
            # Keep the system running
            while orchestrator.is_running:
                await asyncio.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("🛑 System shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        return 1
    finally:
        # Cleanup
        if orchestrator:
            await orchestrator.stop_system()
    
    logger.info("👋 Enhanced Trading System stopped")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
