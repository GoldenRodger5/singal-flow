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
    
    # API Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET = os.getenv('ALPACA_SECRET')
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    WHATSAPP_FROM = os.getenv('WHATSAPP_FROM', 'whatsapp:+14155238886')
    WHATSAPP_TO = os.getenv('WHATSAPP_TO')
    
    # Trading Parameters
    TICKER_PRICE_MIN = float(os.getenv('TICKER_PRICE_MIN', 1))
    TICKER_PRICE_MAX = float(os.getenv('TICKER_PRICE_MAX', 50))
    RR_THRESHOLD = float(os.getenv('RR_THRESHOLD', 2.0))
    MIN_EXPECTED_MOVE = float(os.getenv('MIN_EXPECTED_MOVE', 0.03))
    TRADING_START_TIME = os.getenv('TRADING_START_TIME', '09:45')
    TRADING_END_TIME = os.getenv('TRADING_END_TIME', '11:30')
    
    # System Configuration
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
    
    # API URLs
    POLYGON_BASE_URL = os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io')
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    # Trading Strategy Configuration - Dynamic Thresholds
    RSI_OVERSOLD_THRESHOLD = 30  # Base threshold - will be dynamically adjusted
    RSI_OVERBOUGHT_THRESHOLD = 70  # Base threshold - will be dynamically adjusted
    VOLUME_SPIKE_MULTIPLIER = 2.0
    MIN_CONFIDENCE_SCORE = 7.0  # Base confidence - will be dynamically adjusted
    MAX_DAILY_TRADES = 5
    POSITION_SIZE_PERCENT = 0.1  # Base position size - will be volatility adjusted
    
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
    
    # Data Configuration
    WATCHLIST_SIZE = 50
    DATA_REFRESH_INTERVAL = 120  # seconds
    SCREENER_UPDATE_INTERVAL = 300  # seconds
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate that all required configuration is present."""
        required_keys = [
            'POLYGON_API_KEY',
            'ALPACA_API_KEY',
            'ALPACA_SECRET',
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'WHATSAPP_TO'
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
