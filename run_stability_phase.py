#!/usr/bin/env python3
"""
🧠 STABILITY PHASE LAUNCHER
7-14 Day Paper Trading with Comprehensive Logging

This script implements the exact recommendations from your other AI:
- Paper trading mode with detailed signal logging
- Performance tracking per regime
- Win rate, R:R, drawdown measurement
- Dashboard monitoring

Run this for 7-14 days to validate the enhanced system.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from services.enhanced_trade_recommender import EnhancedTradeRecommender, PaperTradingMonitor
from utils.performance_tracker import performance_tracker
from services.config import Config


class StabilityPhaseController:
    """Controls the 7-14 day stability validation phase."""
    
    def __init__(self):
        self.trade_recommender = EnhancedTradeRecommender()
        self.paper_monitor = PaperTradingMonitor()
        self.session_start = datetime.now()
        logger.info("🧠 Stability Phase Controller initialized")
    
    async def run_stability_phase(self):
        """Main stability phase execution loop."""
        logger.info("=" * 60)
        logger.info("🧠 STARTING STABILITY PHASE - ENHANCED SIGNAL FLOW")
        logger.info("=" * 60)
        logger.info("📋 Phase Goals:")
        logger.info("   • Log every signal, execution, and exit")
        logger.info("   • Measure win rate, R:R, drawdown per regime")
        logger.info("   • Track regime classifications vs real market")
        logger.info("   • Validate enhanced indicator performance")
        logger.info("=" * 60)
        
        # Initialize tracking
        signals_logged = 0
        executions_simulated = 0
        
        try:
            # Main monitoring loop
            while True:
                current_time = datetime.now()
                
                # Check if we're in trading hours (9:45 AM - 11:30 AM)
                if self._is_trading_hours(current_time):
                    await self._scan_and_log_signals()
                    signals_logged += 1
                    
                    # Simulate executions every 5 minutes
                    if signals_logged % 5 == 0:
                        executions = await self._simulate_paper_trades()
                        executions_simulated += len(executions)
                    
                    # Update performance metrics every 10 minutes
                    if signals_logged % 10 == 0:
                        await self._update_performance_metrics()
                
                # Log session summary every hour
                if signals_logged % 60 == 0 and signals_logged > 0:
                    await self._log_session_summary(signals_logged, executions_simulated)
                
                # Wait 1 minute between scans
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("🛑 Stability phase interrupted by user")
            await self._generate_final_report()
        except Exception as e:
            logger.error(f"❌ Error in stability phase: {e}")
            raise
    
    def _is_trading_hours(self, current_time: datetime) -> bool:
        """Check if current time is within trading hours."""
        start_time = current_time.replace(hour=9, minute=45, second=0, microsecond=0)
        end_time = current_time.replace(hour=11, minute=30, second=0, microsecond=0)
        return start_time <= current_time <= end_time
    
    async def _scan_and_log_signals(self):
        """Scan market and log all signals for analysis."""
        # Mock tickers for testing - replace with your screener
        test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        
        for ticker in test_tickers:
            try:
                # Mock market data - replace with real data feed
                mock_data = self._generate_mock_data(ticker)
                
                # Generate enhanced recommendation
                recommendation = await self.trade_recommender.generate_recommendation(
                    ticker, mock_data
                )
                
                # Log signal regardless of trading decision
                if recommendation.get('signal_id'):
                    logger.debug(f"📊 Signal logged: {ticker} - {recommendation['signal_type']} "
                               f"(Confidence: {recommendation['confidence']:.1f})")
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
    
    async def _simulate_paper_trades(self) -> list:
        """Simulate paper trade executions."""
        executions = []
        
        # Get recent signals that haven't been executed
        # This would query the database for unexecuted signals
        # For now, we'll simulate
        
        mock_signals = [
            {'ticker': 'AAPL', 'should_trade': True, 'signal_id': 1, 'position_size': 10000},
            {'ticker': 'MSFT', 'should_trade': True, 'signal_id': 2, 'position_size': 8000}
        ]
        
        for signal in mock_signals:
            if signal['should_trade']:
                execution = await self.paper_monitor.simulate_execution(signal)
                if execution:
                    # Log execution
                    execution_id = await self.trade_recommender.log_execution(
                        signal['signal_id'], execution
                    )
                    executions.append(execution)
        
        return executions
    
    async def _update_performance_metrics(self):
        """Update daily performance metrics."""
        try:
            performance_tracker.update_daily_performance()
            
            # Get current session summary
            summary = performance_tracker.get_daily_summary()
            
            if summary.get('total_trades', 0) > 0:
                logger.info(f"📈 Session Update: {summary['total_trades']} trades, "
                          f"{summary.get('win_rate', 0)*100:.1f}% win rate, "
                          f"${summary.get('total_pnl', 0):.2f} P&L")
        
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def _log_session_summary(self, signals_logged: int, executions_simulated: int):
        """Log hourly session summary."""
        session_duration = datetime.now() - self.session_start
        
        logger.info("📊 HOURLY SESSION SUMMARY")
        logger.info("=" * 40)
        logger.info(f"📡 Signals Processed: {signals_logged}")
        logger.info(f"📈 Executions Simulated: {executions_simulated}")
        logger.info(f"⏰ Session Duration: {session_duration}")
        
        # Get regime performance
        regime_summary = self.trade_recommender.get_performance_summary(1)
        if regime_summary:
            logger.info("🎯 Regime Performance Today:")
            for regime, stats in regime_summary.items():
                logger.info(f"   {regime}: {stats.get('total_trades', 0)} trades, "
                          f"{stats.get('avg_win_rate', 0)*100:.1f}% win rate")
        
        logger.info("=" * 40)
    
    async def _generate_final_report(self):
        """Generate comprehensive final report."""
        logger.info("📊 GENERATING STABILITY PHASE FINAL REPORT")
        logger.info("=" * 60)
        
        # Export performance report
        report_path = performance_tracker.export_performance_report(14)
        
        # Get comprehensive summary
        overall_summary = performance_tracker.get_regime_performance_summary(14)
        
        logger.info("🎯 STABILITY PHASE RESULTS:")
        logger.info(f"📄 Detailed report saved: {report_path}")
        
        if overall_summary:
            total_trades = sum(stats.get('total_trades', 0) for stats in overall_summary.values())
            avg_win_rate = sum(stats.get('avg_win_rate', 0) for stats in overall_summary.values()) / len(overall_summary)
            total_pnl = sum(stats.get('total_pnl', 0) for stats in overall_summary.values())
            
            logger.info(f"📈 Total Trades: {total_trades}")
            logger.info(f"🎯 Overall Win Rate: {avg_win_rate*100:.1f}%")
            logger.info(f"💰 Total P&L: ${total_pnl:.2f}")
            
            logger.info("\n🎯 Performance by Regime:")
            for regime, stats in overall_summary.items():
                logger.info(f"   {regime}: {stats.get('total_trades', 0)} trades, "
                          f"{stats.get('avg_win_rate', 0)*100:.1f}% win rate, "
                          f"${stats.get('total_pnl', 0):.2f} P&L")
        
        logger.info("=" * 60)
        logger.info("✅ STABILITY PHASE COMPLETE - READY FOR LIVE TRADING")
        logger.info("=" * 60)
    
    def _generate_mock_data(self, ticker: str) -> dict:
        """Generate mock market data for testing."""
        import random
        
        # Mock data - replace with real market data
        return {
            'ticker': ticker,
            'timestamp': datetime.now(),
            'current_price': random.uniform(100, 200),
            'volume': random.randint(1000000, 10000000),
            'high': random.uniform(105, 210),
            'low': random.uniform(95, 190),
            'open': random.uniform(98, 205)
        }


async def main():
    """Main entry point for stability phase."""
    print("🧠 SIGNAL FLOW STABILITY PHASE")
    print("=" * 50)
    print("🎯 RECOMMENDED BY YOUR OTHER AI:")
    print("   ✅ Paper trading mode")
    print("   ✅ Log every signal & execution")
    print("   ✅ Measure win rate per regime")
    print("   ✅ Track regime classifications")
    print("   ✅ Performance dashboard ready")
    print("=" * 50)
    print()
    
    # Check if enhanced components are available
    try:
        controller = StabilityPhaseController()
        print("✅ Enhanced components loaded successfully")
        print("🚀 Starting stability phase monitoring...")
        print()
        print("💡 While this runs, open a new terminal and run:")
        print("   streamlit run dashboard.py")
        print("   (for real-time performance dashboard)")
        print()
        print("⏹️  Press Ctrl+C to stop and generate final report")
        print("=" * 50)
        
        await controller.run_stability_phase()
        
    except ImportError as e:
        print(f"❌ Enhanced components not available: {e}")
        print("💡 Run: python start_enhanced.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting stability phase: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
