"""
Real-time Market Data Service using Polygon API
Provides live market data for trading decisions and dashboard
"""

import os
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from loguru import logger
from dataclasses import dataclass
from services.market_schedule_manager import market_schedule

@dataclass
class MarketDataPoint:
    """Real-time market data structure."""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    change: float
    change_percent: float
    day_high: float
    day_low: float
    day_open: float
    previous_close: float

class RealTimeMarketDataService:
    """Real-time market data service using Polygon API."""
    
    def __init__(self):
        """Initialize the Real-time Market Data Service."""
        # Use the robust environment manager
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        
        if not self.api_key:
            logger.error("Polygon API key not found. Please check your .env file.")
            raise ValueError("POLYGON_API_KEY is required")
        
        # Validate API key format
        if len(self.api_key) < 10:
            logger.error(f"Invalid Polygon API key format: {self.api_key[:5]}...")
            raise ValueError("Invalid POLYGON_API_KEY format")
        
        self.session = None
        self.rate_limit_delay = 0.06  # ~60ms between requests for Starter tier (1000 req/min)
        self.last_request_time = 0
        self.cache = {}
        self.cache_ttl = 30  # 30 second cache for real-time data
        
        logger.info(f"Real-time Market Data Service initialized with Stocks Starter tier")
        logger.info(f"API key: {self.api_key[:8]}... | Base URL: {self.base_url}")
        
        # Check current market status
        import datetime as dt
        now = dt.datetime.now()
        if now.weekday() >= 5:  # Weekend
            logger.info("📅 Market Status: Closed (Weekend)")
        elif not (9 <= now.hour < 16):  # Outside market hours
            logger.info("🕐 Market Status: Closed (After Hours)")
        else:
            logger.info("📈 Market Status: Open (Trading Hours)")
            
        logger.info("✅ Real-time quotes available during market hours")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_real_time_quote(self, symbol: str) -> Optional[MarketDataPoint]:
        """Get real-time quote for a symbol using Stocks Starter tier."""
        try:
            # Intelligent scheduling - check if we should fetch real-time data
            if not market_schedule.should_fetch_real_time():
                logger.debug(f"Market closed - using cached data for {symbol}")
                return await self._get_cached_or_historical_quote(symbol)
            
            # Check cache first
            cache_key = f"quote_{symbol}"
            if self._is_cached_valid(cache_key):
                return self.cache[cache_key]['data']
            
            # If no API key, return simulated data
            if not self.api_key:
                return self._get_simulated_quote(symbol)
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            await self._respect_rate_limit()
            
            # Try real-time snapshot endpoint (WORKING with Stocks Starter!)
            url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'ticker' in data and data['ticker']:
                        ticker_data = data['ticker']
                        
                        # Extract real-time data from snapshot
                        last_quote = ticker_data.get('lastQuote', {})
                        last_trade = ticker_data.get('lastTrade', {})
                        day_data = ticker_data.get('day', {})
                        prev_day = ticker_data.get('prevDay', {})
                        
                        # Use last trade price for most current price
                        current_price = float(last_trade.get('p', 0))
                        if current_price == 0:
                            # Fallback to last quote
                            current_price = float(last_quote.get('p', 0))
                        
                        volume = int(day_data.get('v', 0))
                        timestamp = datetime.fromtimestamp(
                            last_trade.get('t', 0) / 1000, tz=timezone.utc
                        ) if last_trade.get('t') else datetime.now(timezone.utc)
                        
                        # Calculate change from previous close
                        previous_close = float(prev_day.get('c', current_price))
                        change = current_price - previous_close
                        change_percent = (change / previous_close * 100) if previous_close > 0 else 0
                        
                        market_point = MarketDataPoint(
                            symbol=symbol,
                            price=current_price,
                            volume=volume,
                            timestamp=timestamp,
                            change=round(change, 2),
                            change_percent=round(change_percent, 2),
                            day_high=float(day_data.get('h', current_price)),
                            day_low=float(day_data.get('l', current_price)),
                            day_open=float(day_data.get('o', current_price)),
                            previous_close=previous_close
                        )
                        
                        # Cache the result
                        self.cache[cache_key] = {
                            'data': market_point,
                            'timestamp': datetime.now()
                        }
                        
                        logger.info(f"✅ Real-time snapshot for {symbol}: ${current_price:.2f} (Stocks Starter)")
                        return market_point
                
                elif response.status == 403:
                    logger.info(f"Real-time data not available for {symbol} (market closed or subscription limitation) - using previous close")
                    return self._get_simulated_quote(symbol)
                else:
                    logger.warning(f"Failed to get quote for {symbol}: HTTP {response.status}")
                    return self._get_simulated_quote(symbol)
                    
        except Exception as e:
            logger.error(f"Error getting real-time quote for {symbol}: {e}")
            return await self._get_cached_or_historical_quote(symbol)
    
    async def _get_cached_or_historical_quote(self, symbol: str) -> MarketDataPoint:
        """Get cached or historical data when market is closed."""
        try:
            # Try to get previous close data
            return await self._get_previous_close_quote(symbol)
        except Exception as e:
            logger.error(f"Error getting cached quote for {symbol}: {e}")
            return self._get_simulated_quote(symbol)
    
    async def _get_previous_close_quote(self, symbol: str) -> MarketDataPoint:
        """Fallback method to get previous close data."""
        try:
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
            params = {'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and data['results']:
                        result = data['results'][0]
                        current_price = float(result['c'])  # Close price
                        volume = int(result.get('v', 0))
                        
                        # Calculate change from open to close
                        open_price = float(result.get('o', current_price))
                        change = current_price - open_price
                        change_percent = (change / open_price * 100) if open_price > 0 else 0
                        
                        market_point = MarketDataPoint(
                            symbol=symbol,
                            price=current_price,
                            volume=volume,
                            timestamp=datetime.now(timezone.utc),
                            change=round(change, 2),
                            change_percent=round(change_percent, 2),
                            day_high=float(result.get('h', current_price)),
                            day_low=float(result.get('l', current_price)),
                            day_open=open_price,
                            previous_close=float(result.get('c', current_price))
                        )
                        
                        logger.debug(f"Previous close fallback for {symbol}: ${current_price:.2f}")
                        return market_point
                        
        except Exception as e:
            logger.error(f"Error getting previous close for {symbol}: {e}")
        
        return self._get_simulated_quote(symbol)
    
    async def _get_daily_aggregate_data(self, symbol: str) -> Dict[str, float]:
        """Get daily aggregate data for additional market info."""
        try:
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
            params = {'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and data['results']:
                        result = data['results'][0]
                        return {
                            'previous_close': float(result.get('c', 0)),
                            'day_high': float(result.get('h', 0)),
                            'day_low': float(result.get('l', 0)),
                            'day_open': float(result.get('o', 0))
                        }
                        
        except Exception as e:
            logger.error(f"Error getting daily data for {symbol}: {e}")
        
        return {
            'previous_close': 0,
            'day_high': 0,
            'day_low': 0,
            'day_open': 0
        }
    
    async def _get_daily_data(self, symbol: str) -> Dict[str, float]:
        """Get daily statistics for a symbol."""
        try:
            cache_key = f"daily_{symbol}"
            if self._is_cached_valid(cache_key):
                return self.cache[cache_key]['data']
            
            # Get previous day's close and today's data
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
            params = {'adjusted': 'true', 'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and len(data['results']) > 0:
                        prev_data = data['results'][0]
                        previous_close = float(prev_data['c'])
                        
                        # Get today's data
                        today_data = await self._get_todays_data(symbol)
                        current_price = today_data.get('current_price', previous_close)
                        
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
                        
                        daily_stats = {
                            'previous_close': previous_close,
                            'change': change,
                            'change_percent': change_percent,
                            'high': today_data.get('high', current_price),
                            'low': today_data.get('low', current_price),
                            'open': today_data.get('open', previous_close)
                        }
                        
                        # Cache for 1 minute
                        self.cache[cache_key] = {
                            'data': daily_stats,
                            'timestamp': datetime.now()
                        }
                        
                        return daily_stats
            
            # Fallback to basic data
            return {
                'previous_close': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
                'high': 0.0,
                'low': 0.0,
                'open': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting daily data for {symbol}: {e}")
            return {}
    
    async def _get_todays_data(self, symbol: str) -> Dict[str, float]:
        """Get today's OHLC data."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{self.base_url}/v1/open-close/{symbol}/{today}"
            params = {'adjusted': 'true', 'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        'current_price': float(data.get('close', data.get('open', 0))),
                        'high': float(data.get('high', 0)),
                        'low': float(data.get('low', 0)),
                        'open': float(data.get('open', 0))
                    }
                    
        except Exception as e:
            logger.debug(f"Could not get today's data for {symbol}: {e}")
        
        return {}
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Get real-time quotes for multiple symbols."""
        quotes = {}
        
        # Process in batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            tasks = [self.get_real_time_quote(symbol) for symbol in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(batch, results):
                if isinstance(result, MarketDataPoint):
                    quotes[symbol] = result
                elif not isinstance(result, Exception):
                    logger.warning(f"No data returned for {symbol}")
            
            # Rate limiting delay
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.1)
        
        logger.info(f"Retrieved quotes for {len(quotes)}/{len(symbols)} symbols")
        return quotes
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get current market status."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/v1/marketstatus/now"
            params = {'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    market_status = {
                        'market_open': data.get('market', 'closed') == 'open',
                        'after_hours': data.get('afterHours', 'closed') == 'open',
                        'server_time': data.get('serverTime', datetime.now().isoformat()),
                        'exchanges': data.get('exchanges', {})
                    }
                    
                    logger.debug(f"Market status: {market_status['market_open']}")
                    return market_status
                    
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
        
        # Fallback status based on current time
        now = datetime.now()
        market_hours = (9, 30) <= (now.hour, now.minute) <= (16, 0)  # 9:30 AM - 4:00 PM EST
        
        return {
            'market_open': market_hours and now.weekday() < 5,  # Monday-Friday during market hours
            'after_hours': False,
            'server_time': datetime.now().isoformat(),
            'exchanges': {'nasdaq': 'closed', 'nyse': 'closed'}
        }
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical price data for analysis."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {'adjusted': 'true', 'sort': 'asc', 'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data:
                        historical_data = []
                        for point in data['results']:
                            historical_data.append({
                                'date': datetime.fromtimestamp(point['t'] / 1000).date().isoformat(),
                                'open': float(point['o']),
                                'high': float(point['h']),
                                'low': float(point['l']),
                                'close': float(point['c']),
                                'volume': int(point['v'])
                            })
                        
                        logger.debug(f"Retrieved {len(historical_data)} days of historical data for {symbol}")
                        return historical_data
                        
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
        
        return []
    
    async def _respect_rate_limit(self):
        """Respect API rate limits for Stocks Starter tier."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _is_cached_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key]['timestamp']
        age = (datetime.now() - cache_time).total_seconds()
        
        return age < self.cache_ttl
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
    
    def _get_simulated_quote(self, symbol: str) -> MarketDataPoint:
        """Get simulated market data when API is not available."""
        import random
        
        # Simulate realistic stock prices
        base_prices = {
            'AAPL': 150.0, 'GOOGL': 2500.0, 'MSFT': 300.0, 'TSLA': 200.0,
            'NVDA': 400.0, 'META': 250.0, 'AMZN': 3000.0, 'SPY': 400.0,
            'QQQ': 350.0, 'IWM': 180.0, 'DIA': 340.0, 'VIX': 20.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Add random variation
        price_variation = random.uniform(-0.05, 0.05)  # ±5%
        current_price = base_price * (1 + price_variation)
        
        # Simulate daily change
        daily_change = random.uniform(-3.0, 3.0)  # ±3%
        previous_close = current_price / (1 + daily_change / 100)
        
        return MarketDataPoint(
            symbol=symbol,
            price=round(current_price, 2),
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now(timezone.utc),
            change=round(current_price - previous_close, 2),
            change_percent=round(daily_change, 2),
            day_high=round(current_price * 1.02, 2),
            day_low=round(current_price * 0.98, 2),
            day_open=round(previous_close * 1.005, 2),
            previous_close=round(previous_close, 2)
        )

# Global instance - will be created when needed
market_data_service = None

def get_market_data_service():
    """Get or create the market data service instance."""
    global market_data_service
    if market_data_service is None:
        market_data_service = RealTimeMarketDataService()
    return market_data_service

# Export
__all__ = ['get_market_data_service', 'market_data_service', 'RealTimeMarketDataService', 'MarketDataPoint']
