"""
Trading window configuration for time-based strategy execution.
Implements structured time windows with regime-specific strategies.
"""
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, time, timezone, timedelta
import pytz
from loguru import logger


class TradingWindow(Enum):
    """Trading window types with specific characteristics."""
    PRE_MARKET = "pre_market"
    OPENING_RANGE = "opening_range"
    MORNING_SESSION = "morning_session"
    LUNCH_SESSION = "lunch_session"
    AFTERNOON_SESSION = "afternoon_session"
    CLOSING_SESSION = "closing_session"
    POST_MARKET = "post_market"
    CLOSED = "closed"


class StrategyType(Enum):
    """Strategy types optimized for different time windows."""
    GAP_BREAKOUT = "gap_breakout"
    NEWS_SPIKE_REVERSAL = "news_spike_reversal"
    ORB_BREAKOUT = "orb_breakout"
    VWAP_RECLAIM = "vwap_reclaim"
    RSI_ZSCORE_FADE = "rsi_zscore_fade"
    VOLUME_TREND_CONTINUATION = "volume_trend_continuation"
    EMA_CROSSOVER = "ema_crossover"
    SECTOR_ROTATION = "sector_rotation"
    VWAP_REVERSAL = "vwap_reversal"
    LATE_VOLUME_SPIKE = "late_volume_spike"
    EARNINGS_BREAKOUT = "earnings_breakout"
    REACTION_CONTINUATION = "reaction_continuation"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM_CONTINUATION = "momentum_continuation"


@dataclass
class WindowConfig:
    """Configuration for a trading window."""
    start_time: time
    end_time: time
    description: str
    risk_level: str  # LOW, MEDIUM, HIGH
    liquidity_level: str  # LOW, MEDIUM, HIGH
    spread_impact: str  # LOW, MEDIUM, HIGH
    allowed_strategies: List[StrategyType]
    position_size_multiplier: float  # Adjust position size for this window
    min_confidence_threshold: float  # Minimum confidence required
    max_trades_per_window: int
    special_considerations: List[str]


