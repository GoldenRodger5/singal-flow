"""
Enhanced Environment Variable Manager
Robust configuration loading with validation and fallbacks
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvManager:
    """Centralized environment variable management with validation"""
    
    def __init__(self):
        self._config_cache = {}
        self._load_environment()
        self._validate_critical_keys()
    
    def _load_environment(self):
        """Load environment variables from multiple possible locations"""
        # Possible .env file locations
        possible_paths = [
            # Current working directory
            Path.cwd() / '.env',
            # Parent directory (if running from backend/)
            Path.cwd().parent / '.env',
            # Explicit path from workspace root
            Path('/Users/isaacmineo/Main/projects/singal-flow/.env'),
            # Backend directory
            Path('/Users/isaacmineo/Main/projects/singal-flow/backend/.env'),
        ]
        
        loaded = False
        for env_path in possible_paths:
            if env_path.exists():
                logger.info(f"Loading environment from: {env_path}")
                load_dotenv(env_path, override=True)
                loaded = True
                break
        
        if not loaded:
            logger.warning("No .env file found, using system environment variables only")
        
        # Also load from system environment
        self._config_cache.update(dict(os.environ))
        
        logger.info(f"Loaded {len(self._config_cache)} environment variables")
    
    def _validate_critical_keys(self):
        """Validate that critical API keys are present"""
        critical_keys = [
            'ALPACA_API_KEY',
            'ALPACA_SECRET_KEY', 
            'POLYGON_API_KEY',
            'MONGODB_URL'
        ]
        
        missing_keys = []
        for key in critical_keys:
            if not self.get(key):
                missing_keys.append(key)
        
        if missing_keys:
            logger.error(f"Missing critical environment variables: {missing_keys}")
        else:
            logger.info("All critical API keys validated")
    
    def get(self, key: str, default: Any = None) -> Optional[str]:
        """Get environment variable with fallback"""
        # Check cache first
        if key in self._config_cache:
            value = self._config_cache[key]
            if value and value.strip():
                return value.strip()
        
        # Check os.environ directly
        value = os.getenv(key, default)
        if value and isinstance(value, str):
            value = value.strip()
            self._config_cache[key] = value
            return value
        
        # Check alternative key names
        alternatives = self._get_alternative_keys(key)
        for alt_key in alternatives:
            alt_value = os.getenv(alt_key)
            if alt_value and alt_value.strip():
                alt_value = alt_value.strip()
                self._config_cache[key] = alt_value
                logger.info(f"Using alternative key {alt_key} for {key}")
                return alt_value
        
        return default
    
    def _get_alternative_keys(self, key: str) -> list:
        """Get alternative environment variable names"""
        alternatives = {
            'ALPACA_SECRET_KEY': ['ALPACA_SECRET'],
            'ALPACA_API_KEY': ['BROKER_API_KEY'],
            'POLYGON_API_KEY': ['MARKET_DATA_API_KEY'],
            'CLAUDE_API_KEY': ['ANTHROPIC_API_KEY'],
        }
        return alternatives.get(key, [])
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = self.get(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable"""
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float environment variable"""
        try:
            return float(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def is_configured(self, key: str) -> bool:
        """Check if an environment variable is properly configured"""
        value = self.get(key)
        return value is not None and len(value.strip()) > 0
    
    def get_api_config(self) -> Dict[str, str]:
        """Get all API configuration in one place"""
        return {
            # Trading APIs
            'alpaca_api_key': self.get('ALPACA_API_KEY'),
            'alpaca_secret_key': self.get('ALPACA_SECRET_KEY'),
            'alpaca_base_url': self.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
            
            # Market Data
            'polygon_api_key': self.get('POLYGON_API_KEY'),
            'polygon_base_url': self.get('POLYGON_BASE_URL', 'https://api.polygon.io'),
            
            # AI APIs
            'openai_api_key': self.get('OPENAI_API_KEY'),
            'anthropic_api_key': self.get('ANTHROPIC_API_KEY'),
            'claude_api_key': self.get('CLAUDE_API_KEY'),
            
            # Database
            'mongodb_url': self.get('MONGODB_URL'),
            'mongodb_name': self.get('MONGODB_NAME', 'signal_flow_trading'),
            
            # Notifications
            'telegram_bot_token': self.get('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': self.get('TELEGRAM_CHAT_ID'),
        }
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate all API keys and return status"""
        config = self.get_api_config()
        validation_results = {}
        
        for key, value in config.items():
            if value and len(value.strip()) > 10:  # Basic length check
                validation_results[key] = True
                logger.info(f"✅ {key}: Configured")
            else:
                validation_results[key] = False
                logger.warning(f"❌ {key}: Not configured or too short")
        
        return validation_results
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading-specific configuration"""
        return {
            'system_mode': self.get('SYSTEM_MODE', 'paper_trading'),
            'automation_mode': self.get('AUTOMATION_MODE', 'supervised'),
            'paper_trading': self.get_bool('PAPER_TRADING', True),
            'auto_execute_signals': self.get_bool('AUTO_EXECUTE_SIGNALS', False),
            'max_daily_trades': self.get_int('MAX_DAILY_TRADES', 50),
            'max_daily_loss_pct': self.get_float('MAX_DAILY_LOSS_PCT', 0.025),
            'min_confidence_threshold': self.get_float('MIN_CONFIDENCE_THRESHOLD', 0.65),
            'default_position_size_pct': self.get_float('DEFAULT_POSITION_SIZE_PCT', 0.05),
            'max_position_size_pct': self.get_float('MAX_POSITION_SIZE_PCT', 0.10),
        }
    
    def print_config_summary(self):
        """Print a summary of current configuration"""
        print("\n" + "="*60)
        print("SIGNAL FLOW TRADING SYSTEM - CONFIGURATION SUMMARY")
        print("="*60)
        
        # API Key Status
        print("\n🔑 API KEY STATUS:")
        validation = self.validate_api_keys()
        for key, status in validation.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {key.upper().replace('_', ' ')}")
        
        # Trading Configuration
        print("\n📈 TRADING CONFIGURATION:")
        trading_config = self.get_trading_config()
        for key, value in trading_config.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        # System Status
        print("\n🖥️  SYSTEM STATUS:")
        print(f"  • Environment file loaded: {len(self._config_cache)} variables")
        print(f"  • MongoDB configured: {'✅' if self.is_configured('MONGODB_URL') else '❌'}")
        print(f"  • Polygon API configured: {'✅' if self.is_configured('POLYGON_API_KEY') else '❌'}")
        print(f"  • Alpaca API configured: {'✅' if self.is_configured('ALPACA_API_KEY') else '❌'}")
        
        print("\n" + "="*60)

# Create global instance
env_manager = EnvManager()

# Convenience functions for backward compatibility
def get_env(key: str, default: Any = None) -> Optional[str]:
    """Get environment variable"""
    return env_manager.get(key, default)

def get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    return env_manager.get_bool(key, default)

def get_int_env(key: str, default: int = 0) -> int:
    """Get integer environment variable"""
    return env_manager.get_int(key, default)

def get_float_env(key: str, default: float = 0.0) -> float:
    """Get float environment variable"""
    return env_manager.get_float(key, default)

def is_configured(key: str) -> bool:
    """Check if environment variable is configured"""
    return env_manager.is_configured(key)

# Export for easy importing
__all__ = [
    'env_manager', 
    'get_env', 
    'get_bool_env', 
    'get_int_env', 
    'get_float_env', 
    'is_configured'
]

if __name__ == "__main__":
    # Print configuration summary when run directly
    env_manager.print_config_summary()
