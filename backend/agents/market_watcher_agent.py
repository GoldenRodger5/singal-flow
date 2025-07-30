"""
Market Watcher Agent - Detects trading setups and patterns.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from services.data_provider import PolygonDataProvider
from services.indicators import TechnicalIndicators
from services.dynamic_screener import DynamicScreener
from services.config import Config


class MarketWatcherAgent:
    """Agent responsible for monitoring market and detecting trading setups."""
    
    def __init__(self):
        """Initialize the market watcher agent."""
        self.config = Config()
        self.screener = DynamicScreener()
        self.data_provider = None
        
    async def scan_for_setups(self) -> List[Dict[str, Any]]:
        """Scan the watchlist for trading setups."""
        logger.info("Starting market scan for trading setups")
        
        try:
            # Get current watchlist
            watchlist = self.screener.load_watchlist()
            
            if not watchlist:
                logger.warning("Empty watchlist, running screener first")
                await self.screener.update_watchlist()
                watchlist = self.screener.load_watchlist()
            
            if not watchlist:
                logger.error("Still no watchlist available")
                return []
            
            logger.info(f"Scanning {len(watchlist)} tickers for setups")
            
            # Analyze each ticker for setups
            setups = []
            async with PolygonDataProvider() as data_provider:
                self.data_provider = data_provider
                
                for ticker in watchlist:
                    try:
                        setup = await self._analyze_ticker_for_setup(ticker)
                        if setup and self._is_valid_setup(setup):
                            setups.append(setup)
                            logger.info(f"Valid setup found for {ticker} (score: {setup['setup_score']})")
                        
                        # Rate limiting
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        logger.error(f"Error analyzing {ticker}: {e}")
                        continue
            
            # Sort setups by score (best first)
            setups.sort(key=lambda x: x['setup_score'], reverse=True)
            
            logger.info(f"Found {len(setups)} valid trading setups")
            return setups[:5]  # Return top 5 setups
            
        except Exception as e:
            logger.error(f"Error in market scan: {e}")
            return []
    
    async def _analyze_ticker_for_setup(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Analyze a single ticker for trading setup."""
        try:
            # Get historical data for technical analysis
            df = await self.data_provider.get_technical_indicators_data(ticker, days_back=50)
            
            if df.empty:
                logger.warning(f"No data available for {ticker}")
                return None
            
            # Perform comprehensive technical analysis
            setup = TechnicalIndicators.analyze_ticker_setup(df, ticker)
            
            if not setup:
                return None
            
            # Add current market context
            market_context = await self._get_market_context(ticker)
            setup.update(market_context)
            
            # Calculate confidence score
            confidence = self._calculate_setup_confidence(setup)
            setup['confidence'] = confidence
            
            return setup
            
        except Exception as e:
            logger.error(f"Error analyzing setup for {ticker}: {e}")
            return None
    
    async def _get_market_context(self, ticker: str) -> Dict[str, Any]:
        """Get additional market context for the ticker."""
        try:
            context = {}
            
            # Get current market snapshot
            snapshot = await self.data_provider.get_market_snapshot(ticker)
            ticker_data = snapshot.get('ticker', {})
            
            if ticker_data:
                # Current trading session data
                day_data = ticker_data.get('day', {})
                context.update({
                    'day_open': day_data.get('o', 0),
                    'day_high': day_data.get('h', 0),
                    'day_low': day_data.get('l', 0),
                    'day_close': day_data.get('c', 0),
                    'day_volume': day_data.get('v', 0),
                    'day_change': day_data.get('c', 0),
                    'day_change_percent': day_data.get('c', 0) / day_data.get('o', 1) * 100 if day_data.get('o', 0) > 0 else 0
                })
            
            # Get recent news sentiment (basic)
            news = await self.data_provider.get_news(ticker, limit=3)
            context['recent_news_count'] = len(news)
            
            # Check if it's a volatile session
            context['is_volatile_session'] = self._check_volatility(context)
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting market context for {ticker}: {e}")
            return {}
    
    def _check_volatility(self, context: Dict[str, Any]) -> bool:
        """Check if the current session is volatile enough for trading."""
        day_high = context.get('day_high', 0)
        day_low = context.get('day_low', 0)
        day_open = context.get('day_open', 0)
        
        if day_open == 0:
            return False
        
        # Calculate intraday range as percentage of opening price
        intraday_range = ((day_high - day_low) / day_open) * 100
        
        # Consider volatile if intraday range > 3%
        return intraday_range > 3.0
    
    def _calculate_setup_confidence(self, setup: Dict[str, Any]) -> float:
        """Calculate confidence score for a trading setup."""
        try:
            base_score = setup.get('setup_score', 0)
            confidence = base_score * 10  # Convert to 0-100 scale
            
            # Adjust based on additional factors
            
            # Risk/Reward ratio impact
            rr_ratio = setup.get('risk_reward', {}).get('rr_ratio', 0)
            if rr_ratio >= 3.0:
                confidence += 10
            elif rr_ratio >= 2.5:
                confidence += 5
            
            # Volume confirmation
            volume_data = setup.get('volume_data', {})
            if volume_data.get('spike', False):
                confidence += 8
            
            # VWAP bounce quality
            vwap_data = setup.get('vwap', {})
            if vwap_data.get('is_bounce', False):
                confidence += 10
                
            # RSI oversold level
            rsi_data = setup.get('rsi', {})
            if rsi_data.get('is_oversold', False):
                rsi_value = rsi_data.get('rsi_value', 50)
                if rsi_value < 25:
                    confidence += 8
                elif rsi_value < 30:
                    confidence += 5
            
            # MACD confirmation
            macd_data = setup.get('macd', {})
            if macd_data.get('is_bullish_cross', False):
                confidence += 7
            
            # Market volatility bonus
            if setup.get('is_volatile_session', False):
                confidence += 5
            
            # Recent news activity
            news_count = setup.get('recent_news_count', 0)
            if news_count > 0:
                confidence += min(news_count * 2, 6)  # Cap at 6 points
            
            # Normalize to 0-10 scale
            confidence = min(confidence / 10, 10.0)
            
            return round(confidence, 1)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.0
    
    def _is_valid_setup(self, setup: Dict[str, Any]) -> bool:
        """Determine if a setup meets minimum criteria for trading."""
        try:
            # Minimum setup score
            if setup.get('setup_score', 0) < 3:
                return False
            
            # Minimum confidence
            if setup.get('confidence', 0) < self.config.MIN_CONFIDENCE_SCORE:
                return False
            
            # Minimum R:R ratio
            rr_ratio = setup.get('risk_reward', {}).get('rr_ratio', 0)
            if rr_ratio < self.config.RR_THRESHOLD:
                return False
            
            # Price range check
            current_price = setup.get('current_price', 0)
            if not (self.config.TICKER_PRICE_MIN <= current_price <= self.config.TICKER_PRICE_MAX):
                return False
            
            # Must have at least one strong signal
            strong_signals = 0
            
            if setup.get('vwap', {}).get('is_bounce', False):
                strong_signals += 1
            
            if setup.get('rsi', {}).get('is_oversold', False):
                strong_signals += 1
            
            if setup.get('macd', {}).get('is_bullish_cross', False):
                strong_signals += 1
            
            if strong_signals < 1:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating setup: {e}")
            return False
    
    async def monitor_active_setups(self, active_setups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Monitor active trading setups for updates."""
        updated_setups = []
        
        async with PolygonDataProvider() as data_provider:
            for setup in active_setups:
                try:
                    ticker = setup['ticker']
                    
                    # Get fresh data
                    df = await data_provider.get_technical_indicators_data(ticker, days_back=10)
                    
                    if df.empty:
                        continue
                    
                    # Update current price and indicators
                    current_price = df['close'].iloc[-1]
                    
                    # Check if setup is still valid
                    fresh_analysis = TechnicalIndicators.analyze_ticker_setup(df, ticker)
                    
                    if fresh_analysis:
                        fresh_analysis['original_timestamp'] = setup.get('timestamp')
                        fresh_analysis['confidence'] = self._calculate_setup_confidence(fresh_analysis)
                        
                        # Only keep if still meets criteria
                        if self._is_valid_setup(fresh_analysis):
                            updated_setups.append(fresh_analysis)
                    
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error monitoring setup for {setup.get('ticker', 'unknown')}: {e}")
                    continue
        
        return updated_setups