class TradingWindowManager:
    """Manages trading windows and strategy allocation."""
    
    # Trading window definitions (Eastern Time)
    TRADING_WINDOWS = {
        TradingWindow.PRE_MARKET: WindowConfig(
            start_time=time(7, 30),
            end_time=time(9, 15),
            description="Pre-market scan and gap analysis",
            risk_level="HIGH",
            liquidity_level="LOW",
            spread_impact="HIGH",
            allowed_strategies=[
                StrategyType.GAP_BREAKOUT,
                StrategyType.NEWS_SPIKE_REVERSAL,
                StrategyType.EARNINGS_BREAKOUT
            ],
            position_size_multiplier=0.5,  # Reduce size due to risk
            min_confidence_threshold=0.8,  # Higher confidence required
            max_trades_per_window=3,
            special_considerations=[
                "Wide spreads",
                "Low liquidity",
                "News-driven volatility",
                "Gap analysis priority"
            ]
        ),
        
        TradingWindow.OPENING_RANGE: WindowConfig(
            start_time=time(9, 30),
            end_time=time(10, 0),
            description="Opening range breakouts and VWAP analysis",
            risk_level="MEDIUM",
            liquidity_level="HIGH",
            spread_impact="MEDIUM",
            allowed_strategies=[
                StrategyType.ORB_BREAKOUT,
                StrategyType.VWAP_RECLAIM,
                StrategyType.VOLUME_TREND_CONTINUATION
            ],
            position_size_multiplier=0.8,
            min_confidence_threshold=0.7,
            max_trades_per_window=5,
            special_considerations=[
                "High volume expected",
                "Range establishment critical",
                "VWAP anchor point"
            ]
        ),
        
        TradingWindow.MORNING_SESSION: WindowConfig(
            start_time=time(10, 0),
            end_time=time(11, 30),
            description="Momentum fades and mean reversion",
            risk_level="LOW",
            liquidity_level="HIGH",
            spread_impact="LOW",
            allowed_strategies=[
                StrategyType.RSI_ZSCORE_FADE,
                StrategyType.MEAN_REVERSION,
                StrategyType.VOLUME_TREND_CONTINUATION,
                StrategyType.VWAP_REVERSAL
            ],
            position_size_multiplier=1.0,  # Normal sizing
            min_confidence_threshold=0.6,
            max_trades_per_window=8,
            special_considerations=[
                "Optimal liquidity",
                "Clear trend patterns",
                "Best execution window"
            ]
        ),
        
        TradingWindow.LUNCH_SESSION: WindowConfig(
            start_time=time(11, 30),
            end_time=time(13, 30),
            description="Low priority - avoid unless trending low-vol",
            risk_level="MEDIUM",
            liquidity_level="MEDIUM",
            spread_impact="MEDIUM",
            allowed_strategies=[
                StrategyType.MEAN_REVERSION,
                StrategyType.SECTOR_ROTATION
            ],
            position_size_multiplier=0.6,  # Reduced activity
            min_confidence_threshold=0.75,  # Higher threshold
            max_trades_per_window=2,
            special_considerations=[
                "Reduced volume",
                "Institutional lunch break",
                "Avoid unless strong regime"
            ]
        ),
        
        TradingWindow.AFTERNOON_SESSION: WindowConfig(
            start_time=time(13, 30),
            end_time=time(15, 30),
            description="Power hour build-up and trend continuation",
            risk_level="LOW",
            liquidity_level="HIGH",
            spread_impact="LOW",
            allowed_strategies=[
                StrategyType.EMA_CROSSOVER,
                StrategyType.MOMENTUM_CONTINUATION,
                StrategyType.SECTOR_ROTATION,
                StrategyType.VOLUME_TREND_CONTINUATION
            ],
            position_size_multiplier=1.0,
            min_confidence_threshold=0.65,
            max_trades_per_window=6,
            special_considerations=[
                "Institutional activity resumes",
                "Trend continuation favored",
                "Good execution environment"
            ]
        ),
        
        TradingWindow.CLOSING_SESSION: WindowConfig(
            start_time=time(15, 30),
            end_time=time(16, 0),
            description="Closing reversals and liquidity events",
            risk_level="HIGH",
            liquidity_level="HIGH",
            spread_impact="MEDIUM",
            allowed_strategies=[
                StrategyType.VWAP_REVERSAL,
                StrategyType.LATE_VOLUME_SPIKE,
                StrategyType.MEAN_REVERSION
            ],
            position_size_multiplier=0.7,  # Reduced due to volatility
            min_confidence_threshold=0.75,
            max_trades_per_window=3,
            special_considerations=[
                "Stop hunts common",
                "Institutional rebalancing",
                "High volatility potential",
                "Quick reversals possible"
            ]
        ),
        
        TradingWindow.POST_MARKET: WindowConfig(
            start_time=time(16, 0),
            end_time=time(18, 0),
            description="Earnings reactions and after-hours momentum",
            risk_level="HIGH",
            liquidity_level="LOW",
            spread_impact="HIGH",
            allowed_strategies=[
                StrategyType.EARNINGS_BREAKOUT,
                StrategyType.REACTION_CONTINUATION,
                StrategyType.NEWS_SPIKE_REVERSAL
            ],
            position_size_multiplier=0.4,  # Significantly reduced
            min_confidence_threshold=0.85,  # Very high confidence required
            max_trades_per_window=2,
            special_considerations=[
                "Earnings-driven moves",
                "HFT activity heavy",
                "Wide spreads",
                "Swing setup preparation"
            ]
        )
    }
    
    def __init__(self, timezone_str: str = "US/Eastern"):
        """Initialize trading window manager."""
        self.timezone = pytz.timezone(timezone_str)
        self.current_window = TradingWindow.CLOSED
        self.window_stats = {}
        self.automation_config = {
            'auto_start': True,
            'auto_stop': True,
            'safety_stops': True,
            'max_daily_trades': 25,
            'max_daily_loss': 0.02,  # 2% of account
            'emergency_stop_conditions': [
                'market_circuit_breaker',
                'system_error',
                'connectivity_loss'
            ]
        }
        
        logger.info(f"Trading Window Manager initialized for {timezone_str}")
    
    def get_current_window(self, current_time: Optional[datetime] = None) -> TradingWindow:
        """Get the current trading window."""
        if current_time is None:
            current_time = datetime.now(self.timezone)
        
        current_time_only = current_time.time()
        
        # Check each window
        for window, config in self.TRADING_WINDOWS.items():
            if config.start_time <= current_time_only <= config.end_time:
                self.current_window = window
                return window
        
        # If not in any window, market is closed
        self.current_window = TradingWindow.CLOSED
        return TradingWindow.CLOSED
    
    def get_window_config(self, window: TradingWindow) -> WindowConfig:
        """Get configuration for a specific window."""
        return self.TRADING_WINDOWS.get(window)
    
    def is_strategy_allowed(self, strategy: StrategyType, 
                          window: Optional[TradingWindow] = None) -> bool:
        """Check if a strategy is allowed in current or specified window."""
        if window is None:
            window = self.get_current_window()
        
        if window == TradingWindow.CLOSED:
            return False
        
        config = self.get_window_config(window)
        return strategy in config.allowed_strategies
    
    def get_position_size_multiplier(self, window: Optional[TradingWindow] = None) -> float:
        """Get position size multiplier for current or specified window."""
        if window is None:
            window = self.get_current_window()
        
        if window == TradingWindow.CLOSED:
            return 0.0
        
        config = self.get_window_config(window)
        return config.position_size_multiplier
    
    def get_confidence_threshold(self, window: Optional[TradingWindow] = None) -> float:
        """Get minimum confidence threshold for current or specified window."""
        if window is None:
            window = self.get_current_window()
        
        if window == TradingWindow.CLOSED:
            return 1.0  # No trades when closed
        
        config = self.get_window_config(window)
        return config.min_confidence_threshold
    
    def should_trade_now(self, strategy: StrategyType, confidence: float,
                        current_trades_in_window: int = 0) -> Dict[str, Any]:
        """
        Determine if trading should occur now based on multiple factors.
        
        Returns decision with reasoning.
        """
        current_window = self.get_current_window()
        
        if current_window == TradingWindow.CLOSED:
            return {
                'should_trade': False,
                'reason': 'Market is closed',
                'window': current_window.value,
                'confidence_required': 1.0,
                'confidence_provided': confidence
            }
        
        config = self.get_window_config(current_window)
        
        # Check strategy allowance
        if not self.is_strategy_allowed(strategy, current_window):
            return {
                'should_trade': False,
                'reason': f'Strategy {strategy.value} not allowed in {current_window.value}',
                'window': current_window.value,
                'allowed_strategies': [s.value for s in config.allowed_strategies]
            }
        
        # Check confidence threshold
        if confidence < config.min_confidence_threshold:
            return {
                'should_trade': False,
                'reason': f'Confidence {confidence:.2f} below threshold {config.min_confidence_threshold:.2f}',
                'window': current_window.value,
                'confidence_required': config.min_confidence_threshold,
                'confidence_provided': confidence
            }
        
        # Check trade count limit
        if current_trades_in_window >= config.max_trades_per_window:
            return {
                'should_trade': False,
                'reason': f'Max trades per window ({config.max_trades_per_window}) reached',
                'window': current_window.value,
                'trades_taken': current_trades_in_window
            }
        
        # All checks passed
        return {
            'should_trade': True,
            'reason': 'All conditions met',
            'window': current_window.value,
            'position_size_multiplier': config.position_size_multiplier,
            'risk_level': config.risk_level,
            'special_considerations': config.special_considerations
        }
    
    def get_window_schedule(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get the full trading window schedule for a date."""
        if date is None:
            date = datetime.now(self.timezone)
        
        schedule = {}
        for window, config in self.TRADING_WINDOWS.items():
            start_dt = datetime.combine(date.date(), config.start_time)
            end_dt = datetime.combine(date.date(), config.end_time)
            
            schedule[window.value] = {
                'start': start_dt.replace(tzinfo=self.timezone),
                'end': end_dt.replace(tzinfo=self.timezone),
                'description': config.description,
                'strategies': [s.value for s in config.allowed_strategies],
                'risk_level': config.risk_level,
                'max_trades': config.max_trades_per_window
            }
        
        return schedule
    
    def configure_automation(self, auto_start: bool = True, auto_stop: bool = True,
                           max_daily_trades: int = 25, max_daily_loss: float = 0.02) -> None:
        """Configure automation settings."""
        self.automation_config.update({
            'auto_start': auto_start,
            'auto_stop': auto_stop,
            'max_daily_trades': max_daily_trades,
            'max_daily_loss': max_daily_loss
        })
        
        logger.info(f"Automation configured: auto_start={auto_start}, auto_stop={auto_stop}")
    
    def get_next_window_change(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get information about the next window change."""
        if current_time is None:
            current_time = datetime.now(self.timezone)
        
        current_window = self.get_current_window(current_time)
        current_time_only = current_time.time()
        
        # Find next window
        next_window = None
        next_time = None
        
        for window, config in self.TRADING_WINDOWS.items():
            if config.start_time > current_time_only:
                if next_time is None or config.start_time < next_time:
                    next_window = window
                    next_time = config.start_time
        
        # If no window found today, get first window tomorrow
        if next_window is None:
            next_day = current_time + timedelta(days=1)
            first_window = min(self.TRADING_WINDOWS.items(), 
                             key=lambda x: x[1].start_time)
            next_window = first_window[0]
            next_time = datetime.combine(next_day.date(), first_window[1].start_time)
        else:
            next_time = datetime.combine(current_time.date(), next_time)
        
        next_time = next_time.replace(tzinfo=self.timezone)
        time_until = next_time - current_time
        
        return {
            'current_window': current_window.value,
            'next_window': next_window.value,
            'next_change_time': next_time,
            'time_until_change': time_until,
            'minutes_until_change': time_until.total_seconds() / 60
        }


# Window strategies mapping for easy reference
WINDOW_STRATEGIES = {
    TradingWindow.PRE_MARKET: ["gap_breakout", "news_spike_reversal", "earnings_breakout"],
    TradingWindow.OPENING_RANGE: ["orb_breakout", "vwap_reclaim", "volume_trend_continuation"],
    TradingWindow.MORNING_SESSION: ["rsi_zscore_fade", "mean_reversion", "volume_trend_continuation"],
    TradingWindow.AFTERNOON_SESSION: ["ema_crossover", "momentum_continuation", "sector_rotation"],
    TradingWindow.CLOSING_SESSION: ["vwap_reversal", "late_volume_spike", "mean_reversion"],
    TradingWindow.POST_MARKET: ["earnings_breakout", "reaction_continuation", "news_spike_reversal"]
}


def get_optimal_strategies_for_time(window_manager: TradingWindowManager, 
                                  current_time: Optional[datetime] = None) -> List[str]:
    """Get optimal strategies for current time."""
    window = window_manager.get_current_window(current_time)
    return WINDOW_STRATEGIES.get(window, [])
