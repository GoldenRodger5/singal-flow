"""
Automated Trading System Manager.
Handles continuous operation, safety monitoring, and autonomous decision making.
"""
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from loguru import logger
import json
import os

from .trading_window_config import TradingWindowManager, TradingWindow, StrategyType
from .llm_router import LLMRouter, TaskType
from .config import Config


class SystemState(Enum):
    """System operational states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class AutomationMode(Enum):
    """Automation operation modes."""
    FULLY_AUTOMATED = "fully_automated"    # System runs 24/7
    MARKET_HOURS_ONLY = "market_hours_only"  # Only during market hours
    SUPERVISED = "supervised"               # Human approval required
    PAPER_TRADING = "paper_trading"         # Simulated trades only
    ANALYSIS_ONLY = "analysis_only"         # No trading, analysis only


@dataclass
class SafetyLimits:
    """Safety limits for automated trading."""
    max_daily_trades: int = 25
    max_daily_loss_pct: float = 0.02  # 2%
    max_position_size_pct: float = 0.10  # 10% of account
    max_correlation_exposure: float = 0.30  # 30% in correlated positions
    min_account_balance: float = 10000  # Minimum account balance
    max_consecutive_losses: int = 5
    circuit_breaker_loss_pct: float = 0.05  # 5% daily loss triggers stop
    connectivity_timeout_seconds: int = 30


@dataclass
class OperationalStats:
    """Operational statistics tracking."""
    system_start_time: datetime = field(default_factory=datetime.now)
    trades_today: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    last_trade_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    errors_today: List[str] = field(default_factory=list)
    uptime_percentage: float = 100.0


class AutomatedTradingManager:
    """
    Manages fully automated trading system with safety monitoring.
    Handles continuous operation, decision making, and risk management.
    """
    
    def __init__(self, config: Config):
        """Initialize automated trading manager."""
        self.config = config
        self.state = SystemState.STOPPED
        self.automation_mode = AutomationMode.PAPER_TRADING  # Safe default
        
        # Core components
        self.window_manager = TradingWindowManager()
        self.llm_router = LLMRouter(config)
        
        # Safety and monitoring
        self.safety_limits = SafetyLimits()
        self.stats = OperationalStats()
        
        # Control flags
        self.should_stop = threading.Event()
        self.is_paused = threading.Event()
        self.emergency_stop_triggered = threading.Event()
        
        # Main loop thread
        self.main_thread: Optional[threading.Thread] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Callbacks for external integration
        self.trade_execution_callback: Optional[Callable] = None
        self.data_fetch_callback: Optional[Callable] = None
        self.notification_callback: Optional[Callable] = None
        
        # Performance tracking
        self.performance_log = []
        self.decision_log = []
        
        logger.info("Automated Trading Manager initialized")
    
    def configure_automation(self, mode: AutomationMode, safety_limits: Optional[SafetyLimits] = None):
        """Configure automation mode and safety limits."""
        self.automation_mode = mode
        if safety_limits:
            self.safety_limits = safety_limits
        
        logger.info(f"Automation configured: mode={mode.value}")
    
    def register_callbacks(self, 
                          trade_execution: Optional[Callable] = None,
                          data_fetch: Optional[Callable] = None,
                          notification: Optional[Callable] = None):
        """Register callback functions for external integration."""
        if trade_execution:
            self.trade_execution_callback = trade_execution
        if data_fetch:
            self.data_fetch_callback = data_fetch
        if notification:
            self.notification_callback = notification
        
        logger.info("Callbacks registered for external integration")
    
    def start_system(self) -> bool:
        """Start the automated trading system."""
        try:
            if self.state != SystemState.STOPPED:
                logger.warning(f"Cannot start system in state: {self.state.value}")
                return False
            
            self.state = SystemState.STARTING
            self._reset_daily_stats()
            
            # Perform system health checks
            if not self._perform_startup_checks():
                self.state = SystemState.ERROR
                return False
            
            # Start main trading loop
            self.should_stop.clear()
            self.is_paused.clear()
            self.emergency_stop_triggered.clear()
            
            self.main_thread = threading.Thread(target=self._main_trading_loop, daemon=True)
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            
            self.main_thread.start()
            self.monitoring_thread.start()
            
            self.state = SystemState.RUNNING
            self.stats.system_start_time = datetime.now()
            
            logger.info("🚀 Automated Trading System STARTED")
            self._send_notification("System Started", "Automated trading system is now running")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.state = SystemState.ERROR
            return False
    
    def stop_system(self, emergency: bool = False) -> bool:
        """Stop the automated trading system."""
        try:
            if emergency:
                self.state = SystemState.EMERGENCY_STOP
                self.emergency_stop_triggered.set()
                logger.critical("🚨 EMERGENCY STOP TRIGGERED")
            else:
                self.state = SystemState.STOPPING
            
            # Signal threads to stop
            self.should_stop.set()
            
            # Wait for threads to finish
            if self.main_thread and self.main_thread.is_alive():
                self.main_thread.join(timeout=30)
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=10)
            
            self.state = SystemState.STOPPED
            
            # Generate final report
            self._generate_session_report()
            
            logger.info("🛑 Automated Trading System STOPPED")
            self._send_notification("System Stopped", "Automated trading system has been stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")
            return False
    
    def pause_system(self) -> bool:
        """Pause the trading system temporarily."""
        if self.state == SystemState.RUNNING:
            self.is_paused.set()
            self.state = SystemState.PAUSED
            logger.info("⏸️ System PAUSED")
            return True
        return False
    
    def resume_system(self) -> bool:
        """Resume the trading system from pause."""
        if self.state == SystemState.PAUSED:
            self.is_paused.clear()
            self.state = SystemState.RUNNING
            logger.info("▶️ System RESUMED")
            return True
        return False
    
    def _main_trading_loop(self):
        """Main trading loop that runs continuously."""
        logger.info("Main trading loop started")
        
        while not self.should_stop.is_set():
            try:
                # Check for pause
                if self.is_paused.is_set():
                    time.sleep(1)
                    continue
                
                # Check emergency stop
                if self.emergency_stop_triggered.is_set():
                    break
                
                # Execute trading cycle
                self._execute_trading_cycle()
                
                # Adaptive sleep based on market conditions
                sleep_time = self._calculate_sleep_time()
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in main trading loop: {e}")
                self.stats.errors_today.append(f"{datetime.now()}: {str(e)}")
                time.sleep(10)  # Sleep longer on error
        
        logger.info("Main trading loop stopped")
    
    def _monitoring_loop(self):
        """Monitoring loop for safety checks and performance tracking."""
        logger.info("Monitoring loop started")
        
        while not self.should_stop.is_set():
            try:
                # Perform safety checks
                if not self._perform_safety_checks():
                    logger.critical("Safety check failed - triggering emergency stop")
                    self.stop_system(emergency=True)
                    break
                
                # Update health metrics
                self._update_health_metrics()
                
                # Log performance metrics
                self._log_performance_metrics()
                
                # Sleep for monitoring interval
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
        
        logger.info("Monitoring loop stopped")
    
    def _execute_trading_cycle(self):
        """Execute one complete trading cycle."""
        try:
            # Get current market window
            current_window = self.window_manager.get_current_window()
            
            # Skip if market is closed and not configured for extended hours
            if current_window == TradingWindow.CLOSED:
                if self.automation_mode == AutomationMode.MARKET_HOURS_ONLY:
                    return
            
            # Fetch market data
            market_data = self._fetch_market_data()
            if not market_data:
                return
            
            # Analyze market conditions using LLM
            market_analysis = self._analyze_market_conditions(market_data)
            
            # Generate trading signals
            signals = self._generate_trading_signals(market_data, market_analysis)
            
            # Filter signals based on current window and safety
            filtered_signals = self._filter_signals_by_window(signals, current_window)
            
            # Execute approved trades
            for signal in filtered_signals:
                if self._should_execute_trade(signal):
                    self._execute_trade(signal)
            
            # Update statistics
            self._update_cycle_stats()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            self.stats.errors_today.append(f"{datetime.now()}: Trading cycle error: {str(e)}")
    
    def _fetch_market_data(self) -> Optional[Dict[str, Any]]:
        """Fetch current market data."""
        try:
            if self.data_fetch_callback:
                return self.data_fetch_callback()
            else:
                # Placeholder for market data fetching
                return {
                    'timestamp': datetime.now(),
                    'market_open': True,
                    'volatility': 'normal'
                }
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    def _analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions using LLM."""
        try:
            # Use LLM for market regime detection
            analysis_prompt = f"""
            Analyze current market conditions:
            Data: {json.dumps(market_data, default=str)}
            
            Provide:
            1. Market regime classification
            2. Volatility assessment
            3. Risk level recommendation
            4. Trading opportunity assessment
            """
            
            result = self.llm_router.route_task(
                TaskType.MARKET_REGIME_DETECTION,
                analysis_prompt,
                market_data
            )
            
            return {
                'analysis': result['response'],
                'llm_used': result['llm_used'],
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {'analysis': 'Error in analysis', 'risk_level': 'high'}
    
    def _generate_trading_signals(self, market_data: Dict[str, Any], 
                                market_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals based on analysis."""
        # Placeholder for signal generation
        # This would integrate with your existing indicator system
        signals = []
        
        try:
            # Example signal generation logic
            if 'opportunity' in market_analysis.get('analysis', '').lower():
                signals.append({
                    'symbol': 'SPY',
                    'action': 'buy',
                    'confidence': 0.75,
                    'strategy': StrategyType.MOMENTUM_CONTINUATION,
                    'reasoning': market_analysis.get('analysis', '')
                })
        
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
        
        return signals
    
    def _filter_signals_by_window(self, signals: List[Dict[str, Any]], 
                                window: TradingWindow) -> List[Dict[str, Any]]:
        """Filter signals based on current trading window."""
        filtered = []
        
        for signal in signals:
            strategy = signal.get('strategy')
            confidence = signal.get('confidence', 0)
            
            # Check if trade should proceed
            decision = self.window_manager.should_trade_now(
                strategy, confidence, self.stats.trades_today
            )
            
            if decision['should_trade']:
                signal['window_decision'] = decision
                filtered.append(signal)
            else:
                logger.debug(f"Signal filtered out: {decision['reason']}")
        
        return filtered
    
    def _should_execute_trade(self, signal: Dict[str, Any]) -> bool:
        """Determine if a trade should be executed based on safety checks."""
        try:
            # Check daily trade limit
            if self.stats.trades_today >= self.safety_limits.max_daily_trades:
                return False
            
            # Check daily loss limit
            loss_pct = abs(self.stats.daily_pnl) / self.safety_limits.min_account_balance
            if loss_pct >= self.safety_limits.max_daily_loss_pct:
                return False
            
            # Check consecutive losses
            if self.stats.consecutive_losses >= self.safety_limits.max_consecutive_losses:
                return False
            
            # For supervised mode, require approval
            if self.automation_mode == AutomationMode.SUPERVISED:
                return self._request_trade_approval(signal)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in trade execution check: {e}")
            return False
    
    def _execute_trade(self, signal: Dict[str, Any]):
        """Execute a trade signal."""
        try:
            if self.automation_mode == AutomationMode.PAPER_TRADING:
                # Simulate trade execution
                self._simulate_trade(signal)
            else:
                # Real trade execution
                if self.trade_execution_callback:
                    result = self.trade_execution_callback(signal)
                    self._process_trade_result(signal, result)
            
            self.stats.trades_today += 1
            self.stats.last_trade_time = datetime.now()
            
            # Log trade decision
            self._log_trade_decision(signal)
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self.stats.failed_trades += 1
    
    def _simulate_trade(self, signal: Dict[str, Any]):
        """Simulate trade execution for paper trading."""
        # Simple simulation - assume trade succeeds with random outcome
        import random
        
        success = random.random() > 0.3  # 70% success rate
        pnl = random.uniform(-50, 100) if success else random.uniform(-100, -10)
        
        self.stats.daily_pnl += pnl
        
        if success:
            self.stats.successful_trades += 1
            self.stats.consecutive_losses = 0
        else:
            self.stats.failed_trades += 1
            self.stats.consecutive_losses += 1
        
        logger.info(f"📊 Paper trade: {signal['symbol']} {signal['action']} - P&L: ${pnl:.2f}")
    
    def _perform_startup_checks(self) -> bool:
        """Perform system startup health checks."""
        try:
            logger.info("Performing startup health checks...")
            
            # Check API connectivity
            if not self._check_connectivity():
                logger.error("Connectivity check failed")
                return False
            
            # Check account balance
            if not self._check_account_balance():
                logger.error("Account balance check failed")
                return False
            
            # Check market data access
            if not self._check_market_data_access():
                logger.error("Market data access check failed")
                return False
            
            logger.info("✅ All startup checks passed")
            return True
            
        except Exception as e:
            logger.error(f"Startup check error: {e}")
            return False
    
    def _perform_safety_checks(self) -> bool:
        """Perform ongoing safety checks."""
        try:
            # Check daily loss limit
            if self.stats.daily_pnl < -self.safety_limits.circuit_breaker_loss_pct * self.safety_limits.min_account_balance:
                logger.critical(f"Circuit breaker triggered: Daily loss ${self.stats.daily_pnl:.2f}")
                return False
            
            # Check consecutive losses
            if self.stats.consecutive_losses >= self.safety_limits.max_consecutive_losses:
                logger.warning(f"Consecutive loss limit reached: {self.stats.consecutive_losses}")
                return False
            
            # Check system health
            self.stats.last_health_check = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Safety check error: {e}")
            return False
    
    def _calculate_sleep_time(self) -> float:
        """Calculate adaptive sleep time based on market conditions."""
        current_window = self.window_manager.get_current_window()
        
        # Sleep times by window (seconds)
        sleep_times = {
            TradingWindow.PRE_MARKET: 30,
            TradingWindow.OPENING_RANGE: 5,
            TradingWindow.MORNING_SESSION: 10,
            TradingWindow.LUNCH_SESSION: 60,
            TradingWindow.AFTERNOON_SESSION: 10,
            TradingWindow.CLOSING_SESSION: 5,
            TradingWindow.POST_MARKET: 30,
            TradingWindow.CLOSED: 300  # 5 minutes when closed
        }
        
        return sleep_times.get(current_window, 30)
    
    def _send_notification(self, title: str, message: str, priority: str = "info"):
        """Send notification through registered callback."""
        try:
            if self.notification_callback:
                self.notification_callback({
                    'title': title,
                    'message': message,
                    'priority': priority,
                    'timestamp': datetime.now()
                })
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'state': self.state.value,
            'automation_mode': self.automation_mode.value,
            'current_window': self.window_manager.get_current_window().value,
            'stats': {
                'uptime': datetime.now() - self.stats.system_start_time,
                'trades_today': self.stats.trades_today,
                'success_rate': self.stats.successful_trades / max(1, self.stats.trades_today),
                'daily_pnl': self.stats.daily_pnl,
                'consecutive_losses': self.stats.consecutive_losses
            },
            'safety_status': {
                'within_loss_limits': self.stats.daily_pnl > -self.safety_limits.circuit_breaker_loss_pct * self.safety_limits.min_account_balance,
                'within_trade_limits': self.stats.trades_today < self.safety_limits.max_daily_trades,
                'connectivity_ok': self._check_connectivity()
            },
            'next_window_change': self.window_manager.get_next_window_change()
        }
    
    # Placeholder methods for external integration
    def _check_connectivity(self) -> bool:
        """Check system connectivity."""
        return True  # Placeholder
    
    def _check_account_balance(self) -> bool:
        """Check account balance."""
        return True  # Placeholder
    
    def _check_market_data_access(self) -> bool:
        """Check market data access."""
        return True  # Placeholder
    
    def _request_trade_approval(self, signal: Dict[str, Any]) -> bool:
        """Request human approval for trade (supervised mode)."""
        return False  # Placeholder - would integrate with UI
    
    def _process_trade_result(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """Process the result of a trade execution."""
        pass  # Placeholder
    
    def _log_trade_decision(self, signal: Dict[str, Any]):
        """Log trade decision for analysis."""
        self.decision_log.append({
            'timestamp': datetime.now(),
            'signal': signal,
            'window': self.window_manager.get_current_window().value
        })
    
    def _update_cycle_stats(self):
        """Update cycle statistics."""
        pass
    
    def _update_health_metrics(self):
        """Update system health metrics."""
        pass
    
    def _log_performance_metrics(self):
        """Log performance metrics."""
        pass
    
    def _reset_daily_stats(self):
        """Reset daily statistics."""
        self.stats.trades_today = 0
        self.stats.successful_trades = 0
        self.stats.failed_trades = 0
        self.stats.daily_pnl = 0.0
        self.stats.consecutive_losses = 0
        self.stats.errors_today = []
    
    def _generate_session_report(self):
        """Generate end-of-session report."""
        report = {
            'session_duration': datetime.now() - self.stats.system_start_time,
            'total_trades': self.stats.trades_today,
            'successful_trades': self.stats.successful_trades,
            'success_rate': self.stats.successful_trades / max(1, self.stats.trades_today),
            'daily_pnl': self.stats.daily_pnl,
            'errors': len(self.stats.errors_today)
        }
        
        logger.info(f"📊 Session Report: {report}")
        return report
