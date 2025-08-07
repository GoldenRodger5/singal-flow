"""
Market Pulse Service (NO SENTIMENT ANALYSIS)
Provides real-time market overview and technical analysis
Focus on price action, volume, and technical indicators only
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from loguru import logger
from dataclasses import dataclass

from services.real_time_market_data import market_data_service
from services.database_manager import db_manager

@dataclass
class MarketPulseData:
    """Market pulse data structure."""
    market_trend: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    market_volatility: str  # 'LOW', 'MEDIUM', 'HIGH'
    volume_profile: str  # 'HEAVY', 'NORMAL', 'LIGHT'
    key_levels: Dict[str, float]
    active_sectors: List[str]
    market_breadth: Dict[str, int]
    volatility_index: float
    momentum_score: float
    timestamp: datetime

class MarketPulseService:
    """Market pulse service providing technical market overview."""
    
    def __init__(self):
        """Initialize market pulse service."""
        self.major_indices = ['SPY', 'QQQ', 'IWM', 'DIA']
        self.sector_etfs = {
            'Technology': 'XLK',
            'Healthcare': 'XLV', 
            'Financials': 'XLF',
            'Energy': 'XLE',
            'Consumer Discretionary': 'XLY',
            'Consumer Staples': 'XLP',
            'Industrials': 'XLI',
            'Materials': 'XLB',
            'Utilities': 'XLU',
            'Real Estate': 'XLRE'
        }
        self.volatility_symbols = ['VIX', 'UVXY', 'SVXY']
        
        logger.info("Market Pulse Service initialized (technical analysis only)")
    
    async def get_market_pulse(self) -> MarketPulseData:
        """Get comprehensive market pulse data."""
        try:
            # Get market data for all symbols
            all_symbols = (self.major_indices + 
                         list(self.sector_etfs.values()) + 
                         self.volatility_symbols)
            
            async with market_data_service:
                market_data = await market_data_service.get_multiple_quotes(all_symbols)
                market_status = await market_data_service.get_market_status()
            
            # Analyze market components
            market_trend = await self._analyze_market_trend(market_data)
            market_volatility = await self._analyze_market_volatility(market_data)
            volume_profile = await self._analyze_volume_profile(market_data)
            key_levels = await self._calculate_key_levels(market_data)
            active_sectors = await self._identify_active_sectors(market_data)
            market_breadth = await self._calculate_market_breadth()
            volatility_index = self._get_volatility_index(market_data)
            momentum_score = await self._calculate_momentum_score(market_data)
            
            pulse_data = MarketPulseData(
                market_trend=market_trend,
                market_volatility=market_volatility,
                volume_profile=volume_profile,
                key_levels=key_levels,
                active_sectors=active_sectors,
                market_breadth=market_breadth,
                volatility_index=volatility_index,
                momentum_score=momentum_score,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Store pulse data for historical tracking
            await self._store_pulse_data(pulse_data)
            
            logger.debug("Generated market pulse data")
            return pulse_data
            
        except Exception as e:
            logger.error(f"Error generating market pulse: {e}")
            return self._get_default_pulse_data()
    
    async def _analyze_market_trend(self, market_data: Dict) -> str:
        """Analyze overall market trend based on major indices."""
        try:
            bullish_count = 0
            bearish_count = 0
            
            for symbol in self.major_indices:
                if symbol in market_data:
                    data = market_data[symbol]
                    change_percent = data.change_percent
                    
                    # Simple trend analysis based on daily change
                    if change_percent > 0.5:
                        bullish_count += 1
                    elif change_percent < -0.5:
                        bearish_count += 1
                    
                    # Volume confirmation
                    if hasattr(data, 'volume') and data.volume > 0:
                        # High volume strengthens the signal
                        if change_percent > 1.0:
                            bullish_count += 0.5
                        elif change_percent < -1.0:
                            bearish_count += 0.5
            
            if bullish_count > bearish_count + 0.5:
                return 'BULLISH'
            elif bearish_count > bullish_count + 0.5:
                return 'BEARISH'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"Error analyzing market trend: {e}")
            return 'NEUTRAL'
    
    async def _analyze_market_volatility(self, market_data: Dict) -> str:
        """Analyze market volatility level."""
        try:
            # Check VIX if available
            if 'VIX' in market_data:
                vix_price = market_data['VIX'].price
                
                if vix_price > 25:
                    return 'HIGH'
                elif vix_price > 15:
                    return 'MEDIUM'
                else:
                    return 'LOW'
            
            # Fallback: analyze volatility from major indices
            total_volatility = 0
            count = 0
            
            for symbol in self.major_indices:
                if symbol in market_data:
                    data = market_data[symbol]
                    daily_range = abs(data.day_high - data.day_low) / data.price * 100
                    total_volatility += daily_range
                    count += 1
            
            if count > 0:
                avg_volatility = total_volatility / count
                
                if avg_volatility > 3.0:
                    return 'HIGH'
                elif avg_volatility > 1.5:
                    return 'MEDIUM'
                else:
                    return 'LOW'
            
            return 'MEDIUM'
            
        except Exception as e:
            logger.error(f"Error analyzing market volatility: {e}")
            return 'MEDIUM'
    
    async def _analyze_volume_profile(self, market_data: Dict) -> str:
        """Analyze volume profile across major indices."""
        try:
            # Get historical volume averages for comparison
            volume_ratios = []
            
            for symbol in self.major_indices:
                if symbol in market_data:
                    current_volume = market_data[symbol].volume
                    
                    # Get historical average volume
                    async with market_data_service:
                        historical_data = await market_data_service.get_historical_data(symbol, days=20)
                    
                    if historical_data and len(historical_data) > 10:
                        avg_volume = sum(day['volume'] for day in historical_data) / len(historical_data)
                        
                        if avg_volume > 0:
                            volume_ratio = current_volume / avg_volume
                            volume_ratios.append(volume_ratio)
            
            if volume_ratios:
                avg_ratio = sum(volume_ratios) / len(volume_ratios)
                
                if avg_ratio > 1.5:
                    return 'HEAVY'
                elif avg_ratio > 0.8:
                    return 'NORMAL'
                else:
                    return 'LIGHT'
            
            return 'NORMAL'
            
        except Exception as e:
            logger.error(f"Error analyzing volume profile: {e}")
            return 'NORMAL'
    
    async def _calculate_key_levels(self, market_data: Dict) -> Dict[str, float]:
        """Calculate key support and resistance levels."""
        try:
            key_levels = {}
            
            # Focus on SPY as main market indicator
            if 'SPY' in market_data:
                spy_data = market_data['SPY']
                current_price = spy_data.price
                
                # Get historical data for level calculation
                async with market_data_service:
                    historical_data = await market_data_service.get_historical_data('SPY', days=30)
                
                if historical_data:
                    highs = [day['high'] for day in historical_data]
                    lows = [day['low'] for day in historical_data]
                    
                    # Calculate support and resistance
                    resistance_1 = max(highs[-10:]) if len(highs) >= 10 else current_price * 1.02
                    support_1 = min(lows[-10:]) if len(lows) >= 10 else current_price * 0.98
                    
                    resistance_2 = max(highs) if highs else current_price * 1.05
                    support_2 = min(lows) if lows else current_price * 0.95
                    
                    key_levels = {
                        'SPY_price': round(current_price, 2),
                        'resistance_1': round(resistance_1, 2),
                        'support_1': round(support_1, 2),
                        'resistance_2': round(resistance_2, 2),
                        'support_2': round(support_2, 2),
                        'daily_high': round(spy_data.day_high, 2),
                        'daily_low': round(spy_data.day_low, 2)
                    }
            
            return key_levels
            
        except Exception as e:
            logger.error(f"Error calculating key levels: {e}")
            return {}
    
    async def _identify_active_sectors(self, market_data: Dict) -> List[str]:
        """Identify most active sectors based on performance."""
        try:
            sector_performance = []
            
            for sector_name, etf_symbol in self.sector_etfs.items():
                if etf_symbol in market_data:
                    data = market_data[etf_symbol]
                    
                    # Calculate activity score based on change and volume
                    change_score = abs(data.change_percent)
                    
                    # Volume score (relative to price)
                    volume_score = data.volume / 1000000 if data.volume > 0 else 0  # Volume in millions
                    
                    activity_score = change_score + (volume_score * 0.1)
                    
                    sector_performance.append({
                        'sector': sector_name,
                        'score': activity_score,
                        'change': data.change_percent
                    })
            
            # Sort by activity score
            sector_performance.sort(key=lambda x: x['score'], reverse=True)
            
            # Return top 3 most active sectors
            active_sectors = [s['sector'] for s in sector_performance[:3]]
            
            logger.debug(f"Most active sectors: {active_sectors}")
            return active_sectors
            
        except Exception as e:
            logger.error(f"Error identifying active sectors: {e}")
            return []
    
    async def _calculate_market_breadth(self) -> Dict[str, int]:
        """Calculate market breadth indicators."""
        try:
            # Analyze major indices performance
            advancing = 0
            declining = 0
            unchanged = 0
            
            for symbol in self.major_indices:
                if symbol in await self._get_current_market_data():
                    data = (await self._get_current_market_data())[symbol]
                    
                    if data.change_percent > 0.1:
                        advancing += 1
                    elif data.change_percent < -0.1:
                        declining += 1
                    else:
                        unchanged += 1
            
            # Add sector analysis
            sector_data = await self._get_current_market_data()
            sector_advancing = 0
            sector_declining = 0
            
            for etf_symbol in self.sector_etfs.values():
                if etf_symbol in sector_data:
                    data = sector_data[etf_symbol]
                    
                    if data.change_percent > 0:
                        sector_advancing += 1
                    else:
                        sector_declining += 1
            
            return {
                'indices_advancing': advancing,
                'indices_declining': declining,
                'indices_unchanged': unchanged,
                'sectors_advancing': sector_advancing,
                'sectors_declining': sector_declining,
                'breadth_ratio': round(advancing / (advancing + declining), 2) if (advancing + declining) > 0 else 0.5
            }
            
        except Exception as e:
            logger.error(f"Error calculating market breadth: {e}")
            return {
                'indices_advancing': 0,
                'indices_declining': 0,
                'indices_unchanged': 0,
                'sectors_advancing': 0,
                'sectors_declining': 0,
                'breadth_ratio': 0.5
            }
    
    def _get_volatility_index(self, market_data: Dict) -> float:
        """Get current volatility index value."""
        try:
            if 'VIX' in market_data:
                return round(market_data['VIX'].price, 2)
            
            # Fallback calculation using SPY
            if 'SPY' in market_data:
                spy_data = market_data['SPY']
                daily_range = abs(spy_data.day_high - spy_data.day_low) / spy_data.price
                
                # Convert to VIX-like scale (rough approximation)
                estimated_vix = daily_range * 100 * 16  # Rough scaling factor
                return round(min(estimated_vix, 100), 2)  # Cap at 100
            
            return 20.0  # Default moderate volatility
            
        except Exception as e:
            logger.error(f"Error getting volatility index: {e}")
            return 20.0
    
    async def _calculate_momentum_score(self, market_data: Dict) -> float:
        """Calculate overall market momentum score."""
        try:
            momentum_scores = []
            
            for symbol in self.major_indices:
                if symbol in market_data:
                    data = market_data[symbol]
                    
                    # Price momentum (current vs open)
                    price_momentum = (data.price - data.day_open) / data.day_open * 100 if data.day_open > 0 else 0
                    
                    # Daily change momentum
                    change_momentum = data.change_percent
                    
                    # Combined momentum score
                    symbol_momentum = (price_momentum + change_momentum) / 2
                    momentum_scores.append(symbol_momentum)
            
            if momentum_scores:
                overall_momentum = sum(momentum_scores) / len(momentum_scores)
                
                # Normalize to -100 to +100 scale
                normalized_momentum = max(-100, min(100, overall_momentum * 10))
                
                return round(normalized_momentum, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return 0.0
    
    async def _get_current_market_data(self) -> Dict:
        """Get current market data for all tracked symbols."""
        try:
            all_symbols = (self.major_indices + 
                         list(self.sector_etfs.values()) + 
                         self.volatility_symbols)
            
            async with market_data_service:
                return await market_data_service.get_multiple_quotes(all_symbols)
        except Exception as e:
            logger.error(f"Error getting current market data: {e}")
            return {}
    
    async def _store_pulse_data(self, pulse_data: MarketPulseData):
        """Store market pulse data for historical tracking."""
        try:
            pulse_doc = {
                'market_trend': pulse_data.market_trend,
                'market_volatility': pulse_data.market_volatility,
                'volume_profile': pulse_data.volume_profile,
                'key_levels': pulse_data.key_levels,
                'active_sectors': pulse_data.active_sectors,
                'market_breadth': pulse_data.market_breadth,
                'volatility_index': pulse_data.volatility_index,
                'momentum_score': pulse_data.momentum_score,
                'timestamp': pulse_data.timestamp
            }
            
            await db_manager.store_market_pulse(pulse_doc)
            logger.debug("Stored market pulse data to database")
            
        except Exception as e:
            logger.error(f"Error storing pulse data: {e}")
    
    def _get_default_pulse_data(self) -> MarketPulseData:
        """Return default market pulse data."""
        return MarketPulseData(
            market_trend='NEUTRAL',
            market_volatility='MEDIUM',
            volume_profile='NORMAL',
            key_levels={},
            active_sectors=[],
            market_breadth={
                'indices_advancing': 0,
                'indices_declining': 0,
                'indices_unchanged': 0,
                'sectors_advancing': 0,
                'sectors_declining': 0,
                'breadth_ratio': 0.5
            },
            volatility_index=20.0,
            momentum_score=0.0,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def get_historical_pulse(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical market pulse data."""
        try:
            historical_data = await db_manager.get_historical_market_pulse(days)
            
            formatted_data = []
            for entry in historical_data:
                formatted_data.append({
                    'date': entry.get('timestamp', datetime.now()).date().isoformat(),
                    'trend': entry.get('market_trend', 'NEUTRAL'),
                    'volatility': entry.get('market_volatility', 'MEDIUM'),
                    'volume': entry.get('volume_profile', 'NORMAL'),
                    'vix': entry.get('volatility_index', 20.0),
                    'momentum': entry.get('momentum_score', 0.0),
                    'breadth_ratio': entry.get('market_breadth', {}).get('breadth_ratio', 0.5)
                })
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error getting historical pulse data: {e}")
            return []

# Global instance
market_pulse_service = MarketPulseService()

# Export for easy importing
__all__ = ['market_pulse_service', 'MarketPulseService', 'MarketPulseData']
