"""
Signal Flow AI Trading Assistant
Main entry point and orchestrator for the trading system.
Enhanced with comprehensive AI learning capabilities.
"""
import asyncio
import schedule
import time
from datetime import datetime
from loguru import logger

from services.config import Config
from utils.logger_setup import setup_logger
from services.learning_manager import LearningManager


class SignalFlowOrchestrator:
    """Main orchestrator for the Signal Flow trading system."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        setup_logger()
        self.config = Config()
        self.is_running = False
        
        # Initialize AI learning system
        self.learning_manager = LearningManager()
        
        # Validate configuration
        if not self.config.validate_required_keys():
            raise ValueError("Missing required configuration. Check your .env file.")
            
        logger.info("Signal Flow Trading Assistant with AI Learning initialized")
    
    async def run_market_scan(self):
        """Run the market scanning process with AI learning integration."""
        try:
            # Skip trading hours check for full automation mode
            # if not self.config.is_trading_hours():
            #     logger.info("Outside trading hours, skipping market scan")
            #     return
                
            logger.info("Starting AI-enhanced market scan (24/7 automation mode)...")
            
            # Import agents here to avoid circular imports
            from agents.market_watcher_agent import MarketWatcherAgent
            from agents.sentiment_agent import SentimentAgent
            from agents.trade_recommender_agent import TradeRecommenderAgent
            from agents.reasoning_agent import ReasoningAgent
            from services.alpaca_trading import AlpacaTradingService
            from services.interactive_trading import InteractiveTradingService
            from services.telegram_bot import TelegramNotifier
            from services.production_telegram import production_telegram  # NEW: Production integration
            
            # Initialize services (Telegram only)
            market_watcher = MarketWatcherAgent()
            sentiment_agent = SentimentAgent()
            trade_recommender = TradeRecommenderAgent()
            reasoning_agent = ReasoningAgent()
            telegram_notifier = TelegramNotifier()
            alpaca_trading = AlpacaTradingService()
            interactive_trading = InteractiveTradingService()
            
            # Run the trading pipeline
            setups = await market_watcher.scan_for_setups()
            
            for setup in setups:
                # Analyze sentiment
                sentiment = await sentiment_agent.analyze_ticker(setup['ticker'])
                
                # Get trade recommendation
                recommendation = await trade_recommender.evaluate_setup(setup, sentiment)
                
                if recommendation and recommendation['confidence'] >= self.config.MIN_CONFIDENCE_SCORE:
                    # Generate explanation
                    explanation = await reasoning_agent.explain_trade(recommendation, setup, sentiment)
                    
                    # Check trading mode
                    if self.config.AUTO_TRADING_ENABLED:
                        # Automatic trading - execute immediately
                        logger.info(f"Auto-trading enabled: executing buy order for {setup['ticker']}")
                        order_result = await alpaca_trading.place_buy_order(recommendation)
                        
                        if order_result:
                            # Send notification about executed trade
                            await telegram_notifier.send_simple_message(
                                f"🤖 AUTO-TRADE EXECUTED\n"
                                f"📊 {setup['ticker']}: {order_result['shares']} shares\n"
                                f"💰 Entry: ${recommendation['entry']}\n"
                                f"🎯 Target: ${recommendation['take_profit']}\n"
                                f"🛑 Stop: ${recommendation['stop_loss']}\n"
                                f"⭐ Confidence: {recommendation['confidence']}/10"
                            )
                            
                            # Send Telegram notification too
                            await telegram_notifier.send_execution_update(
                                setup['ticker'], 
                                'BUY', 
                                'success',
                                {
                                    'shares': order_result['shares'],
                                    'price': recommendation['entry'],
                                    'order_id': order_result.get('order_id', 'N/A')
                                }
                            )
                            
                            # Add to execution monitor
                            from agents.execution_monitor_agent import ExecutionMonitorAgent
                            monitor = ExecutionMonitorAgent()
                            await monitor.add_trade({
                                'ticker': setup['ticker'],
                                'entry_price': recommendation['entry'],
                                'stop_loss': recommendation['stop_loss'],
                                'take_profit': recommendation['take_profit'],
                                'shares': order_result['shares'],
                                'order_id': order_result['order_id']
                            })
                            
                            logger.info(f"Auto-trade executed and monitored for {setup['ticker']}")
                        else:
                            await telegram_notifier.send_simple_message(f"❌ Auto-trade failed for {setup['ticker']}")
                    
                    elif self.config.INTERACTIVE_TRADING_ENABLED:
                        # Interactive trading - request confirmation
                        logger.info(f"Interactive trading: requesting confirmation for {setup['ticker']}")
                        confirmed = await interactive_trading.request_buy_confirmation(recommendation, explanation)
                        
                        if confirmed:
                            logger.info(f"Trade confirmed and executed for {setup['ticker']}")
                        else:
                            logger.info(f"Trade declined for {setup['ticker']}")
                    
                    else:
                        # PRODUCTION: Send interactive Telegram signal with real execution buttons
                        logger.info(f"Sending interactive trading signal for {setup['ticker']}")
                        
                        # Send production Telegram signal with executable buttons
                        await production_telegram.send_trading_signal(recommendation, explanation)
                        
                        # Also send backup SMS notification
                        await telegram_notifier.send_trade_alert(recommendation, explanation)
                        
                        logger.info(f"Production interactive signal sent for {setup['ticker']}")
                
        except Exception as e:
            logger.error(f"Error in market scan: {e}")
    
    async def run_morning_screener(self):
        """Run the morning stock screener."""
        try:
            logger.info("Running morning stock screener...")
            
            from services.dynamic_screener import DynamicScreener
            
            screener = DynamicScreener()
            await screener.update_watchlist()
            
            logger.info("Morning screener completed")
            
        except Exception as e:
            logger.error(f"Error in morning screener: {e}")
    
    async def run_daily_summary(self):
        """Generate and send daily trading summary."""
        try:
            logger.info("Generating daily summary...")
            
            from agents.summary_agent import SummaryAgent
            from services.telegram_trading import telegram_trading
            
            summary_agent = SummaryAgent()
            
            summary = await summary_agent.generate_daily_summary()
            await telegram_trading.send_daily_summary(summary)
            
            logger.info("Daily summary sent")
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
    
    def schedule_tasks(self):
        """Schedule trading and learning tasks."""
        # Schedule market scans every minute for full automation
        schedule.every(1).minutes.do(self._schedule_market_scan)
        
        # Schedule learning tasks  
        schedule.every(30).minutes.do(self._schedule_learning)
        schedule.every(2).hours.do(self._schedule_validation)
        
        # Schedule summary generation  
        schedule.every().day.at("16:00").do(self._schedule_daily_summary)
        
        logger.info("Trading and AI learning tasks scheduled (full automation mode)")
    
    def _schedule_market_scan(self):
        """Schedule market scan as async task."""
        asyncio.create_task(self.run_market_scan())
    
    def _schedule_learning(self):
        """Schedule learning as async task."""
        asyncio.create_task(self.learning_manager.run_comprehensive_learning())
    
    def _schedule_validation(self):
        """Schedule validation as async task."""
        asyncio.create_task(self.learning_manager.run_strategy_validation())
    
    def _schedule_daily_summary(self):
        """Schedule daily summary as async task."""
        asyncio.create_task(self.generate_daily_summary())
    
    async def run_learning_cycle(self):
        """Run AI learning cycle."""
        try:
            logger.info("Starting AI learning cycle...")
            results = await self.learning_manager.run_comprehensive_learning()
            
            # Generate insights
            insights = await self.learning_manager.generate_daily_insights()
            
            # Send learning summary via Telegram
            from services.telegram_trading import telegram_trading
            
            learning_summary = self._format_learning_summary(results, insights)
            await telegram_trading.send_message(f"🧠 AI Learning Update:\n{learning_summary}")
            
            logger.info("AI learning cycle completed")
            
        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")
    
    async def run_strategy_validation(self):
        """Run strategy validation through backtesting."""
        try:
            logger.info("Starting strategy validation...")
            results = await self.learning_manager.run_strategy_validation()
            
            # Send validation summary
            from services.telegram_trading import telegram_trading
            
            validation_summary = self._format_validation_summary(results)
            await telegram_trading.send_message(f"📊 Strategy Validation:\n{validation_summary}")
            
            logger.info("Strategy validation completed")
            
        except Exception as e:
            logger.error(f"Error in strategy validation: {e}")
    
    def _format_learning_summary(self, results: dict, insights: dict) -> str:
        """Format learning results for Telegram notification."""
        summary = []
        
        # Learning metrics
        if results.get('learning_engine_results'):
            metrics = results['learning_engine_results']
            if hasattr(metrics, 'prediction_accuracy'):
                summary.append(f"📈 Prediction Accuracy: {metrics.prediction_accuracy*100:.1f}%")
                summary.append(f"🎯 Win Rate: {metrics.win_rate*100:.1f}%")
                summary.append(f"📊 Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        
        # Key insights
        key_insights = insights.get('key_insights', [])
        if key_insights:
            summary.append("\n💡 Key Insights:")
            for insight in key_insights[:2]:  # Top 2 insights
                summary.append(f"• {insight}")
        
        # Recommendations
        recommendations = insights.get('recommendations', [])
        if recommendations:
            summary.append("\n🔧 Recommendations:")
            for rec in recommendations[:2]:  # Top 2 recommendations
                summary.append(f"• {rec}")
        
        return "\n".join(summary) if summary else "Learning cycle completed - collecting more data"
    
    def _format_validation_summary(self, results: dict) -> str:
        """Format validation results for WhatsApp notification."""
        summary = []
        
        backtest_results = results.get('backtest_results', {})
        best_strategy = backtest_results.get('best_strategy')
        
        if best_strategy:
            summary.append(f"🏆 Best Strategy: {best_strategy}")
            
            rankings = backtest_results.get('strategy_rankings', [])
            if rankings:
                best = rankings[0]
                summary.append(f"📈 Return: {best['total_return']:.1f}%")
                summary.append(f"🎯 Win Rate: {best['win_rate']*100:.1f}%")
                summary.append(f"📉 Max Drawdown: {best['max_drawdown']*100:.1f}%")
        
        validation_insights = results.get('validation_insights', {})
        opportunities = validation_insights.get('optimization_opportunities', [])
        if opportunities:
            summary.append("\n🔧 Optimization:")
            for opp in opportunities[:2]:
                summary.append(f"• {opp}")
        
        return "\n".join(summary) if summary else "Strategy validation completed"
    
    async def start(self):
        """Start the trading system with AI learning."""
        logger.info("Starting Signal Flow Trading Assistant with AI Learning...")
        
        self.schedule_tasks()
        self.is_running = True
        
        # Send startup notification
        try:
            from services.telegram_trading import telegram_trading
            await telegram_trading.send_message(
                "🚀 *TRADING SYSTEM STARTING*\n\n"
                f"✅ System: Initializing\n"
                f"⏰ Time: {datetime.now().strftime('%H:%M:%S EST')}\n"
                f"📡 Mode: Paper Trading\n"
                f"🎯 Market Scanning: Starting\n"
                f"📊 Schedule: Every 1 minute\n\n"
                "Running initial market scan now..."
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")
        
        # Start continuous learning in background
        learning_task = asyncio.create_task(self.learning_manager.start_continuous_learning())
        
        # Run initial screener
        await self.run_morning_screener()
        
        # Run immediate market scan to test
        logger.info("Running immediate market scan for testing...")
        await self.run_market_scan()
        
        # Main event loop
        try:
            while self.is_running:
                schedule.run_pending()
                await asyncio.sleep(1)
        finally:
            # Cancel learning task
            learning_task.cancel()
            try:
                await learning_task
            except asyncio.CancelledError:
                pass
    
    def stop(self):
        """Stop the trading system."""
        logger.info("Stopping Signal Flow Trading Assistant...")
        self.is_running = False


async def main():
    """Main entry point."""
    orchestrator = SignalFlowOrchestrator()
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        orchestrator.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
