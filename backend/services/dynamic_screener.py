"""
Dynamic stock screener for identifying potential trading candidates.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from services.data_provider import PolygonDataProvider
from services.config import Config

# Import optional momentum multiplier
try:
    from services.momentum_multiplier import MomentumMultiplier
    MOMENTUM_MULTIPLIER_AVAILABLE = True
except ImportError:
    logger.warning("Momentum multiplier not available - using basic momentum scoring")
    MOMENTUM_MULTIPLIER_AVAILABLE = False


class DynamicScreener:
    """Screen stocks based on price, volume, and momentum criteria."""
    
    def __init__(self):
        """Initialize the screener."""
        self.config = Config()
        self.watchlist_file = "data/watchlist_dynamic.json"
        
        # Initialize momentum multiplier if available
        if MOMENTUM_MULTIPLIER_AVAILABLE:
            self.momentum_multiplier = MomentumMultiplier()
            logger.info("Momentum multiplier enabled for enhanced screening")
        else:
            self.momentum_multiplier = None
        
    async def screen_by_price_range(self) -> List[str]:
        """Screen stocks within the specified price range."""
        logger.info(f"Screening stocks between ${self.config.TICKER_PRICE_MIN} and ${self.config.TICKER_PRICE_MAX}")
        
        async with PolygonDataProvider() as data_provider:
            # Get gainers first as they're more likely to be volatile
            gainers = await data_provider.get_gainers_losers("gainers")
            
            filtered_tickers = []
            
            for stock in gainers[:100]:  # Limit to top 100 gainers
                ticker = stock.get('ticker')
                price = stock.get('value', 0)
                volume = stock.get('session', {}).get('volume', 0)
                
                if not ticker or not self._meets_price_criteria(price):
                    continue
                    
                if not self._meets_volume_criteria(volume):
                    continue
                    
                filtered_tickers.append(ticker)
                
                if len(filtered_tickers) >= 50:  # Limit watchlist size
                    break
                    
        logger.info(f"Found {len(filtered_tickers)} tickers meeting criteria")
        return filtered_tickers
    
    async def screen_by_momentum(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Screen tickers for momentum characteristics."""
        logger.info(f"Analyzing momentum for {len(tickers)} tickers")
        
        momentum_stocks = []
        
        async with PolygonDataProvider() as data_provider:
            for ticker in tickers:
                try:
                    # Get market snapshot
                    snapshot = await data_provider.get_market_snapshot(ticker)
                    ticker_data = snapshot.get('ticker', {})
                    
                    if not ticker_data:
                        continue
                    
                    # Extract key metrics
                    day_data = ticker_data.get('day', {})
                    prev_day = ticker_data.get('prevDay', {})
                    last_quote = ticker_data.get('lastQuote', {})
                    
                    current_price = last_quote.get('P', 0)  # Current price
                    day_volume = day_data.get('v', 0)  # Today's volume
                    day_change = day_data.get('c', 0)  # Day's change
                    day_change_percent = (day_change / (current_price - day_change)) * 100 if current_price > day_change else 0
                    
                    prev_volume = prev_day.get('v', 0)  # Previous day volume
                    volume_ratio = day_volume / prev_volume if prev_volume > 0 else 0
                    
                    # Calculate momentum score
                    momentum_score = self._calculate_momentum_score(
                        day_change_percent, volume_ratio, current_price
                    )
                    
                    if momentum_score >= 5:  # Minimum momentum threshold
                        momentum_stocks.append({
                            'ticker': ticker,
                            'current_price': current_price,
                            'day_change_percent': day_change_percent,
                            'volume_ratio': volume_ratio,
                            'momentum_score': momentum_score,
                            'day_volume': day_volume
                        })
                        
                    # Rate limiting
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error analyzing momentum for {ticker}: {e}")
                    continue
        
        # Sort by momentum score
        momentum_stocks.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        logger.info(f"Found {len(momentum_stocks)} stocks with good momentum")
        return momentum_stocks[:20]  # Top 20 momentum stocks
    
    async def get_sector_diversity(self, tickers: List[str]) -> List[str]:
        """Ensure sector diversity in the watchlist."""
        sector_counts = {}
        diversified_tickers = []
        
        async with PolygonDataProvider() as data_provider:
            for ticker in tickers:
                try:
                    # Get ticker details for sector information
                    details = await data_provider.get_ticker_details(ticker)
                    
                    if not details or 'results' not in details:
                        continue
                        
                    sector = details['results'].get('sic_description', 'Unknown')
                    
                    # Limit tickers per sector to ensure diversity
                    if sector_counts.get(sector, 0) < 3:
                        diversified_tickers.append(ticker)
                        sector_counts[sector] = sector_counts.get(sector, 0) + 1
                    
                    await asyncio.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error getting sector for {ticker}: {e}")
                    continue
        
        return diversified_tickers
    
    def _meets_price_criteria(self, price: float) -> bool:
        """Check if price meets screening criteria."""
        return (self.config.TICKER_PRICE_MIN <= price <= self.config.TICKER_PRICE_MAX)
    
    def _meets_volume_criteria(self, volume: int) -> bool:
        """Check if volume meets minimum requirements."""
        return volume >= 100000  # Minimum 100k volume
    
    def _calculate_momentum_score(self, change_percent: float, 
                                 volume_ratio: float, price: float) -> float:
        """Calculate momentum score for a stock."""
        score = 0
        
        # Price change component (0-4 points)
        if change_percent > 5:
            score += 4
        elif change_percent > 3:
            score += 3
        elif change_percent > 1:
            score += 2
        elif change_percent > 0:
            score += 1
        
        # Volume component (0-3 points)
        if volume_ratio > 3:
            score += 3
        elif volume_ratio > 2:
            score += 2
        elif volume_ratio > 1.5:
            score += 1
        
        # Price range preference (0-2 points)
        if 5 <= price <= 30:
            score += 2
        elif 1 <= price <= 50:
            score += 1
        
        return score
    
    async def update_watchlist(self) -> None:
        """Update the dynamic watchlist with fresh screening results."""
        try:
            logger.info("Starting watchlist update process")
            
            # Step 1: Screen by price and volume
            price_filtered = await self.screen_by_price_range()
            
            if not price_filtered:
                logger.warning("No stocks found in price range")
                return
            
            # Step 2: Analyze momentum
            momentum_stocks = await self.screen_by_momentum(price_filtered)
            
            if not momentum_stocks:
                logger.warning("No stocks found with good momentum")
                return
            
            # Step 3: Extract tickers for sector diversity check
            momentum_tickers = [stock['ticker'] for stock in momentum_stocks]
            
            # Step 4: Ensure sector diversity
            diversified_tickers = await self.get_sector_diversity(momentum_tickers)
            
            # Step 5: Create final watchlist with metadata
            final_watchlist = []
            for stock in momentum_stocks:
                if stock['ticker'] in diversified_tickers:
                    final_watchlist.append(stock)
            
            # Step 6: Save to file
            watchlist_data = {
                'timestamp': datetime.now().isoformat(),
                'total_stocks': len(final_watchlist),
                'screening_criteria': {
                    'price_min': self.config.TICKER_PRICE_MIN,
                    'price_max': self.config.TICKER_PRICE_MAX,
                    'min_volume': 100000,
                    'min_momentum_score': 5
                },
                'stocks': final_watchlist
            }
            
            self._save_watchlist(watchlist_data)
            
            logger.info(f"Watchlist updated with {len(final_watchlist)} stocks")
            
        except Exception as e:
            logger.error(f"Error updating watchlist: {e}")
    
    def _save_watchlist(self, watchlist_data: Dict[str, Any]) -> None:
        """Save watchlist data to JSON file."""
        try:
            with open(self.watchlist_file, 'w') as f:
                json.dump(watchlist_data, f, indent=2)
            logger.info(f"Watchlist saved to {self.watchlist_file}")
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")
    
    def load_watchlist(self) -> List[str]:
        """Load the current watchlist."""
        try:
            with open(self.watchlist_file, 'r') as f:
                data = json.load(f)
                stocks = data.get('stocks', [])
                return [stock['ticker'] for stock in stocks]
        except FileNotFoundError:
            logger.warning("Watchlist file not found, returning empty list")
            return []
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            return []
    
    def get_watchlist_with_metadata(self) -> Dict[str, Any]:
        """Load the full watchlist with metadata."""
        try:
            with open(self.watchlist_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Watchlist file not found")
            return {'stocks': [], 'timestamp': None}
        except Exception as e:
            logger.error(f"Error loading watchlist metadata: {e}")
            return {'stocks': [], 'timestamp': None}
