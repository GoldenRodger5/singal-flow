#!/usr/bin/env python3
"""
Enhanced Signal Flow Trading System Startup
Runs with optimized components and regime awareness.
"""
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Start enhanced trading system."""
    logger.info("🚀 Starting Enhanced Signal Flow Trading System")
    logger.info("=" * 60)
    
    try:
        # Import main orchestrator
        from main import SignalFlowOrchestrator
        
        # Create orchestrator instance
        orchestrator = SignalFlowOrchestrator()
        
        # Check if enhanced components are available
        if hasattr(orchestrator.trade_recommender, 'regime_detector'):
            logger.info("✅ Enhanced components active:")
            logger.info("   • Market regime detection")
            logger.info("   • Modern technical indicators")
            logger.info("   • Kelly Criterion position sizing")
            logger.info("   • Volatility-scaled risk management")
        else:
            logger.info("⚠️  Running in compatibility mode with traditional indicators")
        
        # Start the system
        await orchestrator.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down enhanced trading system")
    except Exception as e:
        logger.error(f"❌ Error in enhanced startup: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
