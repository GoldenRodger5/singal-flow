"""
Market data provider using Polygon API.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from services.config import Config


class PolygonDataProvider:
    """Polygon.io API client for market data."""
    
    def __init__(self):
        """Initialize the data provider."""
        self.api_key = Config.POLYGON_API_KEY
        self.base_url = "https://api.polygon.io"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make an authenticated request to Polygon API."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        if params is None:
            params = {}
            
        params['apikey'] = self.api_key
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"API request failed: {response.status} - {await response.text()}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error making API request to {endpoint}: {e}")
            return {}
    
    async def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """Get detailed information about a ticker."""
        endpoint = f"/v3/reference/tickers/{ticker}"
        return await self._make_request(endpoint)
    
    async def get_market_snapshot(self, ticker: str) -> Dict[str, Any]:
        """Get current market snapshot for a ticker."""
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        return await self._make_request(endpoint)
    
    async def get_previous_close(self, ticker: str) -> Dict[str, Any]:
        """Get previous close data for a ticker."""
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"
        return await self._make_request(endpoint)
    
    async def get_aggregates(self, ticker: str, timespan: str = "minute", 
                           multiplier: int = 1, from_date: str = None, 
                           to_date: str = None) -> Dict[str, Any]:
        """Get aggregate bars for a ticker."""
        if not from_date:
            from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
            
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        return await self._make_request(endpoint)
    
    async def get_gainers_losers(self, direction: str = "gainers") -> List[Dict[str, Any]]:
        """Get market gainers or losers."""
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/{direction}"
        data = await self._make_request(endpoint)
        return data.get('results', [])
    
    async def search_tickers(self, query: str = "", market: str = "stocks", 
                           active: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for tickers matching criteria."""
        params = {
            "market": market,
            "active": str(active).lower(),
            "limit": limit
        }
        
        if query:
            params["search"] = query
            
        endpoint = "/v3/reference/tickers"
        data = await self._make_request(endpoint, params)
        return data.get('results', [])
    
    async def get_news(self, ticker: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest news articles."""
        params = {"limit": limit}
        
        if ticker:
            params["ticker"] = ticker
            
        endpoint = "/v2/reference/news"
        data = await self._make_request(endpoint, params)
        return data.get('results', [])
    
    async def get_real_time_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote for a ticker."""
        endpoint = f"/v1/last_quote/stocks/{ticker}"
        return await self._make_request(endpoint)
    
    async def filter_tickers_by_price_range(self, min_price: float = None, 
                                          max_price: float = None) -> List[str]:
        """Filter tickers by price range."""
        try:
            # Get all active stocks
            tickers_data = await self.search_tickers(market="stocks", active=True, limit=1000)
            
            filtered_tickers = []
            
            for ticker_info in tickers_data:
                ticker = ticker_info.get('ticker')
                if not ticker:
                    continue
                    
                # Get current price
                snapshot = await self.get_market_snapshot(ticker)
                ticker_data = snapshot.get('ticker', {})
                last_quote = ticker_data.get('lastQuote', {})
                price = last_quote.get('p')  # Last price
                
                if price and self._is_price_in_range(price, min_price, max_price):
                    filtered_tickers.append(ticker)
                    
                # Rate limiting - small delay between requests
                await asyncio.sleep(0.1)
                
            return filtered_tickers
            
        except Exception as e:
            logger.error(f"Error filtering tickers by price: {e}")
            return []
    
    def _is_price_in_range(self, price: float, min_price: float = None, 
                          max_price: float = None) -> bool:
        """Check if price is within specified range."""
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False
        return True
    
    async def get_technical_indicators_data(self, ticker: str, 
                                          days_back: int = 50) -> pd.DataFrame:
        """Get historical data suitable for technical analysis."""
        try:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            
            # Get minute-level data for intraday analysis
            data = await self.get_aggregates(ticker, "minute", 1, from_date, to_date)
            
            if not data.get('results'):
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data['results'])
            
            # Rename columns to standard format
            df.rename(columns={
                't': 'timestamp',
                'o': 'open',
                'h': 'high', 
                'l': 'low',
                'c': 'close',
                'v': 'volume'
            }, inplace=True)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting technical data for {ticker}: {e}")
            return pd.DataFrame()
