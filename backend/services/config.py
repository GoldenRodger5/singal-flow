"""
Configuration management for Signal Flow trading system.
"""
import os
from typing import Any, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class for the trading system."""
    
    # API Configuration - Fixed environment variable names
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET = os.getenv('ALPACA_SECRET_KEY')  # Fixed: was ALPACA_SECRET
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    # Telegram Configuration (Primary notification method)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Trading Parameters - Optimized for Low-Cap Momentum Strategy
    TICKER_PRICE_MIN = float(os.getenv('TICKER_PRICE_MIN', 0.75))  # Lowered for penny stocks
    TICKER_PRICE_MAX = float(os.getenv('TICKER_PRICE_MAX', 10))    # Focused on low-cap range
    RR_THRESHOLD = float(os.getenv('RR_THRESHOLD', 1.8))  # Trail after 2:1, let winners run
    MIN_EXPECTED_MOVE = float(os.getenv('MIN_EXPECTED_MOVE', 0.08))  # 8% minimum for explosive moves
    TRADING_START_TIME = os.getenv('TRADING_START_TIME', '09:00')  # Pre-market gaps
    TRADING_END_TIME = os.getenv('TRADING_END_TIME', '16:00')      # Include power hour
    
    # Low-Cap Momentum Filters
    MIN_DAILY_VOLUME = int(os.getenv('MIN_DAILY_VOLUME', 2000000))  # 2M minimum volume
    MIN_RELATIVE_VOLUME = float(os.getenv('MIN_RELATIVE_VOLUME', 2.0))  # 2x average volume
    MAX_FLOAT_SHARES = int(os.getenv('MAX_FLOAT_SHARES', 100000000))  # 100M max float
    IDEAL_FLOAT_MIN = int(os.getenv('IDEAL_FLOAT_MIN', 10000000))   # 10M ideal min
    IDEAL_FLOAT_MAX = int(os.getenv('IDEAL_FLOAT_MAX', 50000000))   # 50M ideal max
    MIN_INTRADAY_RANGE = float(os.getenv('MIN_INTRADAY_RANGE', 0.05))  # 5% minimum volatility
    
    # System Configuration
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
    
    # Database Configuration (MongoDB Atlas)
    MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb+srv://username:password@cluster.mongodb.net/')
    MONGODB_NAME = os.getenv('MONGODB_NAME', 'signal_flow_trading')
    MONGODB_CONNECTION_TIMEOUT = int(os.getenv('MONGODB_CONNECTION_TIMEOUT', 10000))  # 10 seconds
    MONGODB_SERVER_TIMEOUT = int(os.getenv('MONGODB_SERVER_TIMEOUT', 10000))  # 10 seconds
    
    # Local Server Configuration
    LOCAL_SERVER_PORT = int(os.getenv('LOCAL_SERVER_PORT', 8000))
    ENABLE_LOCAL_WEBHOOKS = os.getenv('ENABLE_LOCAL_WEBHOOKS', 'true').lower() == 'true'
    
    # Telegram Configuration (Enhanced)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # API URLs
    POLYGON_BASE_URL = os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io')
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    # Enhanced Position Sizing for Low-Cap Momentum (Paper Trading)
    MAX_DAILY_TRADES = 100  # Massive increase for data collection during paper trading
    MAX_DAILY_LOSS_PCT = 0.15  # 15% max daily loss for aggressive learning
    POSITION_SIZE_PERCENT = 0.25  # Base 25% position size for low-cap momentum
    MAX_POSITION_SIZE_PERCENT = 0.50  # Allow up to 50% for highest confidence trades
    
    # Sub-$3 Stock Limits (Higher risk tolerance for smaller stocks)
    MAX_SUB_3_DOLLAR_EXPOSURE = 0.60  # Max 60% of portfolio in sub-$3 stocks
    SUB_3_DOLLAR_POSITION_BOOST = 0.10  # Additional 10% position size for sub-$3 stocks
    
    # Trading Strategy Configuration - Low-Cap Momentum Optimized
    RSI_OVERSOLD_THRESHOLD = 25  # More aggressive for volatile low-caps
    RSI_OVERBOUGHT_THRESHOLD = 75  # More aggressive for volatile low-caps
    VOLUME_SPIKE_MULTIPLIER = 3.0  # Require 3x volume spike for confirmation
    MIN_CONFIDENCE_SCORE = 6.0  # Lowered for paper trading data collection
    PAPER_TRADING_MIN_CONFIDENCE = 5.5  # Even lower for learning trades
    
    # Williams %R Configuration (Better than RSI for momentum)
    WILLIAMS_R_OVERSOLD = -80
    WILLIAMS_R_OVERBOUGHT = -20
    WILLIAMS_R_ENABLED = True
    
    # Bollinger Band Squeeze Detection
    BOLLINGER_SQUEEZE_ENABLED = True
    BOLLINGER_SQUEEZE_THRESHOLD = 0.1  # Volatility contraction threshold
    
    # Market Regime Detection Configuration
    VOLATILITY_LOOKBACK_DAYS = 20
    TREND_DETECTION_PERIOD = 50
    REGIME_DETECTION_ENABLED = True
    
    # Alternative Indicator Configuration
    RSI_ZSCORE_ENABLED = True
    ORDER_FLOW_ANALYSIS_ENABLED = True
    SECTOR_RELATIVE_STRENGTH_ENABLED = True
    
    # Risk Management Enhancement
    VOLATILITY_SCALING_ENABLED = True
    CORRELATION_ADJUSTMENT_ENABLED = True
    KELLY_CRITERION_SIZING = True
    MAX_PORTFOLIO_VOLATILITY = 0.15  # 15% annual volatility target
    
    # Auto Trading Configuration
    AUTO_TRADING_ENABLED = os.getenv('AUTO_TRADING_ENABLED', 'false').lower() == 'true'
    INTERACTIVE_TRADING_ENABLED = os.getenv('INTERACTIVE_TRADING_ENABLED', 'true').lower() == 'true'
    TRADE_CONFIRMATION_TIMEOUT = int(os.getenv('TRADE_CONFIRMATION_TIMEOUT', 30))  # seconds
    
    # Enhanced Data Collection Configuration
    WATCHLIST_SIZE = 100  # Doubled for more opportunities
    DATA_REFRESH_INTERVAL = 60   # Faster refresh for momentum detection
    SCREENER_UPDATE_INTERVAL = 180  # More frequent screening
    
    # Multi-Timeframe Trading Windows
    POWER_HOUR_ENABLED = True
    POWER_HOUR_START = "15:30"  # 3:30 PM
    POWER_HOUR_END = "16:00"    # 4:00 PM
    PREMARKET_ENABLED = True
    PREMARKET_START = "09:00"   # 9:00 AM
    PREMARKET_END = "09:30"     # 9:30 AM
    
    # Gap Trading Configuration
    MIN_GAP_PERCENT = 3.0  # Minimum 3% gap for gap-and-go
    MAX_GAP_PERCENT = 25.0  # Maximum 25% gap (avoid pump/dump)
    GAP_VOLUME_CONFIRMATION = 5.0  # Require 5x volume on gaps
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate that all required configuration is present."""
        required_keys = [
            'POLYGON_API_KEY',
            'ALPACA_API_KEY',
            'ALPACA_SECRET',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        return {
            'valid': len(missing_keys) == 0,
            'missing_keys': missing_keys,
            'paper_trading': cls.PAPER_TRADING,
            'environment': cls.ENVIRONMENT
        }
    
    @classmethod
    def get_trading_hours(cls) -> tuple:
        """Get trading hours as time objects."""
        from datetime import time
        
        start_parts = cls.TRADING_START_TIME.split(':')
        end_parts = cls.TRADING_END_TIME.split(':')
        
        start_time = time(int(start_parts[0]), int(start_parts[1]))
        end_time = time(int(end_parts[0]), int(end_parts[1]))
        
        return start_time, end_time
    
    def validate_required_keys(self) -> bool:
        """Validate that all required configuration keys are present."""
        required_keys = [
            'POLYGON_API_KEY',
            'ALPACA_API_KEY',
            'ALPACA_SECRET'  # This is the actual attribute name
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(self, key, None):
                missing_keys.append(key)
        
        if missing_keys:
            print(f"Missing required configuration keys: {missing_keys}")
            return False
        
        return True
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        from datetime import datetime, time
        
        now = datetime.now().time()
        start_time, end_time = self.get_trading_hours()
        
        return start_time <= now <= end_time
