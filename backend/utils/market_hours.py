"""
Market Hours Utility - US Stock Market Trading Hours
Handles NYSE/NASDAQ trading hours (9:30 AM - 4:00 PM EST, weekdays only)
"""
from datetime import datetime, time
import pytz
from typing import Optional, Tuple

class MarketHours:
    """Utility class for US stock market trading hours."""
    
    def __init__(self):
        """Initialize with US Eastern timezone."""
        self.est = pytz.timezone('US/Eastern')
        self.market_open = time(9, 30)    # 9:30 AM EST
        self.market_close = time(16, 0)   # 4:00 PM EST
        self.pre_market = time(4, 0)      # 4:00 AM EST
        self.after_hours_end = time(20, 0) # 8:00 PM EST
    
    def get_current_est_time(self) -> datetime:
        """Get current time in Eastern timezone."""
        return datetime.now(self.est)
    
    def is_market_day(self, dt: Optional[datetime] = None) -> bool:
        """Check if given date is a market day (Monday-Friday, excluding holidays)."""
        if dt is None:
            dt = self.get_current_est_time()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if dt.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # TODO: Add holiday checking for NYSE/NASDAQ holidays
        # For now, just check weekdays
        return True
    
    def is_market_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is during market hours (9:30 AM - 4:00 PM EST)."""
        if dt is None:
            dt = self.get_current_est_time()
        
        # Must be a market day
        if not self.is_market_day(dt):
            return False
        
        current_time = dt.time()
        return self.market_open <= current_time < self.market_close
    
    def is_pre_market(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is during pre-market hours (4:00 AM - 9:30 AM EST)."""
        if dt is None:
            dt = self.get_current_est_time()
        
        if not self.is_market_day(dt):
            return False
        
        current_time = dt.time()
        return self.pre_market <= current_time < self.market_open
    
    def is_after_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is during after-hours trading (4:00 PM - 8:00 PM EST)."""
        if dt is None:
            dt = self.get_current_est_time()
        
        if not self.is_market_day(dt):
            return False
        
        current_time = dt.time()
        return self.market_close <= current_time < self.after_hours_end
    
    def is_extended_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is during extended hours (pre-market + after-hours)."""
        return self.is_pre_market(dt) or self.is_after_hours(dt)
    
    def is_market_closed(self, dt: Optional[datetime] = None) -> bool:
        """Check if market is completely closed (weekends, nights, holidays)."""
        if dt is None:
            dt = self.get_current_est_time()
        
        if not self.is_market_day(dt):
            return True
        
        current_time = dt.time()
        return current_time < self.pre_market or current_time >= self.after_hours_end
    
    def get_market_status(self, dt: Optional[datetime] = None) -> str:
        """Get current market status as string."""
        if dt is None:
            dt = self.get_current_est_time()
        
        if self.is_market_hours(dt):
            return "MARKET_OPEN"
        elif self.is_pre_market(dt):
            return "PRE_MARKET"
        elif self.is_after_hours(dt):
            return "AFTER_HOURS" 
        elif not self.is_market_day(dt):
            return "WEEKEND"
        else:
            return "MARKET_CLOSED"
    
    def time_until_market_open(self, dt: Optional[datetime] = None) -> Optional[int]:
        """Get minutes until market opens. Returns None if market is open."""
        if dt is None:
            dt = self.get_current_est_time()
        
        if self.is_market_hours(dt):
            return None  # Market is already open
        
        # Find next market open
        current_date = dt.date()
        market_open_today = self.est.localize(
            datetime.combine(current_date, self.market_open)
        )
        
        # If market hasn't opened today and it's a market day
        if dt < market_open_today and self.is_market_day(dt):
            minutes_until = int((market_open_today - dt).total_seconds() / 60)
            return minutes_until
        
        # Find next market day
        next_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for _ in range(7):  # Look up to 7 days ahead
            next_day = next_day.replace(day=next_day.day + 1)
            if self.is_market_day(next_day):
                next_market_open = self.est.localize(
                    datetime.combine(next_day.date(), self.market_open)
                )
                minutes_until = int((next_market_open - dt).total_seconds() / 60)
                return minutes_until
        
        return None  # Shouldn't happen
    
    def time_until_market_close(self, dt: Optional[datetime] = None) -> Optional[int]:
        """Get minutes until market closes. Returns None if market is closed."""
        if dt is None:
            dt = self.get_current_est_time()
        
        if not self.is_market_hours(dt):
            return None  # Market is already closed
        
        current_date = dt.date()
        market_close_today = self.est.localize(
            datetime.combine(current_date, self.market_close)
        )
        
        minutes_until = int((market_close_today - dt).total_seconds() / 60)
        return minutes_until
    
    def get_next_market_session(self, dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """Get the next market session (open, close) times."""
        if dt is None:
            dt = self.get_current_est_time()
        
        # If market is currently open, return today's session
        if self.is_market_hours(dt):
            current_date = dt.date()
            market_open_today = self.est.localize(
                datetime.combine(current_date, self.market_open)
            )
            market_close_today = self.est.localize(
                datetime.combine(current_date, self.market_close)
            )
            return market_open_today, market_close_today
        
        # Find next market day
        next_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for _ in range(7):  # Look up to 7 days ahead
            if self.is_market_day(next_day):
                # If it's today and market hasn't opened yet
                if next_day.date() == dt.date():
                    current_time = dt.time()
                    if current_time < self.market_open:
                        market_open = self.est.localize(
                            datetime.combine(next_day.date(), self.market_open)
                        )
                        market_close = self.est.localize(
                            datetime.combine(next_day.date(), self.market_close)
                        )
                        return market_open, market_close
                # Otherwise it's a future day
                elif next_day.date() > dt.date():
                    market_open = self.est.localize(
                        datetime.combine(next_day.date(), self.market_open)
                    )
                    market_close = self.est.localize(
                        datetime.combine(next_day.date(), self.market_close)
                    )
                    return market_open, market_close
            
            next_day = next_day.replace(day=next_day.day + 1)
        
        # Fallback (shouldn't happen)
        return dt, dt

# Global instance
market_hours = MarketHours()

def format_time_until(minutes: int) -> str:
    """Format minutes into human-readable time."""
    if minutes < 60:
        return f"{minutes} minutes"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours == 1:
        if remaining_minutes == 0:
            return "1 hour"
        else:
            return f"1 hour {remaining_minutes} minutes"
    else:
        if remaining_minutes == 0:
            return f"{hours} hours"
        else:
            return f"{hours} hours {remaining_minutes} minutes"
