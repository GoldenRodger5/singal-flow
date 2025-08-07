"""
Anomaly Detection Engine for Day Trading
Based on Polygon.io tutorial best practices
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from services.polygon_flat_files import flat_files_manager
from services.real_time_market_data import get_market_data_service

@dataclass
class TradingAnomaly:
    """Detected trading anomaly."""
    symbol: str
    anomaly_type: str  # 'volume_spike', 'price_breakout', 'unusual_trading'
    severity: float  # Z-score or confidence level
    timestamp: datetime
    current_price: float
    volume_ratio: float  # Current vs average
    price_change_pct: float
    confidence: float
    trade_signal: str  # 'BUY', 'SELL', 'WATCH'

class AnomalyDetectionEngine:
    """
    Real-time anomaly detection for profitable day trading.
    Based on Polygon.io research on market anomaly detection.
    """
    
    def __init__(self):
        self.lookback_days = 5  # Rolling baseline period
        self.volume_threshold = 3.0  # 3+ standard deviations
        self.price_threshold = 2.5   # 2.5+ standard deviations
        self.baseline_cache = {}
        self.active_anomalies = {}
        
        logger.info("🔍 Anomaly Detection Engine initialized")
        logger.info("📊 Monitoring for volume spikes, price breakouts, unusual patterns")
    
    async def detect_anomalies(self, watchlist: List[str]) -> List[TradingAnomaly]:
        """Detect real-time anomalies across watchlist."""
        anomalies = []
        
        # Get real-time market data
        market_data_service = get_market_data_service()
        current_quotes = await market_data_service.get_multiple_quotes(watchlist)
        
        for symbol in watchlist:
            if symbol not in current_quotes:
                continue
            
            quote = current_quotes[symbol]
            
            try:
                # Get baseline statistics
                baseline = await self._get_baseline_stats(symbol)
                if not baseline:
                    continue
                
                # Check for volume anomalies (most profitable signal)
                volume_anomaly = self._detect_volume_anomaly(quote, baseline)
                if volume_anomaly:
                    anomalies.append(volume_anomaly)
                
                # Check for price breakout anomalies
                price_anomaly = self._detect_price_anomaly(quote, baseline)
                if price_anomaly:
                    anomalies.append(price_anomaly)
                
                # Check for combined anomalies (highest confidence)
                combined_anomaly = self._detect_combined_anomaly(quote, baseline)
                if combined_anomaly:
                    anomalies.append(combined_anomaly)
                    
            except Exception as e:
                logger.error(f"Error detecting anomalies for {symbol}: {e}")
        
        # Sort by confidence/severity
        anomalies.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"🎯 Detected {len(anomalies)} trading anomalies")
        return anomalies
    
    async def _get_baseline_stats(self, symbol: str) -> Optional[Dict]:
        """Get baseline trading statistics for anomaly detection."""
        cache_key = f"{symbol}_baseline"
        
        # Check cache (refresh hourly)
        if cache_key in self.baseline_cache:
            cached_data = self.baseline_cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).total_seconds() < 3600:
                return cached_data['data']
        
        try:
            # Get historical data from flat files (more comprehensive)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            historical_data = await flat_files_manager.get_bulk_historical_data(
                symbols=[symbol],
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                data_type='day_aggs_v1'
            )
            
            if historical_data.empty:
                return None
            
            # Calculate baseline statistics
            baseline = {
                'avg_volume': historical_data['volume'].mean(),
                'std_volume': historical_data['volume'].std(),
                'avg_range': (historical_data['high'] - historical_data['low']).mean(),
                'std_range': (historical_data['high'] - historical_data['low']).std(),
                'avg_price': historical_data['close'].mean(),
                'price_volatility': historical_data['close'].std(),
                'typical_change': historical_data['close'].pct_change().std() * 100
            }
            
            # Cache for 1 hour
            self.baseline_cache[cache_key] = {
                'data': baseline,
                'timestamp': datetime.now()
            }
            
            return baseline
            
        except Exception as e:
            logger.error(f"Error calculating baseline for {symbol}: {e}")
            return None
    
    def _detect_volume_anomaly(self, quote, baseline) -> Optional[TradingAnomaly]:
        """Detect unusual volume spikes (most profitable signal)."""
        if not baseline or baseline['std_volume'] == 0:
            return None
        
        # Calculate volume Z-score
        volume_z_score = (quote.volume - baseline['avg_volume']) / baseline['std_volume']
        
        if volume_z_score > self.volume_threshold:
            # High volume spike - potential breakout
            trade_signal = 'BUY' if quote.change_percent > 0 else 'WATCH'
            confidence = min(95, 60 + (volume_z_score - 3) * 10)
            
            return TradingAnomaly(
                symbol=quote.symbol,
                anomaly_type='volume_spike',
                severity=volume_z_score,
                timestamp=datetime.now(),
                current_price=quote.price,
                volume_ratio=quote.volume / baseline['avg_volume'],
                price_change_pct=quote.change_percent,
                confidence=confidence,
                trade_signal=trade_signal
            )
        
        return None
    
    def _detect_price_anomaly(self, quote, baseline) -> Optional[TradingAnomaly]:
        """Detect unusual price movements."""
        if not baseline or baseline['price_volatility'] == 0:
            return None
        
        # Calculate price movement Z-score
        price_z_score = abs(quote.change_percent) / baseline['typical_change']
        
        if price_z_score > self.price_threshold:
            # Significant price movement
            trade_signal = 'BUY' if quote.change_percent > 0 else 'SELL'
            confidence = min(90, 50 + (price_z_score - 2.5) * 15)
            
            return TradingAnomaly(
                symbol=quote.symbol,
                anomaly_type='price_breakout',
                severity=price_z_score,
                timestamp=datetime.now(),
                current_price=quote.price,
                volume_ratio=quote.volume / baseline['avg_volume'] if baseline['avg_volume'] > 0 else 1,
                price_change_pct=quote.change_percent,
                confidence=confidence,
                trade_signal=trade_signal
            )
        
        return None
    
    def _detect_combined_anomaly(self, quote, baseline) -> Optional[TradingAnomaly]:
        """Detect combined volume + price anomalies (highest confidence)."""
        if not baseline:
            return None
        
        # Volume component
        volume_z = (quote.volume - baseline['avg_volume']) / baseline['std_volume'] if baseline['std_volume'] > 0 else 0
        
        # Price component
        price_z = abs(quote.change_percent) / baseline['typical_change'] if baseline['typical_change'] > 0 else 0
        
        # Combined score (weighted)
        combined_score = (volume_z * 0.6) + (price_z * 0.4)
        
        if combined_score > 4.0 and volume_z > 2.0 and price_z > 1.5:
            # Strong combined signal - highest profit potential
            trade_signal = 'BUY' if quote.change_percent > 0 else 'SELL'
            confidence = min(98, 70 + (combined_score - 4) * 8)
            
            return TradingAnomaly(
                symbol=quote.symbol,
                anomaly_type='combined_breakout',
                severity=combined_score,
                timestamp=datetime.now(),
                current_price=quote.price,
                volume_ratio=quote.volume / baseline['avg_volume'] if baseline['avg_volume'] > 0 else 1,
                price_change_pct=quote.change_percent,
                confidence=confidence,
                trade_signal=trade_signal
            )
        
        return None
    
    async def get_profit_targets(self, anomaly: TradingAnomaly) -> Dict[str, float]:
        """Calculate profit targets based on anomaly characteristics."""
        try:
            # Get recent volatility for target calculation
            market_data_service = get_market_data_service()
            historical_data = await market_data_service.get_historical_data(
                anomaly.symbol, days=10
            )
            
            if not historical_data:
                # Default targets
                return {
                    'stop_loss': anomaly.current_price * 0.98,  # 2% stop loss
                    'target_1': anomaly.current_price * 1.03,   # 3% target
                    'target_2': anomaly.current_price * 1.06    # 6% target
                }
            
            # Calculate Average True Range (ATR) for dynamic targets
            df = pd.DataFrame(historical_data)
            df['high'] = df['high']
            df['low'] = df['low']
            df['close'] = df['close']
            
            # Simple ATR calculation
            high_low = df['high'] - df['low']
            atr = high_low.rolling(window=5).mean().iloc[-1]
            atr_percent = (atr / anomaly.current_price) * 100
            
            # Dynamic targets based on volatility and confidence
            volatility_multiplier = max(1.5, atr_percent / 2)
            confidence_multiplier = anomaly.confidence / 100
            
            return {
                'stop_loss': anomaly.current_price * (1 - (atr_percent * 0.8) / 100),
                'target_1': anomaly.current_price * (1 + (volatility_multiplier * confidence_multiplier) / 100),
                'target_2': anomaly.current_price * (1 + (volatility_multiplier * confidence_multiplier * 1.8) / 100)
            }
            
        except Exception as e:
            logger.error(f"Error calculating profit targets for {anomaly.symbol}: {e}")
            return {
                'stop_loss': anomaly.current_price * 0.98,
                'target_1': anomaly.current_price * 1.03,
                'target_2': anomaly.current_price * 1.06
            }

# Global instance - will be created when needed
anomaly_engine = None

def get_anomaly_engine():
    """Get or create the anomaly engine instance."""
    global anomaly_engine
    if anomaly_engine is None:
        anomaly_engine = AnomalyDetectionEngine()
    return anomaly_engine

# Export
__all__ = ['get_anomaly_engine', 'anomaly_engine', 'AnomalyDetectionEngine', 'TradingAnomaly']
