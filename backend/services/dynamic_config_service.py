"""
Dynamic Configuration Service
Real-time configuration updates that integrate with trading agents and AI systems
"""

import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DynamicConfigService:
    """Service for real-time configuration updates across the trading system."""
    
    def __init__(self):
        self.config_file = Path("data/dynamic_config.json")
        self.config_lock = threading.Lock()
        self.listeners = []
        self.current_config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
            
        # Return default configuration
        return {
            "confidence_settings": {
                "min_confidence_score": 6.0,
                "paper_trading_min_confidence": 5.5,
                "auto_execute_threshold": 9.5
            },
            "position_settings": {
                "base_position_size_percent": 0.25,
                "max_position_size_percent": 0.50,
                "position_size_multiplier": 1.0
            },
            "technical_settings": {
                "williams_r_oversold": -80,
                "williams_r_overbought": -20,
                "volume_spike_multiplier": 3.0,
                "momentum_multiplier_min": 5
            },
            "risk_settings": {
                "max_daily_loss_percent": 0.15,
                "max_portfolio_risk_percent": 0.60,
                "stop_loss_percent": 0.05
            },
            "trading_settings": {
                "paper_trading": True,
                "max_daily_trades": 100,
                "ticker_price_min": 0.75,
                "ticker_price_max": 10.0
            },
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def _save_config(self):
        """Save current configuration to file."""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            self.current_config["last_updated"] = datetime.now().isoformat()
            
            with open(self.config_file, 'w') as f:
                json.dump(self.current_config, f, indent=2)
                
            logger.info("Dynamic configuration saved")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """Update a specific configuration value."""
        try:
            with self.config_lock:
                if section not in self.current_config:
                    self.current_config[section] = {}
                    
                old_value = self.current_config[section].get(key)
                self.current_config[section][key] = value
                
                self._save_config()
                self._notify_listeners(section, key, old_value, value)
                
                logger.info(f"Config updated: {section}.{key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating config {section}.{key}: {e}")
            return False
    
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        try:
            with self.config_lock:
                return self.current_config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        try:
            with self.config_lock:
                return self.current_config.get(section, {}).copy()
        except Exception:
            return {}
    
    def register_listener(self, callback):
        """Register a callback for configuration changes."""
        self.listeners.append(callback)
    
    def _notify_listeners(self, section: str, key: str, old_value: Any, new_value: Any):
        """Notify all registered listeners of configuration changes."""
        for listener in self.listeners:
            try:
                listener(section, key, old_value, new_value)
            except Exception as e:
                logger.error(f"Error notifying config listener: {e}")
    
    def update_from_ui_session(self, session_state) -> bool:
        """Update configuration from Streamlit session state."""
        try:
            updates = []
            
            # Confidence settings
            if hasattr(session_state, 'confidence_threshold'):
                updates.append(('confidence_settings', 'min_confidence_score', session_state.confidence_threshold))
                updates.append(('confidence_settings', 'paper_trading_min_confidence', session_state.confidence_threshold - 0.5))
            
            if hasattr(session_state, 'auto_execute_threshold'):
                updates.append(('confidence_settings', 'auto_execute_threshold', session_state.auto_execute_threshold))
            
            # Position settings
            if hasattr(session_state, 'position_multiplier'):
                updates.append(('position_settings', 'position_size_multiplier', session_state.position_multiplier))
            
            # Technical settings
            if hasattr(session_state, 'williams_r_oversold'):
                updates.append(('technical_settings', 'williams_r_oversold', session_state.williams_r_oversold))
            
            if hasattr(session_state, 'volume_multiplier'):
                updates.append(('technical_settings', 'volume_spike_multiplier', session_state.volume_multiplier))
            
            if hasattr(session_state, 'momentum_min'):
                updates.append(('technical_settings', 'momentum_multiplier_min', session_state.momentum_min))
            
            # Risk settings
            if hasattr(session_state, 'max_daily_risk'):
                updates.append(('risk_settings', 'max_daily_loss_percent', session_state.max_daily_risk / 100))
            
            # Trading settings
            if hasattr(session_state, 'paper_trading'):
                updates.append(('trading_settings', 'paper_trading', session_state.paper_trading))
            
            # Apply all updates
            for section, key, value in updates:
                self.update_config(section, key, value)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating config from UI: {e}")
            return False
    
    def apply_to_static_config(self):
        """Apply dynamic config to static Config class."""
        try:
            from services.config import Config
            
            # Update confidence settings
            conf_settings = self.get_section('confidence_settings')
            if conf_settings:
                Config.MIN_CONFIDENCE_SCORE = conf_settings.get('min_confidence_score', Config.MIN_CONFIDENCE_SCORE)
                Config.PAPER_TRADING_MIN_CONFIDENCE = conf_settings.get('paper_trading_min_confidence', Config.PAPER_TRADING_MIN_CONFIDENCE)
            
            # Update position settings
            pos_settings = self.get_section('position_settings')
            if pos_settings:
                Config.POSITION_SIZE_PERCENT = pos_settings.get('base_position_size_percent', Config.POSITION_SIZE_PERCENT)
                Config.MAX_POSITION_SIZE_PERCENT = pos_settings.get('max_position_size_percent', Config.MAX_POSITION_SIZE_PERCENT)
                
                # Add multiplier if it doesn't exist
                if not hasattr(Config, 'POSITION_SIZE_MULTIPLIER'):
                    Config.POSITION_SIZE_MULTIPLIER = pos_settings.get('position_size_multiplier', 1.0)
                else:
                    Config.POSITION_SIZE_MULTIPLIER = pos_settings.get('position_size_multiplier', Config.POSITION_SIZE_MULTIPLIER)
            
            # Update technical settings
            tech_settings = self.get_section('technical_settings')
            if tech_settings:
                Config.WILLIAMS_R_OVERSOLD = tech_settings.get('williams_r_oversold', Config.WILLIAMS_R_OVERSOLD)
                Config.WILLIAMS_R_OVERBOUGHT = tech_settings.get('williams_r_overbought', Config.WILLIAMS_R_OVERBOUGHT)
                Config.VOLUME_SPIKE_MULTIPLIER = tech_settings.get('volume_spike_multiplier', Config.VOLUME_SPIKE_MULTIPLIER)
            
            # Update risk settings
            risk_settings = self.get_section('risk_settings')
            if risk_settings:
                Config.MAX_DAILY_LOSS_PCT = risk_settings.get('max_daily_loss_percent', Config.MAX_DAILY_LOSS_PCT)
            
            # Update trading settings
            trading_settings = self.get_section('trading_settings')
            if trading_settings:
                Config.PAPER_TRADING = trading_settings.get('paper_trading', Config.PAPER_TRADING)
                Config.TICKER_PRICE_MIN = trading_settings.get('ticker_price_min', Config.TICKER_PRICE_MIN)
                Config.TICKER_PRICE_MAX = trading_settings.get('ticker_price_max', Config.TICKER_PRICE_MAX)
            
            logger.info("Dynamic config applied to static Config class")
            return True
            
        except Exception as e:
            logger.error(f"Error applying config to static Config: {e}")
            return False


# Global instance
dynamic_config = DynamicConfigService()


def setup_config_integration():
    """Setup integration with trading agents and AI systems."""
    try:
        # Register listeners for real-time updates
        dynamic_config.register_listener(_on_config_change)
        
        # Apply current config to static Config
        dynamic_config.apply_to_static_config()
        
        logger.info("Dynamic configuration integration setup complete")
        
    except Exception as e:
        logger.error(f"Error setting up config integration: {e}")


def _on_config_change(section: str, key: str, old_value: Any, new_value: Any):
    """Handle configuration changes."""
    try:
        logger.info(f"Config change: {section}.{key} changed from {old_value} to {new_value}")
        
        # Apply changes to static config immediately
        dynamic_config.apply_to_static_config()
        
        # Notify specific components of changes
        if section == 'confidence_settings':
            _notify_trade_agents_confidence_change(key, new_value)
        elif section == 'technical_settings':
            _notify_indicators_change(key, new_value)
        elif section == 'position_settings':
            _notify_position_sizer_change(key, new_value)
        
    except Exception as e:
        logger.error(f"Error handling config change: {e}")


def _notify_trade_agents_confidence_change(key: str, value: Any):
    """Notify trade agents of confidence threshold changes."""
    try:
        # This would integrate with your trade recommender agent
        logger.info(f"Notifying trade agents of confidence change: {key} = {value}")
    except Exception as e:
        logger.error(f"Error notifying trade agents: {e}")


def _notify_indicators_change(key: str, value: Any):
    """Notify technical indicators of parameter changes."""
    try:
        # This would integrate with your Williams %R and momentum multiplier services
        logger.info(f"Notifying indicators of change: {key} = {value}")
    except Exception as e:
        logger.error(f"Error notifying indicators: {e}")


def _notify_position_sizer_change(key: str, value: Any):
    """Notify position sizer of parameter changes."""
    try:
        # This would integrate with your enhanced position sizer
        logger.info(f"Notifying position sizer of change: {key} = {value}")
    except Exception as e:
        logger.error(f"Error notifying position sizer: {e}")
