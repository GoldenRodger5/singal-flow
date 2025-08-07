"""
Market Schedule Manager
Intelligent trading system operation based on market hours
"""

import asyncio
from datetime import datetime, time, timezone
from typing import Dict, Any, Optional
from loguru import logger
import os

class MarketScheduleManager:
    """Manages trading system operation based on market schedule."""
    
    def __init__(self):
        self.market_open_time = time(9, 30)  # 9:30 AM EST
        self.market_close_time = time(16, 0)  # 4:00 PM EST
        self.pre_market_start = time(4, 0)    # 4:00 AM EST
        self.after_hours_end = time(20, 0)    # 8:00 PM EST
        
        # Configuration
        self.enable_pre_market = os.getenv('ENABLE_PRE_MARKET', 'True').lower() == 'true'
        self.enable_post_market = os.getenv('ENABLE_POST_MARKET', 'True').lower() == 'true'
        self.weekend_data_refresh = os.getenv('WEEKEND_DATA_REFRESH', 'True').lower() == 'true'
        
        logger.info("Market Schedule Manager initialized")
    
    def get_market_session(self) -> Dict[str, Any]:
        """Get current market session information."""
        now = datetime.now()
        current_time = now.time()
        is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4
        
        session_info = {
            'timestamp': now,
            'is_weekday': is_weekday,
            'current_session': 'closed',
            'next_session': 'regular',
            'next_session_time': None,
            'real_time_data_available': False,
            'api_calls_recommended': False,
            'use_cached_data': True,
        }
        
        if not is_weekday:
            session_info.update({
                'current_session': 'weekend',
                'api_calls_recommended': self.weekend_data_refresh,
                'use_cached_data': not self.weekend_data_refresh,
            })
            return session_info
        
        # Determine current session
        if self.enable_pre_market and self.pre_market_start <= current_time < self.market_open_time:
            session_info.update({
                'current_session': 'pre_market',
                'real_time_data_available': True,
                'api_calls_recommended': True,
                'use_cached_data': False,
            })
        elif self.market_open_time <= current_time < self.market_close_time:
            session_info.update({
                'current_session': 'regular',
                'real_time_data_available': True,
                'api_calls_recommended': True,
                'use_cached_data': False,
            })
        elif self.enable_post_market and self.market_close_time <= current_time < self.after_hours_end:
            session_info.update({
                'current_session': 'after_hours',
                'real_time_data_available': True,
                'api_calls_recommended': True,
                'use_cached_data': False,
            })
        else:
            session_info.update({
                'current_session': 'closed',
                'api_calls_recommended': False,
                'use_cached_data': True,
            })
        
        return session_info
    
    def should_make_api_calls(self) -> bool:
        """Determine if API calls should be made right now."""
        session = self.get_market_session()
        return session['api_calls_recommended']
    
    def get_data_refresh_interval(self) -> int:
        """Get recommended data refresh interval in seconds."""
        session = self.get_market_session()
        
        intervals = {
            'regular': 30,      # 30 seconds during regular hours
            'pre_market': 60,   # 1 minute during pre-market
            'after_hours': 60,  # 1 minute during after-hours  
            'closed': 3600,     # 1 hour when closed
            'weekend': 14400,   # 4 hours on weekends
        }
        
        return intervals.get(session['current_session'], 3600)
    
    def get_recommended_operation_mode(self) -> str:
        """Get recommended system operation mode."""
        session = self.get_market_session()
        
        mode_mapping = {
            'regular': 'active_trading',
            'pre_market': 'monitoring',
            'after_hours': 'monitoring', 
            'closed': 'analysis_only',
            'weekend': 'maintenance'
        }
        
        return mode_mapping.get(session['current_session'], 'standby')

# Global instance
market_schedule = MarketScheduleManager()

# Export for easy importing
__all__ = ['market_schedule', 'MarketScheduleManager']
