"""
Market Regime Detection Service for Signal Flow Trading System.
Identifies market states (trending vs mean-reverting, high vs low volatility)
to enable regime-aware trading strategies.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime types."""
    TRENDING_HIGH_VOL = "trending_high_vol"
    TRENDING_LOW_VOL = "trending_low_vol"
    MEAN_REVERTING_HIGH_VOL = "mean_reverting_high_vol"
    MEAN_REVERTING_LOW_VOL = "mean_reverting_low_vol"
    UNCERTAIN = "uncertain"

@dataclass
class RegimeData:
    """Market regime data structure."""
    regime: MarketRegime
    confidence: float
    volatility_percentile: float
    trend_strength: float
    mean_reversion_strength: float
    timestamp: datetime
    adaptive_thresholds: Dict[str, float]

class MarketRegimeDetector:
    """Detects and tracks market regimes for adaptive trading."""
    
    def __init__(self, config):
        self.config = config
        self.lookback_days = config.VOLATILITY_LOOKBACK_DAYS
        self.trend_period = config.TREND_DETECTION_PERIOD
        self.regime_cache_file = "data/market_regime_cache.json"
        self.current_regime = None
        self.regime_history = []
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Load cached regime data
        self._load_regime_cache()
    
    def detect_market_regime(self, price_data: pd.DataFrame, 
                           volume_data: pd.DataFrame = None) -> RegimeData:
        """
        Detect current market regime based on price and volume data.
        
        Args:
            price_data: DataFrame with OHLCV data
            volume_data: Optional volume data for enhanced analysis
            
        Returns:
            RegimeData object with regime classification and adaptive parameters
        """
        try:
            # Calculate volatility metrics
            volatility_metrics = self._calculate_volatility_metrics(price_data)
            
            # Calculate trend metrics
            trend_metrics = self._calculate_trend_metrics(price_data)
            
            # Calculate mean reversion metrics
            mean_reversion_metrics = self._calculate_mean_reversion_metrics(price_data)
            
            # Determine regime
            regime = self._classify_regime(volatility_metrics, trend_metrics, mean_reversion_metrics)
            
            # Calculate adaptive thresholds
            adaptive_thresholds = self._calculate_adaptive_thresholds(regime, volatility_metrics)
            
            regime_data = RegimeData(
                regime=regime,
                confidence=self._calculate_regime_confidence(volatility_metrics, trend_metrics, mean_reversion_metrics),
                volatility_percentile=volatility_metrics['percentile'],
                trend_strength=trend_metrics['strength'],
                mean_reversion_strength=mean_reversion_metrics['strength'],
                timestamp=datetime.now(),
                adaptive_thresholds=adaptive_thresholds
            )
            
            # Update cache
            self.current_regime = regime_data
            self.regime_history.append(regime_data)
            self._save_regime_cache()
            
            logger.info(f"Market regime detected: {regime.value} (confidence: {regime_data.confidence:.2f})")
            
            return regime_data
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return self._get_default_regime()
    
    def _calculate_volatility_metrics(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volatility-based metrics."""
        returns = price_data['close'].pct_change().dropna()
        
        # Current volatility (20-day rolling)
        current_vol = returns.rolling(window=20).std() * np.sqrt(252)
        latest_vol = current_vol.iloc[-1]
        
        # Historical volatility percentile
        historical_vol = returns.rolling(window=self.lookback_days).std() * np.sqrt(252)
        vol_percentile = (historical_vol <= latest_vol).sum() / len(historical_vol)
        
        # GARCH-like volatility clustering
        vol_clustering = self._calculate_volatility_clustering(returns)
        
        return {
            'current': latest_vol,
            'percentile': vol_percentile,
            'clustering': vol_clustering,
            'is_high': vol_percentile > 0.7,
            'is_low': vol_percentile < 0.3
        }
    
    def _calculate_trend_metrics(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate trend strength metrics."""
        close_prices = price_data['close']
        
        # Moving average trend
        ma_short = close_prices.rolling(window=20).mean()
        ma_long = close_prices.rolling(window=50).mean()
        ma_trend = (ma_short.iloc[-1] - ma_long.iloc[-1]) / ma_long.iloc[-1]
        
        # ADX-like trend strength
        high_prices = price_data['high']
        low_prices = price_data['low']
        
        # Ensure we have enough data for calculations
        if len(close_prices) < 30:  # Need enough data for ADX calculation
            return {
                'ma_trend': 0.0,
                'strength': 0.0,
                'is_trending': False,
                'direction': 0
            }
        
        tr = pd.DataFrame({
            'hl': high_prices - low_prices,
            'hc': abs(high_prices - close_prices.shift(1)),
            'lc': abs(low_prices - close_prices.shift(1))
        }).max(axis=1)
        
        dm_plus = (high_prices - high_prices.shift(1)).where(
            (high_prices - high_prices.shift(1)) > (low_prices.shift(1) - low_prices), 0
        ).where((high_prices - high_prices.shift(1)) > 0, 0)
        
        dm_minus = (low_prices.shift(1) - low_prices).where(
            (low_prices.shift(1) - low_prices) > (high_prices - high_prices.shift(1)), 0
        ).where((low_prices.shift(1) - low_prices) > 0, 0)
        
        # Ensure all series have the same index
        tr = tr.dropna()
        dm_plus = dm_plus.dropna()
        dm_minus = dm_minus.dropna()
        
        # Align indices
        common_index = tr.index.intersection(dm_plus.index).intersection(dm_minus.index)
        tr = tr.loc[common_index]
        dm_plus = dm_plus.loc[common_index]
        dm_minus = dm_minus.loc[common_index]
        
        
        atr = tr.rolling(window=14).mean()
        di_plus = 100 * (dm_plus.rolling(window=14).mean() / atr)
        di_minus = 100 * (dm_minus.rolling(window=14).mean() / atr)
        
        # Calculate ADX with division by zero protection
        di_sum = di_plus + di_minus
        adx = 100 * abs(di_plus - di_minus) / di_sum.replace(0, np.nan)
        adx = adx.fillna(0)  # Fill NaN values with 0
        
        # Get trend strength, ensuring we have enough data
        if len(adx) >= 14:
            trend_strength = adx.rolling(window=14).mean().iloc[-1]
        else:
            trend_strength = adx.mean() if len(adx) > 0 else 0
        
        return {
            'ma_trend': ma_trend,
            'strength': trend_strength / 100.0,  # Normalize to 0-1
            'is_trending': trend_strength > 25,
            'direction': 1 if ma_trend > 0 else -1
        }
    
    def _calculate_mean_reversion_metrics(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate mean reversion strength metrics."""
        close_prices = price_data['close']
        returns = close_prices.pct_change().dropna()
        
        # Hurst exponent for mean reversion
        hurst = self._calculate_hurst_exponent(returns)
        
        # Bollinger Band position
        bb_period = 20
        bb_std = 2
        bb_ma = close_prices.rolling(window=bb_period).mean()
        bb_std_dev = close_prices.rolling(window=bb_period).std()
        bb_upper = bb_ma + (bb_std_dev * bb_std)
        bb_lower = bb_ma - (bb_std_dev * bb_std)
        bb_position = (close_prices.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
        
        # Mean reversion strength (inverse of Hurst)
        mr_strength = 1.0 - hurst if hurst is not None else 0.5
        
        return {
            'hurst': hurst,
            'strength': mr_strength,
            'bb_position': bb_position,
            'is_mean_reverting': hurst < 0.5 if hurst is not None else False
        }
    
    def _calculate_hurst_exponent(self, returns: pd.Series) -> Optional[float]:
        """Calculate Hurst exponent for mean reversion detection."""
        try:
            if len(returns) < 50:
                return None
                
            # Use simplified Hurst calculation
            lags = range(2, min(20, len(returns) // 4))
            tau = []
            
            for lag in lags:
                # Calculate variance of lagged differences
                lagged_returns = returns.iloc[lag:]
                original_returns = returns.iloc[:-lag]
                variance = np.var(lagged_returns.values - original_returns.values)
                tau.append(variance)
            
            # Fit line to log-log plot
            log_lags = np.log(lags)
            log_tau = np.log(tau)
            
            # Linear regression
            coeffs = np.polyfit(log_lags, log_tau, 1)
            hurst = coeffs[0] / 2.0
            
            return max(0.0, min(1.0, hurst))
            
        except Exception as e:
            logger.warning(f"Error calculating Hurst exponent: {e}")
            return None
    
    def _calculate_volatility_clustering(self, returns: pd.Series) -> float:
        """Calculate volatility clustering metric."""
        try:
            # Calculate squared returns as proxy for volatility
            vol_proxy = returns.rolling(window=5).std()
            
            # Auto-correlation of volatility proxy
            autocorr = vol_proxy.autocorr(lag=1)
            
            return max(0.0, min(1.0, autocorr)) if not np.isnan(autocorr) else 0.5
            
        except Exception:
            return 0.5
    
    def _classify_regime(self, vol_metrics: Dict, trend_metrics: Dict, 
                        mr_metrics: Dict) -> MarketRegime:
        """Classify market regime based on calculated metrics."""
        is_high_vol = vol_metrics['is_high']
        is_trending = trend_metrics['is_trending']
        is_mean_reverting = mr_metrics['is_mean_reverting']
        
        # Classification logic
        if is_trending and not is_mean_reverting:
            return MarketRegime.TRENDING_HIGH_VOL if is_high_vol else MarketRegime.TRENDING_LOW_VOL
        elif is_mean_reverting and not is_trending:
            return MarketRegime.MEAN_REVERTING_HIGH_VOL if is_high_vol else MarketRegime.MEAN_REVERTING_LOW_VOL
        else:
            return MarketRegime.UNCERTAIN
    
    def _calculate_regime_confidence(self, vol_metrics: Dict, trend_metrics: Dict, 
                                   mr_metrics: Dict) -> float:
        """Calculate confidence in regime classification."""
        # Base confidence on strength of signals
        vol_confidence = abs(vol_metrics['percentile'] - 0.5) * 2  # 0-1 scale
        trend_confidence = trend_metrics['strength']
        mr_confidence = abs(mr_metrics['strength'] - 0.5) * 2
        
        # Average confidence with weights
        total_confidence = (vol_confidence * 0.3 + trend_confidence * 0.4 + mr_confidence * 0.3)
        
        return max(0.0, min(1.0, total_confidence))
    
    def _calculate_adaptive_thresholds(self, regime: MarketRegime, 
                                     vol_metrics: Dict) -> Dict[str, float]:
        """Calculate adaptive thresholds based on market regime."""
        base_thresholds = {
            'min_confidence_score': self.config.MIN_CONFIDENCE_SCORE,
            'rsi_oversold': self.config.RSI_OVERSOLD_THRESHOLD,
            'rsi_overbought': self.config.RSI_OVERBOUGHT_THRESHOLD,
            'volume_multiplier': self.config.VOLUME_SPIKE_MULTIPLIER,
            'position_size_multiplier': 1.0
        }
        
        # Adjust based on regime
        if regime == MarketRegime.TRENDING_HIGH_VOL:
            base_thresholds['min_confidence_score'] *= 0.9  # Be more aggressive in trending markets
            base_thresholds['rsi_oversold'] = 25  # More extreme RSI levels
            base_thresholds['rsi_overbought'] = 75
            base_thresholds['position_size_multiplier'] = 0.8  # Reduce size in high vol
            
        elif regime == MarketRegime.TRENDING_LOW_VOL:
            base_thresholds['min_confidence_score'] *= 0.8  # Even more aggressive
            base_thresholds['rsi_oversold'] = 20
            base_thresholds['rsi_overbought'] = 80
            base_thresholds['position_size_multiplier'] = 1.2  # Increase size in low vol
            
        elif regime == MarketRegime.MEAN_REVERTING_HIGH_VOL:
            base_thresholds['min_confidence_score'] *= 1.1  # Be more selective
            base_thresholds['rsi_oversold'] = 35  # Less extreme levels for mean reversion
            base_thresholds['rsi_overbought'] = 65
            base_thresholds['position_size_multiplier'] = 0.7
            
        elif regime == MarketRegime.MEAN_REVERTING_LOW_VOL:
            base_thresholds['min_confidence_score'] *= 1.0
            base_thresholds['position_size_multiplier'] = 1.1
            
        else:  # UNCERTAIN
            base_thresholds['min_confidence_score'] *= 1.2  # Be very selective
            base_thresholds['position_size_multiplier'] = 0.6
        
        # Additional volatility-based adjustments
        vol_adjustment = vol_metrics['percentile']
        base_thresholds['volume_multiplier'] *= (1 + vol_adjustment * 0.5)
        
        return base_thresholds
    
    def get_regime_specific_strategy(self, regime: MarketRegime) -> Dict[str, Any]:
        """Get trading strategy parameters for specific regime."""
        strategies = {
            MarketRegime.TRENDING_HIGH_VOL: {
                'preferred_indicators': ['macd', 'moving_averages', 'momentum'],
                'avoid_indicators': ['rsi_extremes', 'bollinger_reversal'],
                'position_holding_time': 'medium',
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 2.5
            },
            MarketRegime.TRENDING_LOW_VOL: {
                'preferred_indicators': ['moving_averages', 'trend_lines'],
                'avoid_indicators': ['volatility_breakouts'],
                'position_holding_time': 'long',
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 3.0
            },
            MarketRegime.MEAN_REVERTING_HIGH_VOL: {
                'preferred_indicators': ['rsi_extremes', 'bollinger_bands', 'support_resistance'],
                'avoid_indicators': ['trend_following'],
                'position_holding_time': 'short',
                'stop_loss_multiplier': 2.0,
                'take_profit_multiplier': 1.5
            },
            MarketRegime.MEAN_REVERTING_LOW_VOL: {
                'preferred_indicators': ['mean_reversion', 'range_trading'],
                'avoid_indicators': ['breakout_strategies'],
                'position_holding_time': 'short',
                'stop_loss_multiplier': 1.2,
                'take_profit_multiplier': 1.8
            },
            MarketRegime.UNCERTAIN: {
                'preferred_indicators': ['volume_confirmation', 'multiple_timeframes'],
                'avoid_indicators': [],
                'position_holding_time': 'short',
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 2.0
            }
        }
        
        return strategies.get(regime, strategies[MarketRegime.UNCERTAIN])
    
    def _get_default_regime(self) -> RegimeData:
        """Get default regime data in case of errors."""
        return RegimeData(
            regime=MarketRegime.UNCERTAIN,
            confidence=0.5,
            volatility_percentile=0.5,
            trend_strength=0.5,
            mean_reversion_strength=0.5,
            timestamp=datetime.now(),
            adaptive_thresholds={
                'min_confidence_score': self.config.MIN_CONFIDENCE_SCORE,
                'rsi_oversold': self.config.RSI_OVERSOLD_THRESHOLD,
                'rsi_overbought': self.config.RSI_OVERBOUGHT_THRESHOLD,
                'volume_multiplier': self.config.VOLUME_SPIKE_MULTIPLIER,
                'position_size_multiplier': 1.0
            }
        )
    
    def _load_regime_cache(self):
        """Load cached regime data."""
        try:
            if os.path.exists(self.regime_cache_file):
                with open(self.regime_cache_file, 'r') as f:
                    data = json.load(f)
                    # Load only recent history (last 30 days)
                    cutoff = datetime.now() - timedelta(days=30)
                    for item in data.get('history', []):
                        timestamp = datetime.fromisoformat(item['timestamp'])
                        if timestamp > cutoff:
                            self.regime_history.append(RegimeData(
                                regime=MarketRegime(item['regime']),
                                confidence=item['confidence'],
                                volatility_percentile=item['volatility_percentile'],
                                trend_strength=item['trend_strength'],
                                mean_reversion_strength=item['mean_reversion_strength'],
                                timestamp=timestamp,
                                adaptive_thresholds=item['adaptive_thresholds']
                            ))
        except Exception as e:
            logger.warning(f"Could not load regime cache: {e}")
    
    def _save_regime_cache(self):
        """Save regime data to cache."""
        try:
            # Keep only last 100 entries
            recent_history = self.regime_history[-100:]
            
            data = {
                'current_regime': {
                    'regime': self.current_regime.regime.value,
                    'confidence': self.current_regime.confidence,
                    'timestamp': self.current_regime.timestamp.isoformat()
                } if self.current_regime else None,
                'history': [
                    {
                        'regime': item.regime.value,
                        'confidence': item.confidence,
                        'volatility_percentile': item.volatility_percentile,
                        'trend_strength': item.trend_strength,
                        'mean_reversion_strength': item.mean_reversion_strength,
                        'timestamp': item.timestamp.isoformat(),
                        'adaptive_thresholds': item.adaptive_thresholds
                    }
                    for item in recent_history
                ]
            }
            
            with open(self.regime_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not save regime cache: {e}")
    
    def get_current_regime(self) -> Optional[RegimeData]:
        """Get current market regime."""
        return self.current_regime
    
    def get_regime_history(self, days: int = 7) -> List[RegimeData]:
        """Get regime history for specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        return [r for r in self.regime_history if r.timestamp > cutoff]
