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
            # Skip if outside trading hours (market hours check can be enabled later)
            #     logger.info("Outside trading hours, skipping market scan")
            #     return
            
            logger.info("Starting AI-enhanced market scan (24/7 automation mode)...")
            
            # Import agents dynamically to avoid circular imports
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
            
            # Run the trading pipeline with Polygon.io enhancement
            setups = await market_watcher.scan_for_setups()
            
            # 🚀 NEW: Enhance with Polygon.io Trading Engines
            enhanced_setups = await self._enhance_with_polygon_engines(setups)
            
            for setup in enhanced_setups:
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
                        # PRODUCTION: Send enhanced interactive Telegram signal with Polygon.io data
                        logger.info(f"Sending enhanced trading signal for {setup.get('symbol', setup.get('ticker', 'Unknown'))}")
                        
                        # Create enhanced notification
                        enhanced_message = await self._create_enhanced_notification(
                            setup, recommendation, explanation, sentiment_analysis={'overall_sentiment': 'Neutral'}
                        )
                        
                        # Send enhanced production Telegram signal with proper method
                        await production_telegram.send_trading_signal(recommendation, explanation)
                        
                        # Also send the enhanced message via standard notifier
                        await telegram_notifier.send_message(enhanced_message)
                        
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
        
        # Schedule market open/close notifications (EST)
        schedule.every().monday.at("09:30").do(self._schedule_market_open_notification)
        schedule.every().tuesday.at("09:30").do(self._schedule_market_open_notification)
        schedule.every().wednesday.at("09:30").do(self._schedule_market_open_notification)
        schedule.every().thursday.at("09:30").do(self._schedule_market_open_notification)
        schedule.every().friday.at("09:30").do(self._schedule_market_open_notification)
        
        schedule.every().monday.at("16:00").do(self._schedule_market_close_notification)
        schedule.every().tuesday.at("16:00").do(self._schedule_market_close_notification)
        schedule.every().wednesday.at("16:00").do(self._schedule_market_close_notification)
        schedule.every().thursday.at("16:00").do(self._schedule_market_close_notification)
        schedule.every().friday.at("16:00").do(self._schedule_market_close_notification)
        
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
    
    def _schedule_market_open_notification(self):
        """Schedule market open notification as async task."""
        asyncio.create_task(self.send_market_open_notification())
    
    def _schedule_market_close_notification(self):
        """Schedule market close notification as async task."""
        asyncio.create_task(self.send_market_close_notification())
    
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
    
    async def send_market_open_notification(self):
        """Send market open notification"""
        try:
            from services.telegram_trading import telegram_trading
            await telegram_trading.send_message(
                "🔔 *MARKET OPEN*\n\n"
                f"📈 US Markets are now OPEN\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S EST')}\n"
                f"🤖 AI system is actively monitoring\n"
                f"🎯 Ready to execute trades"
            )
            logger.info("Market open notification sent")
        except Exception as e:
            logger.error(f"Failed to send market open notification: {e}")
    
    async def send_market_close_notification(self):
        """Send market close notification"""
        try:
            from services.telegram_trading import telegram_trading
            await telegram_trading.send_message(
                "🔔 *MARKET CLOSED*\n\n"
                f"📉 US Markets are now CLOSED\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S EST')}\n"
                f"📊 Processing end-of-day analysis\n"
                f"💤 System entering post-market mode"  
            )
            logger.info("Market close notification sent")
        except Exception as e:
            logger.error(f"Failed to send market close notification: {e}")
    
    # 🚀 NEW: Polygon.io Trading Engines Integration Methods
    
    async def _enhance_with_polygon_engines(self, base_setups):
        """
        Enhance trading signals using Polygon.io engines
        Returns enhanced setups with additional Polygon.io data
        """
        start_time = time.time()
        try:
            # Import Polygon.io services with error handling
            try:
                from services.anomaly_detection import AnomalyDetectionEngine as AnomalyDetector
                from services.websocket_engine import RealTimeWebSocketEngine as WebSocketEngine
                from services.short_squeeze_detector import ShortSqueezeDetector
                from services.sentiment_trading import SentimentTradingEngine
                from services.master_trading_coordinator import MasterTradingCoordinator
            except ImportError as import_error:
                logger.error(f"Failed to import Polygon.io services: {import_error}")
                logger.warning("Falling back to base setups without Polygon.io enhancement")
                return base_setups
            
            # Initialize engines
            anomaly_detector = AnomalyDetector()
            websocket_engine = WebSocketEngine()
            squeeze_detector = ShortSqueezeDetector()
            sentiment_engine = SentimentTradingEngine()
            master_coordinator = MasterTradingCoordinator()
            
            enhanced_setups = []
            
            # Early return if no base setups
            if not base_setups:
                logger.info("No base setups provided for Polygon.io enhancement")
                return []
            
            # Extract symbols from base setups (handle both 'ticker' and 'symbol' keys)
            symbols = []
            for setup in base_setups:
                if isinstance(setup, dict):
                    # Priority: symbol > ticker
                    if 'symbol' in setup:
                        symbols.append(setup['symbol'])
                    elif 'ticker' in setup:
                        symbols.append(setup['ticker'])
                elif hasattr(setup, 'symbol'):
                    symbols.append(setup.symbol)
                elif hasattr(setup, 'ticker'):
                    symbols.append(setup.ticker)
            
            # Remove duplicates and log
            symbols = list(set(symbols))
            logger.info(f"Extracted {len(symbols)} unique symbols for Polygon.io enhancement: {symbols[:5]}{'...' if len(symbols) > 5 else ''}")
            
            # Skip Polygon.io processing if no symbols found
            if not symbols:
                logger.warning("No symbols found in setups - skipping Polygon.io enhancement")
                return base_setups
            
            # Get enhanced signals from each Polygon.io engine (with rate limiting)
            polygon_enhancements = {}
            
            # 1. Anomaly Detection (only if we have symbols to analyze)
            if symbols:
                try:
                    polygon_enhancements['anomalies'] = await anomaly_detector.detect_anomalies(symbols)
                    logger.info(f"Detected {len(polygon_enhancements['anomalies'])} anomalies")
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Anomaly detection failed: {e}")
                    polygon_enhancements['anomalies'] = []
            
            # 2. Short Squeeze Detection
            try:
                polygon_enhancements['squeezes'] = await squeeze_detector.scan_for_squeezes()
                logger.info(f"Found {len(polygon_enhancements['squeezes'])} potential squeezes")
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.warning(f"Squeeze detection failed: {e}")
                polygon_enhancements['squeezes'] = []
            
            # 3. Sentiment Analysis Enhancement (only if we have symbols)
            if symbols:
                try:
                    polygon_enhancements['sentiment'] = await sentiment_engine.analyze_market_sentiment(symbols)
                    logger.info(f"Analyzed sentiment for {len(symbols)} symbols")
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Sentiment analysis failed: {e}")
                    polygon_enhancements['sentiment'] = []
            
            # 4. WebSocket Status (for real-time data quality)
            try:
                polygon_enhancements['websocket_status'] = await websocket_engine.get_connection_status()
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.warning(f"WebSocket status check failed: {e}")
                polygon_enhancements['websocket_status'] = {'connected': False, 'status': 'error'}
            
            # Process each setup with Polygon.io enhancements
            for setup in base_setups:
                enhanced_setup = setup.copy() if isinstance(setup, dict) else setup.__dict__.copy()
                # Get the symbol/ticker for matching (prioritize symbol, fallback to ticker)
                symbol = enhanced_setup.get('symbol') or enhanced_setup.get('ticker', '')
                
                # Add Polygon.io anomaly data
                anomaly_data = [a for a in polygon_enhancements.get('anomalies', []) if a.get('symbol') == symbol]
                if anomaly_data:
                    enhanced_setup['polygon_anomalies'] = anomaly_data[0]
                    enhanced_setup['anomaly_score'] = anomaly_data[0].get('anomaly_score', 0)
                
                # Add sentiment data
                sentiment_data = [s for s in polygon_enhancements.get('sentiment', []) if s.get('symbol') == symbol]
                if sentiment_data:
                    enhanced_setup['polygon_sentiment'] = sentiment_data[0]
                    enhanced_setup['sentiment_score'] = sentiment_data[0].get('sentiment_score', 0)
                
                # Add squeeze data
                squeeze_data = [sq for sq in polygon_enhancements.get('squeezes', []) if sq.get('symbol') == symbol]
                if squeeze_data:
                    enhanced_setup['polygon_squeeze'] = squeeze_data[0]
                    enhanced_setup['squeeze_probability'] = squeeze_data[0].get('squeeze_probability', 0)
                
                # Add WebSocket status for data freshness
                enhanced_setup['data_freshness'] = polygon_enhancements['websocket_status']
                
                enhanced_setups.append(enhanced_setup)
            
            # Master Coordinator Processing (with error handling)
            try:
                unified_signals = await master_coordinator.process_all_signals(
                    base_setups, enhanced_setups
                )
                logger.info(f"Master coordinator processed {len(enhanced_setups)} enhanced setups")
            except Exception as e:
                logger.warning(f"Master coordinator processing failed: {e}")
                unified_signals = enhanced_setups  # Use enhanced setups as fallback
            
            logger.info(f"Enhanced {len(enhanced_setups)} setups with Polygon.io data")
            
            # Log performance metrics
            enhancement_time = time.time() - start_time
            logger.info(f"Polygon.io enhancement completed in {enhancement_time:.2f}s")
            
            return unified_signals if unified_signals else enhanced_setups
            
        except Exception as e:
            enhancement_time = time.time() - start_time
            logger.error(f"Error in Polygon.io signal enhancement after {enhancement_time:.2f}s: {e}")
            return base_setups  # Return original setups if enhancement fails
    
    async def _create_enhanced_notification(self, setup, recommendations, reasoning, sentiment_analysis):
        """
        Create enhanced notification message with Polygon.io data
        """
        try:
            # Get symbol/ticker (prioritize symbol, fallback to ticker)
            symbol = setup.get('symbol') or setup.get('ticker', 'Unknown')
            
            # Base message
            message = (
                f"🎯 Enhanced Trading Signal Generated\n\n"
                f"📊 Symbol: {symbol}\n"
                f"📈 Setup Type: {setup.get('setup_type', 'Market Analysis')}\n"
                f"🔍 Signal: {recommendations.get('action', 'Hold')}\n"
                f"💰 Entry: ${recommendations.get('entry', 'N/A')}\n"
                f"🎯 Target: ${recommendations.get('target', 'N/A')}\n"
                f"🛡️ Stop Loss: ${recommendations.get('stop_loss', 'N/A')}\n"
                f"📝 Confidence: {recommendations.get('confidence', 0):.1%}\n\n"
            )
            
            # Add Polygon.io enhancements
            polygon_data = []
            
            # Anomaly data
            if setup.get('polygon_anomalies'):
                anomaly_score = setup.get('anomaly_score', 0)
                polygon_data.append(f"🔥 Anomaly Score: {anomaly_score:.2f}")
            
            # Sentiment data
            if setup.get('polygon_sentiment'):
                sentiment_score = setup.get('sentiment_score', 0)
                polygon_data.append(f"📰 Sentiment Score: {sentiment_score:.2f}")
            
            # Squeeze data
            if setup.get('polygon_squeeze'):
                squeeze_prob = setup.get('squeeze_probability', 0)
                polygon_data.append(f"🚀 Squeeze Probability: {squeeze_prob:.1%}")
            
            # Data freshness
            if setup.get('data_freshness', {}).get('connected'):
                polygon_data.append("✅ Real-time data active")
            else:
                polygon_data.append("⚠️ Using delayed data")
            
            if polygon_data:
                message += "🔬 Polygon.io Enhancements:\n" + "\n".join(polygon_data) + "\n\n"
            
            # Add reasoning and sentiment
            message += (
                f"🧠 AI Reasoning:\n{reasoning}\n\n"
                f"📊 Market Sentiment: {sentiment_analysis.get('overall_sentiment', 'Neutral')}\n"
                f"⏰ Generated: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating enhanced notification: {e}")
            # Fallback to basic notification with proper symbol handling
            symbol = setup.get('symbol') or setup.get('ticker', 'Unknown')
            return (
                f"🎯 Trading Signal: {symbol}\n"
                f"Action: {recommendations.get('action', 'Hold')}\n"
                f"Entry: ${recommendations.get('entry', 'N/A')}"
            )

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
