"""
Short Squeeze Detection Engine
Identifies potential short squeeze opportunities for maximum profit
Based on Polygon.io Short Volume and Short Interest APIs
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
import os

@dataclass
class ShortSqueezeSignal:
    """Short squeeze opportunity signal."""
    symbol: str
    short_interest_ratio: float  # Days to cover
    short_volume_ratio: float    # Short volume / total volume
    price_momentum: float        # Recent price acceleration
    volume_spike: float          # Volume vs average
    squeeze_probability: float   # 0-100% probability
    risk_level: str              # 'LOW', 'MEDIUM', 'HIGH'
    entry_price: float
    target_price: float
    stop_loss: float
    timestamp: datetime

class ShortSqueezeDetector:
    """
    Detects short squeeze opportunities using Polygon.io APIs.
    Based on GameStop, AMC, and other successful squeeze patterns.
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        self.session = None
        
        # Short squeeze thresholds (based on historical successful squeezes)
        self.high_short_interest = 15.0    # >15% short interest
        self.high_days_to_cover = 5.0      # >5 days to cover
        self.high_short_volume = 40.0      # >40% daily short volume
        self.volume_spike_threshold = 3.0   # 3x average volume
        
        logger.info("💥 Short Squeeze Detector initialized")
        logger.info("🎯 Monitoring for high short interest + volume spikes")
    
    async def __aenter__(self):
        """Async context manager."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager cleanup."""
        if self.session:
            await self.session.close()
    
    async def scan_for_squeeze_opportunities(self, watchlist: List[str]) -> List[ShortSqueezeSignal]:
        """Scan watchlist for potential short squeeze opportunities."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        squeeze_signals = []
        
        for symbol in watchlist:
            try:
                signal = await self._analyze_squeeze_potential(symbol)
                if signal and signal.squeeze_probability > 60:
                    squeeze_signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error analyzing {symbol} for squeeze: {e}")
        
        # Sort by squeeze probability
        squeeze_signals.sort(key=lambda x: x.squeeze_probability, reverse=True)
        
        logger.info(f"🔍 Found {len(squeeze_signals)} potential squeeze opportunities")
        return squeeze_signals
    
    async def _analyze_squeeze_potential(self, symbol: str) -> Optional[ShortSqueezeSignal]:
        """Analyze individual stock for squeeze potential."""
        try:
            # Get short interest data
            short_interest_data = await self._get_short_interest(symbol)
            if not short_interest_data:
                return None
            
            # Get recent short volume data
            short_volume_data = await self._get_recent_short_volume(symbol)
            if not short_volume_data:
                return None
            
            # Get current price and volume data
            current_data = await self._get_current_market_data(symbol)
            if not current_data:
                return None
            
            # Calculate squeeze indicators
            days_to_cover = short_interest_data['days_to_cover']
            short_volume_ratio = short_volume_data['short_volume_ratio']
            volume_spike = current_data['volume_spike']
            price_momentum = current_data['price_momentum']
            
            # Calculate squeeze probability
            squeeze_probability = self._calculate_squeeze_probability(
                days_to_cover, short_volume_ratio, volume_spike, price_momentum
            )
            
            if squeeze_probability < 60:
                return None
            
            # Calculate risk level and targets
            risk_level = self._assess_risk_level(squeeze_probability, volume_spike)
            entry_price = current_data['current_price']
            target_price, stop_loss = self._calculate_targets(
                entry_price, squeeze_probability, price_momentum
            )
            
            return ShortSqueezeSignal(
                symbol=symbol,
                short_interest_ratio=days_to_cover,
                short_volume_ratio=short_volume_ratio,
                price_momentum=price_momentum,
                volume_spike=volume_spike,
                squeeze_probability=squeeze_probability,
                risk_level=risk_level,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing squeeze potential for {symbol}: {e}")
            return None
    
    async def _get_short_interest(self, symbol: str) -> Optional[Dict]:
        """Get latest short interest data."""
        try:
            url = f"{self.base_url}/v1/stocks/{symbol}/short_interest"
            params = {'apikey': self.api_key, 'limit': 1}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and data['results']:
                        result = data['results'][0]
                        return {
                            'short_interest': result.get('short_interest', 0),
                            'avg_daily_volume': result.get('avg_daily_volume', 1),
                            'days_to_cover': result.get('days_to_cover', 0)
                        }
                        
        except Exception as e:
            logger.error(f"Error getting short interest for {symbol}: {e}")
        
        return None
    
    async def _get_recent_short_volume(self, symbol: str, days: int = 5) -> Optional[Dict]:
        """Get recent short volume data."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f"{self.base_url}/v1/stocks/{symbol}/short_volume"
            params = {
                'apikey': self.api_key,
                'date.gte': start_date.strftime('%Y-%m-%d'),
                'date.lte': end_date.strftime('%Y-%m-%d'),
                'limit': days
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and data['results']:
                        total_short_volume = sum(r.get('short_volume', 0) for r in data['results'])
                        total_volume = sum(r.get('total_volume', 1) for r in data['results'])
                        
                        short_volume_ratio = (total_short_volume / total_volume * 100) if total_volume > 0 else 0
                        
                        return {
                            'short_volume_ratio': short_volume_ratio,
                            'avg_short_volume': total_short_volume / len(data['results'])
                        }
                        
        except Exception as e:
            logger.error(f"Error getting short volume for {symbol}: {e}")
        
        return None
    
    async def _get_current_market_data(self, symbol: str) -> Optional[Dict]:
        """Get current market data for analysis."""
        try:
            # Get current quote
            url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'ticker' in data and data['ticker']:
                        ticker_data = data['ticker']
                        
                        # Get price and volume info
                        last_trade = ticker_data.get('lastTrade', {})
                        day_data = ticker_data.get('day', {})
                        prev_day = ticker_data.get('prevDay', {})
                        
                        current_price = float(last_trade.get('p', 0))
                        current_volume = int(day_data.get('v', 0))
                        prev_volume = int(prev_day.get('v', 1))
                        
                        # Calculate metrics
                        volume_spike = current_volume / prev_volume if prev_volume > 0 else 1
                        price_change = ((current_price - float(prev_day.get('c', current_price))) / float(prev_day.get('c', current_price)) * 100) if prev_day.get('c', 0) > 0 else 0
                        
                        # Simple momentum calculation (can be enhanced)
                        price_momentum = abs(price_change)
                        
                        return {
                            'current_price': current_price,
                            'volume_spike': volume_spike,
                            'price_momentum': price_momentum,
                            'price_change': price_change
                        }
                        
        except Exception as e:
            logger.error(f"Error getting current data for {symbol}: {e}")
        
        return None
    
    def _calculate_squeeze_probability(self, days_to_cover: float, short_volume_ratio: float, 
                                     volume_spike: float, price_momentum: float) -> float:
        """Calculate probability of short squeeze."""
        score = 0
        
        # Days to cover component (0-30 points)
        if days_to_cover > 10:
            score += 30
        elif days_to_cover > 7:
            score += 25
        elif days_to_cover > 5:
            score += 20
        elif days_to_cover > 3:
            score += 15
        elif days_to_cover > 2:
            score += 10
        
        # Short volume ratio component (0-25 points)
        if short_volume_ratio > 50:
            score += 25
        elif short_volume_ratio > 40:
            score += 20
        elif short_volume_ratio > 30:
            score += 15
        elif short_volume_ratio > 20:
            score += 10
        
        # Volume spike component (0-25 points)
        if volume_spike > 5:
            score += 25
        elif volume_spike > 3:
            score += 20
        elif volume_spike > 2:
            score += 15
        elif volume_spike > 1.5:
            score += 10
        
        # Price momentum component (0-20 points)
        if price_momentum > 10:
            score += 20
        elif price_momentum > 5:
            score += 15
        elif price_momentum > 3:
            score += 10
        elif price_momentum > 1:
            score += 5
        
        return min(100, score)
    
    def _assess_risk_level(self, squeeze_probability: float, volume_spike: float) -> str:
        """Assess risk level of squeeze play."""
        if squeeze_probability > 85 and volume_spike > 3:
            return 'LOW'
        elif squeeze_probability > 70 and volume_spike > 2:
            return 'MEDIUM'
        else:
            return 'HIGH'
    
    def _calculate_targets(self, entry_price: float, squeeze_probability: float, 
                         price_momentum: float) -> Tuple[float, float]:
        """Calculate target and stop loss prices."""
        # Target based on squeeze probability and momentum
        target_multiplier = 1 + (squeeze_probability / 100 * 0.5) + (price_momentum / 100 * 0.3)
        target_price = entry_price * target_multiplier
        
        # Stop loss (conservative)
        stop_loss = entry_price * 0.92  # 8% stop loss
        
        return target_price, stop_loss
    
    async def monitor_active_squeezes(self, active_positions: List[str]) -> Dict[str, Dict]:
        """Monitor active squeeze positions."""
        updates = {}
        
        for symbol in active_positions:
            try:
                current_data = await self._get_current_market_data(symbol)
                if current_data:
                    updates[symbol] = {
                        'current_price': current_data['current_price'],
                        'volume_spike': current_data['volume_spike'],
                        'price_momentum': current_data['price_momentum'],
                        'timestamp': datetime.now()
                    }
                    
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
        
        return updates

# Global instance - will be created when needed
squeeze_detector = None

def get_squeeze_detector():
    """Get or create the squeeze detector instance."""
    global squeeze_detector
    if squeeze_detector is None:
        squeeze_detector = ShortSqueezeDetector()
    return squeeze_detector

# Export
__all__ = ['get_squeeze_detector', 'squeeze_detector', 'ShortSqueezeDetector', 'ShortSqueezeSignal']
