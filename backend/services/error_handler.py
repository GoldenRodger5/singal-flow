"""
Production Error Handling and Circuit Breaker System
Prevents cascade failures and implements automatic recovery
"""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from loguru import logger
import functools

from services.database_manager import get_db_manager


class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # Failures before opening
    timeout: int = 60              # Seconds before trying half-open
    success_threshold: int = 2      # Successes to close from half-open
    reset_timeout: int = 300       # Seconds to reset failure count


class CircuitBreaker:
    """Circuit breaker for external API calls"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_reset_time = time.time()
        
    def _should_attempt_call(self) -> bool:
        """Determine if call should be attempted"""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if current_time - self.last_failure_time >= self.config.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} moving to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self):
        """Record successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.last_reset_time = time.time()
                logger.info(f"Circuit breaker {self.name} CLOSED - service recovered")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count periodically on success
            current_time = time.time()
            if current_time - self.last_reset_time >= self.config.reset_timeout:
                self.failure_count = 0
                self.last_reset_time = current_time
    
    def _record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker {self.name} OPENED - service failing")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {self.name} back to OPEN - service still failing")
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if not self._should_attempt_call():
            raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            
            # Log circuit breaker activity
            db_manager = get_db_manager()
            await db_manager.log_system_health(
                f"circuit_breaker_{self.name}",
                "failure",
                {
                    "state": self.state.value,
                    "failure_count": self.failure_count,
                    "error": str(e)
                }
            )
            
            raise e
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout": self.config.timeout,
                "success_threshold": self.config.success_threshold
            }
        }


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class ErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self):
        self.circuit_breakers = {
            'alpaca_api': CircuitBreaker('alpaca_api', CircuitBreakerConfig(
                failure_threshold=3,
                timeout=30,
                success_threshold=2
            )),
            'openai_api': CircuitBreaker('openai_api', CircuitBreakerConfig(
                failure_threshold=5,
                timeout=60,
                success_threshold=2
            )),
            'database': CircuitBreaker('database', CircuitBreakerConfig(
                failure_threshold=2,
                timeout=15,
                success_threshold=1
            )),
            'telegram_api': CircuitBreaker('telegram_api', CircuitBreakerConfig(
                failure_threshold=3,
                timeout=30,
                success_threshold=2
            ))
        }
        
        self.error_counts = {}
        self.last_error_reset = time.time()
    
    def circuit_breaker(self, service_name: str):
        """Decorator for circuit breaker protection"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                breaker = self.circuit_breakers.get(service_name)
                if not breaker:
                    logger.warning(f"No circuit breaker configured for {service_name}")
                    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                return await breaker.call(func, *args, **kwargs)
            return wrapper
        return decorator
    
    async def retry_with_backoff(self, func: Callable, max_retries: int = 3, 
                                base_delay: float = 1.0, max_delay: float = 60.0,
                                exponential_base: float = 2.0):
        """Retry function with exponential backoff"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    break
                
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {str(e)}")
                await asyncio.sleep(delay)
        
        # Log final failure
        db_manager = get_db_manager()
        await db_manager.log_system_health(
            "retry_exhausted",
            "failure",
            {
                "function": func.__name__ if hasattr(func, '__name__') else str(func),
                "attempts": max_retries + 1,
                "final_error": str(last_exception)
            }
        )
        
        raise last_exception
    
    async def handle_trading_error(self, error: Exception, context: Dict[str, Any]):
        """Handle trading-specific errors"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Count errors by type
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Log comprehensive error information
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "count_today": self.error_counts[error_type],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        db_manager = get_db_manager()
        await db_manager.log_system_health("trading_error", "error", error_data)
        
        # Determine if this is a critical error requiring immediate action
        critical_errors = [
            'InsufficientFundsError',
            'AccountSuspendedError',
            'MarketClosedError',
            'APIConnectionError'
        ]
        
        if error_type in critical_errors:
            logger.critical(f"Critical trading error: {error_type} - {error_message}")
            await self.trigger_emergency_protocols(error_data)
        
        # Check for error rate limits
        current_time = time.time()
        if current_time - self.last_error_reset >= 3600:  # Reset hourly
            self.error_counts.clear()
            self.last_error_reset = current_time
        
        # If too many errors of same type, suggest action
        if self.error_counts[error_type] >= 10:
            logger.error(f"High error rate for {error_type}: {self.error_counts[error_type]} occurrences")
            await self.suggest_remedial_action(error_type, error_data)
    
    async def trigger_emergency_protocols(self, error_data: Dict[str, Any]):
        """Trigger emergency protocols for critical errors"""
        logger.critical("EMERGENCY PROTOCOLS TRIGGERED")
        
        emergency_actions = []
        
        # Cancel all pending orders
        try:
            from services.alpaca_trading import TradingService
            trading_service = TradingService()
            orders = await trading_service.get_orders()
            
            for order in orders:
                try:
                    await trading_service.cancel_order(order.id)
                    emergency_actions.append(f"Cancelled order {order.id}")
                except Exception as e:
                    logger.error(f"Failed to cancel order {order.id}: {e}")
        except Exception as e:
            logger.error(f"Emergency order cancellation failed: {e}")
        
        # Log emergency action
        db_manager = get_db_manager()
        await db_manager.log_system_health(
            "emergency_protocols",
            "executed",
            {
                "trigger_error": error_data,
                "actions_taken": emergency_actions,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Send emergency notification (if Telegram is available)
        try:
            from services.telegram_trading import telegram_trading
            await telegram_trading.send_emergency_alert(
                f"🚨 EMERGENCY PROTOCOLS TRIGGERED\n"
                f"Error: {error_data.get('error_type', 'Unknown')}\n"
                f"Actions: {', '.join(emergency_actions)}"
            )
        except Exception as e:
            logger.error(f"Emergency notification failed: {e}")
    
    async def suggest_remedial_action(self, error_type: str, error_data: Dict[str, Any]):
        """Suggest remedial actions for recurring errors"""
        suggestions = {
            'ConnectionError': "Check internet connection and API endpoints",
            'AuthenticationError': "Verify API keys and credentials",
            'RateLimitError': "Implement rate limiting or reduce API call frequency",
            'InsufficientFundsError': "Check account balance and reduce position sizes",
            'ValidationError': "Review order parameters and market conditions"
        }
        
        suggestion = suggestions.get(error_type, "Review system logs and consider manual intervention")
        
        logger.warning(f"Remedial action suggested for {error_type}: {suggestion}")
        
        db_manager = get_db_manager()
        await db_manager.log_system_health(
            "remedial_suggestion",
            "suggested",
            {
                "error_type": error_type,
                "suggestion": suggestion,
                "error_count": self.error_counts.get(error_type, 0)
            }
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive error handling status"""
        return {
            "circuit_breakers": {name: cb.get_status() for name, cb in self.circuit_breakers.items()},
            "error_counts": self.error_counts.copy(),
            "last_error_reset": self.last_error_reset,
            "timestamp": time.time()
        }


# Global error handler instance
error_handler = ErrorHandler()
