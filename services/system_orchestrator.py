"""
System Orchestrator - Main controller for the enhanced trading system.
Coordinates all components: LLM routing, time windows, automation, and trading logic.
"""
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json
from loguru import logger

from .config import Config
from .automated_trading_manager import AutomatedTradingManager, AutomationMode, SafetyLimits
from .llm_router import LLMRouter, TaskType
from .trading_window_config import TradingWindowManager, TradingWindow, StrategyType
from .indicators import TechnicalIndicators
from .market_regime_detector import MarketRegimeDetector


class SystemMode(Enum):
    """Overall system operation modes."""
    DEVELOPMENT = "development"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    ANALYSIS_ONLY = "analysis_only"


@dataclass
class SystemConfiguration:
    """Complete system configuration."""
    mode: SystemMode
    automation_mode: AutomationMode
    enable_pre_market: bool = True
    enable_post_market: bool = True
    enable_ai_explanations: bool = True
    max_daily_trades: int = 25
    max_daily_loss_pct: float = 0.02
    min_confidence_threshold: float = 0.7
    notification_webhooks: List[str] = None
    
    def __post_init__(self):
        if self.notification_webhooks is None:
            self.notification_webhooks = []


class TradingSystemOrchestrator:
    """
    Main orchestrator for the enhanced trading system.
    
    This class coordinates all system components and provides a unified interface
    for starting, stopping, and monitoring the trading system.
    """
    
    def __init__(self, config: Config, system_config: SystemConfiguration):
        """Initialize the trading system orchestrator."""
        self.config = config
        self.system_config = system_config
        
        # Core components
        self.automated_manager = AutomatedTradingManager(config)
        self.llm_router = LLMRouter(config)
        self.window_manager = TradingWindowManager()
        self.regime_detector = MarketRegimeDetector(config)
        self.indicators = TechnicalIndicators(config, self.regime_detector)
        
        # System state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        
        # Performance tracking
        self.session_stats = {
            'trades_executed': 0,
            'signals_generated': 0,
            'ai_explanations_generated': 0,
            'regime_changes': 0,
            'window_changes': 0
        }
        
        # External integrations
        self.data_providers = {}
        self.notification_handlers = []
        
        # Configure automation manager
        self._configure_automation_manager()
        
        logger.info(f"Trading System Orchestrator initialized in {system_config.mode.value} mode")
    
    def _configure_automation_manager(self):
        """Configure the automation manager with system settings."""
        # Set safety limits
        safety_limits = SafetyLimits(
            max_daily_trades=self.system_config.max_daily_trades,
            max_daily_loss_pct=self.system_config.max_daily_loss_pct,
            min_account_balance=10000  # TODO: Get from config
        )
        
        self.automated_manager.configure_automation(
            self.system_config.automation_mode,
            safety_limits
        )
        
        # Register callbacks
        self.automated_manager.register_callbacks(
            trade_execution=self._execute_trade,
            data_fetch=self._fetch_market_data,
            notification=self._send_notification
        )
    
    async def start_system(self) -> bool:
        """Start the complete trading system."""
        try:
            logger.info("🚀 Starting Enhanced Trading System...")
            
            # Perform system checks
            if not await self._perform_system_checks():
                logger.error("System checks failed")
                return False
            
            # Start automated trading manager
            if not self.automated_manager.start_system():
                logger.error("Failed to start automated trading manager")
                return False
            
            # Initialize components
            await self._initialize_components()
            
            # Start monitoring loops
            self._start_monitoring_loops()
            
            self.is_running = True
            self.start_time = datetime.now()
            self.last_heartbeat = datetime.now()
            
            # Send startup notification
            await self._send_notification(
                "🚀 Trading System Started",
                f"Enhanced trading system started in {self.system_config.mode.value} mode",
                "success"
            )
            
            # Generate startup summary
            startup_summary = await self._generate_startup_summary()
            logger.info(f"📊 Startup Summary: {startup_summary}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            return False
    
    async def stop_system(self, emergency: bool = False) -> bool:
        """Stop the trading system gracefully."""
        try:
            logger.info("🛑 Stopping Enhanced Trading System...")
            
            # Stop automated trading manager
            self.automated_manager.stop_system(emergency)
            
            # Generate session report
            session_report = await self._generate_session_report()
            
            # Send shutdown notification
            await self._send_notification(
                "🛑 Trading System Stopped",
                f"System stopped. Session report: {session_report}",
                "info"
            )
            
            self.is_running = False
            
            logger.info("✅ Trading System stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")
            return False
    
    async def _perform_system_checks(self) -> bool:
        """Perform comprehensive system checks before startup."""
        logger.info("Performing system checks...")
        
        checks = {
            'llm_connectivity': await self._check_llm_connectivity(),
            'market_data_access': await self._check_market_data_access(),
            'configuration_valid': self._check_configuration(),
            'dependencies_available': self._check_dependencies()
        }
        
        all_passed = all(checks.values())
        
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {check_name}: {status}")
        
        return all_passed
    
    async def _check_llm_connectivity(self) -> bool:
        """Check LLM API connectivity."""
        try:
            test_result = self.llm_router.route_task(
                TaskType.LIGHTWEIGHT_TASKS,
                "Test connectivity",
                {}
            )
            return 'error' not in test_result['response'].lower()
        except Exception as e:
            logger.error(f"LLM connectivity check failed: {e}")
            return False
    
    async def _check_market_data_access(self) -> bool:
        """Check market data access."""
        try:
            # TODO: Implement actual market data check
            return True
        except Exception as e:
            logger.error(f"Market data check failed: {e}")
            return False
    
    def _check_configuration(self) -> bool:
        """Check system configuration validity."""
        try:
            required_env_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
            
            for var in required_env_vars:
                if not self.config.get(var):
                    logger.error(f"Missing required environment variable: {var}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Configuration check failed: {e}")
            return False
    
    def _check_dependencies(self) -> bool:
        """Check that all required dependencies are available."""
        try:
            import openai
            import anthropic
            import pandas_ta
            import numpy
            import pandas
            return True
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            return False
    
    async def _initialize_components(self):
        """Initialize all system components."""
        logger.info("Initializing system components...")
        
        # Initialize regime detector
        # TODO: Load historical data for regime detection
        
        # Initialize window manager with current time
        current_window = self.window_manager.get_current_window()
        logger.info(f"Current trading window: {current_window.value}")
        
        # Initialize performance tracking
        self.session_stats = {
            'trades_executed': 0,
            'signals_generated': 0,
            'ai_explanations_generated': 0,
            'regime_changes': 0,
            'window_changes': 0
        }
    
    def _start_monitoring_loops(self):
        """Start background monitoring loops."""
        # Start heartbeat loop
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        # Start window change monitoring
        threading.Thread(target=self._window_change_monitor, daemon=True).start()
        
        # Start performance monitoring
        threading.Thread(target=self._performance_monitor, daemon=True).start()
    
    def _heartbeat_loop(self):
        """Heartbeat loop to monitor system health."""
        while self.is_running:
            try:
                self.last_heartbeat = datetime.now()
                
                # Check system health
                health_status = self._check_system_health()
                
                if not health_status['healthy']:
                    logger.warning(f"System health issue: {health_status['issues']}")
                
                # Sleep for heartbeat interval
                threading.Event().wait(30)  # 30 second heartbeat
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                threading.Event().wait(60)  # Longer sleep on error
    
    def _window_change_monitor(self):
        """Monitor trading window changes."""
        current_window = self.window_manager.get_current_window()
        
        while self.is_running:
            try:
                new_window = self.window_manager.get_current_window()
                
                if new_window != current_window:
                    self._handle_window_change(current_window, new_window)
                    current_window = new_window
                    self.session_stats['window_changes'] += 1
                
                # Check every minute
                threading.Event().wait(60)
                
            except Exception as e:
                logger.error(f"Error in window change monitor: {e}")
                threading.Event().wait(60)
    
    def _performance_monitor(self):
        """Monitor system performance metrics."""
        while self.is_running:
            try:
                # Collect performance metrics
                metrics = self._collect_performance_metrics()
                
                # Log metrics periodically
                logger.info(f"📊 Performance Metrics: {metrics}")
                
                # Check for performance issues
                if metrics.get('memory_usage', 0) > 80:
                    logger.warning("High memory usage detected")
                
                # Sleep for monitoring interval
                threading.Event().wait(300)  # 5 minute intervals
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
                threading.Event().wait(300)
    
    def _handle_window_change(self, old_window: TradingWindow, new_window: TradingWindow):
        """Handle trading window changes."""
        logger.info(f"🔄 Trading window changed: {old_window.value} → {new_window.value}")
        
        # Get new window configuration
        new_config = self.window_manager.get_window_config(new_window)
        
        if new_config:
            logger.info(f"New window config: Risk={new_config.risk_level}, "
                       f"Strategies={[s.value for s in new_config.allowed_strategies]}")
        
        # Notify automated trading manager of window change
        # TODO: Implement window change notification
        
        # Send notification
        asyncio.create_task(self._send_notification(
            "🔄 Trading Window Changed",
            f"Changed to {new_window.value}",
            "info"
        ))
    
    async def _fetch_market_data(self) -> Dict[str, Any]:
        """Fetch current market data for the automated trading manager."""
        try:
            # TODO: Implement actual market data fetching
            # This is a placeholder that would connect to your data provider
            
            current_time = datetime.now()
            
            return {
                'timestamp': current_time,
                'market_status': 'open',  # or 'closed', 'pre_market', 'post_market'
                'current_window': self.window_manager.get_current_window().value,
                'market_regime': self.regime_detector.current_regime.regime.value if self.regime_detector.current_regime else 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return {}
    
    async def _execute_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trade through the orchestrator."""
        try:
            logger.info(f"📈 Executing trade: {signal}")
            
            # Generate AI explanation for the trade
            if self.system_config.enable_ai_explanations:
                explanation = await self._generate_trade_explanation(signal)
                signal['ai_explanation'] = explanation
                self.session_stats['ai_explanations_generated'] += 1
            
            # TODO: Implement actual trade execution
            # This would connect to your broker API
            
            result = {
                'success': True,
                'trade_id': f"trade_{datetime.now().timestamp()}",
                'executed_at': datetime.now(),
                'signal': signal
            }
            
            self.session_stats['trades_executed'] += 1
            
            # Send trade notification
            await self._send_notification(
                "📈 Trade Executed",
                f"Executed {signal.get('action', 'unknown')} for {signal.get('symbol', 'unknown')}",
                "info"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_trade_explanation(self, signal: Dict[str, Any]) -> str:
        """Generate AI explanation for a trade using LLM router."""
        try:
            context = {
                'signal': signal,
                'current_window': self.window_manager.get_current_window().value,
                'market_regime': self.regime_detector.current_regime.regime.value if self.regime_detector.current_regime else 'unknown',
                'timestamp': datetime.now()
            }
            
            prompt = f"""
            Explain this automated trade decision:
            
            Symbol: {signal.get('symbol', 'Unknown')}
            Action: {signal.get('action', 'Unknown')}
            Confidence: {signal.get('confidence', 0):.2f}
            Strategy: {signal.get('strategy', 'Unknown')}
            Trading Window: {context['current_window']}
            Market Regime: {context['market_regime']}
            
            Reasoning: {signal.get('reasoning', 'No reasoning provided')}
            
            Provide a clear, concise explanation of:
            1. Why this trade was automatically triggered
            2. The key factors that led to this decision
            3. The expected outcome and risk profile
            4. How the current market conditions support this trade
            """
            
            result = self.llm_router.route_task(
                TaskType.TRADE_EXPLANATION,
                prompt,
                context
            )
            
            return result['response']
            
        except Exception as e:
            logger.error(f"Error generating trade explanation: {e}")
            return f"Error generating explanation: {str(e)}"
    
    async def _send_notification(self, title: str, message: str, priority: str = "info"):
        """Send notification through configured channels."""
        try:
            notification = {
                'title': title,
                'message': message,
                'priority': priority,
                'timestamp': datetime.now(),
                'system': 'Enhanced Trading System'
            }
            
            # Log notification
            logger.info(f"📢 {title}: {message}")
            
            # Send to registered handlers
            for handler in self.notification_handlers:
                try:
                    await handler(notification)
                except Exception as e:
                    logger.error(f"Error in notification handler: {e}")
            
            # TODO: Implement webhook notifications
            # for webhook_url in self.system_config.notification_webhooks:
            #     await self._send_webhook_notification(webhook_url, notification)
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        try:
            issues = []
            
            # Check if automated manager is running
            if not self.automated_manager.state.value == 'running':
                issues.append("Automated trading manager not running")
            
            # Check heartbeat age
            if self.last_heartbeat:
                heartbeat_age = datetime.now() - self.last_heartbeat
                if heartbeat_age > timedelta(minutes=2):
                    issues.append(f"Heartbeat stale: {heartbeat_age}")
            
            # Check for recent errors
            # TODO: Implement error tracking
            
            return {
                'healthy': len(issues) == 0,
                'issues': issues,
                'last_check': datetime.now()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'issues': [f"Health check error: {str(e)}"],
                'last_check': datetime.now()
            }
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics."""
        try:
            import psutil
            
            return {
                'uptime_minutes': (datetime.now() - self.start_time).total_seconds() / 60 if self.start_time else 0,
                'memory_usage': psutil.virtual_memory().percent,
                'cpu_usage': psutil.cpu_percent(),
                'trades_per_hour': self.session_stats['trades_executed'] / max(1, (datetime.now() - self.start_time).total_seconds() / 3600) if self.start_time else 0,
                'session_stats': self.session_stats.copy()
            }
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
            return {'error': str(e)}
    
    async def _generate_startup_summary(self) -> str:
        """Generate startup summary using LLM."""
        try:
            system_status = self.get_system_status()
            
            prompt = f"""
            Generate a startup summary for the enhanced trading system:
            
            System Configuration:
            - Mode: {self.system_config.mode.value}
            - Automation: {self.system_config.automation_mode.value}
            - Pre/Post Market: {self.system_config.enable_pre_market}/{self.system_config.enable_post_market}
            - Max Daily Trades: {self.system_config.max_daily_trades}
            - AI Explanations: {self.system_config.enable_ai_explanations}
            
            Current Status: {json.dumps(system_status, default=str, indent=2)}
            
            Provide a concise startup summary highlighting:
            1. System readiness and configuration
            2. Current market window and opportunities
            3. Key safety measures in place
            4. What to expect during this session
            """
            
            result = self.llm_router.route_task(
                TaskType.DAILY_SUMMARY,
                prompt,
                system_status
            )
            
            return result['response']
            
        except Exception as e:
            logger.error(f"Error generating startup summary: {e}")
            return f"Startup summary generation failed: {str(e)}"
    
    async def _generate_session_report(self) -> str:
        """Generate end-of-session report using LLM."""
        try:
            session_duration = datetime.now() - self.start_time if self.start_time else timedelta(0)
            
            prompt = f"""
            Generate an end-of-session report for the trading system:
            
            Session Duration: {session_duration}
            Session Statistics: {json.dumps(self.session_stats, indent=2)}
            Automated Manager Stats: {json.dumps(self.automated_manager.get_system_status(), default=str, indent=2)}
            
            Provide a comprehensive session report including:
            1. Performance summary and key metrics
            2. Notable events and decisions made
            3. System reliability and uptime
            4. Recommendations for next session
            """
            
            result = self.llm_router.route_task(
                TaskType.DAILY_SUMMARY,
                prompt,
                self.session_stats
            )
            
            return result['response']
            
        except Exception as e:
            logger.error(f"Error generating session report: {e}")
            return f"Session report generation failed: {str(e)}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'orchestrator': {
                'running': self.is_running,
                'start_time': self.start_time,
                'uptime': datetime.now() - self.start_time if self.start_time else None,
                'mode': self.system_config.mode.value,
                'automation_mode': self.system_config.automation_mode.value
            },
            'automated_manager': self.automated_manager.get_system_status(),
            'trading_window': {
                'current': self.window_manager.get_current_window().value,
                'next_change': self.window_manager.get_next_window_change()
            },
            'session_stats': self.session_stats.copy(),
            'health': self._check_system_health()
        }
    
    def register_notification_handler(self, handler: Callable):
        """Register a notification handler."""
        self.notification_handlers.append(handler)
        logger.info("Notification handler registered")
    
    def register_data_provider(self, name: str, provider: Callable):
        """Register a market data provider."""
        self.data_providers[name] = provider
        logger.info(f"Data provider '{name}' registered")


# Convenience function to create and start the system
async def create_and_start_trading_system(
    config: Config,
    mode: SystemMode = SystemMode.PAPER_TRADING,
    automation_mode: AutomationMode = AutomationMode.SUPERVISED
) -> TradingSystemOrchestrator:
    """Create and start the trading system with specified configuration."""
    
    system_config = SystemConfiguration(
        mode=mode,
        automation_mode=automation_mode,
        enable_ai_explanations=True,
        max_daily_trades=25
    )
    
    orchestrator = TradingSystemOrchestrator(config, system_config)
    
    success = await orchestrator.start_system()
    if not success:
        raise RuntimeError("Failed to start trading system")
    
    return orchestrator
