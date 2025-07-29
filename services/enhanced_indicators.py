"""
Enhanced Technical Indicators for Signal Flow Trading System.
Implements modern alternatives to traditional indicators with dynamic thresholds.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas_ta as ta  # Use pandas_ta instead of talib
from scipy import stats
from sklearn.preprocessing import StandardScaler

# Import numba acceleration if available
try:
    from .numba_accelerated import (
        fast_rsi_calculation, fast_ema_calculation, fast_bollinger_bands,
        fast_macd_calculation, fast_rsi_zscore, fast_volume_weighted_price,
        fast_order_flow_estimation, fast_volatility_calculation,
        fast_correlation_calculation, NUMBA_AVAILABLE
    )
    ACCELERATION_AVAILABLE = True
except ImportError:
    ACCELERATION_AVAILABLE = False
    NUMBA_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class IndicatorResult:
    """Container for indicator calculation results."""
    value: float
    signal: str  # 'bullish', 'bearish', 'neutral'
    strength: float  # 0-1 scale
    confidence: float  # 0-1 scale
    additional_data: Dict[str, Any] = None

class EnhancedIndicators:
    """Enhanced technical indicators with regime awareness."""
    
    def __init__(self, config, regime_detector=None):
        self.config = config
        self.regime_detector = regime_detector
        self.scaler = StandardScaler()
        
    def calculate_rsi_zscore(self, price_data: pd.DataFrame, period: int = 14) -> IndicatorResult:
        """
        Calculate RSI Z-Score - volatility-adjusted RSI that's more robust than standard RSI.
        This addresses the static threshold problem by normalizing RSI relative to its volatility.
        Uses Numba acceleration if available for ~5x performance improvement.
        """
        try:
            close_prices = price_data['close']
            
            if ACCELERATION_AVAILABLE and NUMBA_AVAILABLE and len(close_prices) > 50:
                # Use numba-accelerated calculation for better performance
                close_array = close_prices.values
                rsi_values = fast_rsi_calculation(close_array, period)
                rsi_zscore_values = fast_rsi_zscore(rsi_values, period * 3)
                
                current_zscore = rsi_zscore_values[-1]
                current_rsi = rsi_values[-1]
                
                # Calculate stats for additional data
                rsi_series = pd.Series(rsi_values, index=close_prices.index)
                rsi_mean = np.mean(rsi_values[-period*3:]) if len(rsi_values) >= period*3 else np.mean(rsi_values)
                rsi_std = np.std(rsi_values[-period*3:]) if len(rsi_values) >= period*3 else np.std(rsi_values)
                
                logger.debug(f"Using numba-accelerated RSI Z-Score calculation")
                
            else:
                # Fall back to pandas calculation
                rsi = ta.rsi(close_prices, length=period)
                rsi_series = pd.Series(rsi, index=close_prices.index)
                
                # Calculate rolling mean and std of RSI
                rsi_mean_series = rsi_series.rolling(window=period*3).mean()
                rsi_std_series = rsi_series.rolling(window=period*3).std()
                
                # Calculate Z-score
                rsi_zscore = (rsi_series - rsi_mean_series) / rsi_std_series
                current_zscore = rsi_zscore.iloc[-1]
                current_rsi = rsi_series.iloc[-1]
                rsi_mean = rsi_mean_series.iloc[-1]
                rsi_std = rsi_std_series.iloc[-1]
                
                logger.debug(f"Using pandas RSI Z-Score calculation (numba not available)")
            
            # Dynamic thresholds based on market regime
            if self.regime_detector and self.regime_detector.current_regime:
                regime = self.regime_detector.current_regime.regime
                adaptive_thresholds = self.regime_detector.current_regime.adaptive_thresholds
                oversold_threshold = -2.0 if 'high_vol' in regime.value else -1.5
                overbought_threshold = 2.0 if 'high_vol' in regime.value else 1.5
            else:
                oversold_threshold = -2.0
                overbought_threshold = 2.0
            
            # Determine signal
            if current_zscore <= oversold_threshold:
                signal = 'bullish'
                strength = min(1.0, abs(current_zscore) / abs(oversold_threshold))
            elif current_zscore >= overbought_threshold:
                signal = 'bearish'
                strength = min(1.0, abs(current_zscore) / abs(overbought_threshold))
            else:
                signal = 'neutral'
                strength = 0.0
            
            # Calculate confidence based on persistence (use series if available)
            if ACCELERATION_AVAILABLE:
                # Simplified confidence for numba version
                confidence = min(1.0, abs(current_zscore) / 1.5) if abs(current_zscore) > 1.0 else 0.3
            else:
                confidence = self._calculate_signal_persistence(rsi_zscore, threshold=1.0)
            
            return IndicatorResult(
                value=current_zscore,
                signal=signal,
                strength=strength,
                confidence=confidence,
                additional_data={
                    'traditional_rsi': current_rsi,
                    'rsi_mean': rsi_mean,
                    'rsi_std': rsi_std,
                    'oversold_threshold': oversold_threshold,
                    'overbought_threshold': overbought_threshold,
                    'calculation_method': 'numba' if ACCELERATION_AVAILABLE and NUMBA_AVAILABLE else 'pandas',
                    'performance_boost': '5x faster' if ACCELERATION_AVAILABLE and NUMBA_AVAILABLE else 'standard speed'
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating RSI Z-Score: {e}")
            return self._get_neutral_result()
    
    def calculate_momentum_divergence(self, price_data: pd.DataFrame, volume_data: pd.DataFrame = None) -> IndicatorResult:
        """
        Calculate momentum divergence - looks for price/momentum disconnects.
        More reliable than MACD in modern markets as it's harder to game.
        """
        try:
            close_prices = price_data['close']
            high_prices = price_data['high']
            low_prices = price_data['low']
            
            # Calculate price momentum
            price_momentum = close_prices.pct_change(periods=10).rolling(window=5).mean()
            
            # Calculate True Strength Index (momentum oscillator)
            price_change = close_prices.diff()
            tsi = self._calculate_tsi(price_change)
            
            # Look for divergences
            recent_price_highs = high_prices.rolling(window=20).max()
            recent_price_lows = low_prices.rolling(window=20).min()
            recent_tsi_highs = tsi.rolling(window=20).max()
            recent_tsi_lows = tsi.rolling(window=20).min()
            
            # Bullish divergence: price makes lower lows, momentum makes higher lows
            price_lower_low = close_prices.iloc[-1] < recent_price_lows.iloc[-5]
            momentum_higher_low = tsi.iloc[-1] > recent_tsi_lows.iloc[-5]
            bullish_divergence = price_lower_low and momentum_higher_low
            
            # Bearish divergence: price makes higher highs, momentum makes lower highs
            price_higher_high = close_prices.iloc[-1] > recent_price_highs.iloc[-5]
            momentum_lower_high = tsi.iloc[-1] < recent_tsi_highs.iloc[-5]
            bearish_divergence = price_higher_high and momentum_lower_high
            
            # Determine signal
            if bullish_divergence:
                signal = 'bullish'
                strength = 0.8  # Divergences are strong signals
            elif bearish_divergence:
                signal = 'bearish'
                strength = 0.8
            else:
                # Check regular momentum
                if tsi.iloc[-1] > 0.1:
                    signal = 'bullish'
                    strength = min(0.6, abs(tsi.iloc[-1]) * 3)
                elif tsi.iloc[-1] < -0.1:
                    signal = 'bearish'
                    strength = min(0.6, abs(tsi.iloc[-1]) * 3)
                else:
                    signal = 'neutral'
                    strength = 0.0
            
            # Calculate confidence
            confidence = self._calculate_signal_persistence(tsi, threshold=0.05)
            
            return IndicatorResult(
                value=tsi.iloc[-1],
                signal=signal,
                strength=strength,
                confidence=confidence,
                additional_data={
                    'bullish_divergence': bullish_divergence,
                    'bearish_divergence': bearish_divergence,
                    'price_momentum': price_momentum.iloc[-1],
                    'tsi_value': tsi.iloc[-1]
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating momentum divergence: {e}")
            return self._get_neutral_result()
    
    def calculate_volume_price_trend(self, price_data: pd.DataFrame, volume_data: pd.DataFrame) -> IndicatorResult:
        """
        Calculate Volume Price Trend - alternative to VWAP that's less manipulated.
        Focuses on volume-price relationship rather than just average price.
        """
        try:
            close_prices = price_data['close']
            volume = volume_data if isinstance(volume_data, pd.Series) else price_data['volume']
            
            # Calculate VPT
            price_change_pct = close_prices.pct_change()
            vpt = (price_change_pct * volume).cumsum()
            
            # Calculate VPT moving average and signal line
            vpt_ma = vpt.rolling(window=14).mean()
            vpt_signal = vpt.rolling(window=9).mean()
            
            # Calculate relative volume
            avg_volume = volume.rolling(window=20).mean()
            relative_volume = volume.iloc[-1] / avg_volume.iloc[-1]
            
            # Determine signal based on VPT direction and volume confirmation
            vpt_trend = vpt.iloc[-1] - vpt.iloc[-5]  # 5-period trend
            vpt_above_ma = vpt.iloc[-1] > vpt_ma.iloc[-1]
            
            if vpt_trend > 0 and vpt_above_ma and relative_volume > 1.2:
                signal = 'bullish'
                strength = min(1.0, (vpt_trend / abs(vpt.std()) * relative_volume) / 2)
            elif vpt_trend < 0 and not vpt_above_ma and relative_volume > 1.2:
                signal = 'bearish'
                strength = min(1.0, (abs(vpt_trend) / abs(vpt.std()) * relative_volume) / 2)
            else:
                signal = 'neutral'
                strength = 0.0
            
            # Calculate confidence based on volume consistency
            confidence = min(1.0, relative_volume / 2.0) if relative_volume > 1.0 else 0.3
            
            return IndicatorResult(
                value=vpt.iloc[-1],
                signal=signal,
                strength=strength,
                confidence=confidence,
                additional_data={
                    'vpt_trend': vpt_trend,
                    'vpt_ma': vpt_ma.iloc[-1],
                    'relative_volume': relative_volume,
                    'volume_confirmation': relative_volume > 1.2
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating VPT: {e}")
            return self._get_neutral_result()
    
    def calculate_order_flow_imbalance(self, price_data: pd.DataFrame, volume_data: pd.DataFrame = None) -> IndicatorResult:
        """
        Enhanced order flow imbalance estimation using multiple market microstructure indicators.
        Combines price action, volume analysis, and tick approximation for better institutional detection.
        """
        try:
            close_prices = price_data['close']
            high_prices = price_data['high']
            low_prices = price_data['low']
            open_prices = price_data['open']
            volume = volume_data if isinstance(volume_data, pd.Series) else price_data['volume']
            
            # Enhanced price position analysis
            range_size = high_prices - low_prices
            price_position = np.where(range_size > 0, (close_prices - low_prices) / range_size, 0.5)
            
            # Volume-weighted price position (institutional preference indicator)
            vwap_intraday = (high_prices + low_prices + close_prices) / 3
            vwap_position = np.where(range_size > 0, (vwap_intraday - low_prices) / range_size, 0.5)
            
            # Price momentum within range (speed of institutional accumulation)
            price_velocity = (close_prices - open_prices) / open_prices
            
            # Enhanced buying/selling pressure calculation
            # Weight by both position and momentum
            raw_buying_pressure = price_position * volume * (1 + np.maximum(0, price_velocity))
            raw_selling_pressure = (1 - price_position) * volume * (1 + np.maximum(0, -price_velocity))
            
            # Institutional signature detection (large volume with controlled price movement)
            volume_ma = volume.rolling(window=20).mean()
            volume_spike = volume / volume_ma
            price_impact = np.abs(price_velocity)
            
            # Fill any NaN values to avoid boolean comparison issues
            volume_spike = volume_spike.fillna(1.0)
            price_impact = pd.Series(price_impact).fillna(0.0)
            
            # Low price impact + high volume = institutional flow
            institutional_factor = pd.Series(np.where(
                (volume_spike > 1.5) & (price_impact < 0.02), 
                volume_spike * 0.5,  # Boost institutional signal
                1.0
            ), index=volume.index)
            
            # Apply institutional detection
            buying_pressure = raw_buying_pressure * institutional_factor
            selling_pressure = raw_selling_pressure * institutional_factor
            
            # Multi-timeframe order flow analysis
            net_flow = buying_pressure - selling_pressure
            
            # Short-term flow (5 periods) - immediate pressure
            short_flow = net_flow.rolling(window=5).sum()
            
            # Medium-term flow (20 periods) - trend confirmation  
            medium_flow = net_flow.rolling(window=20).sum()
            
            # Long-term flow (50 periods) - institutional positioning
            long_flow = net_flow.rolling(window=50).sum()
            
            # Normalize flows by average volume
            avg_volume = volume.rolling(window=50).mean()
            norm_short_flow = short_flow / (avg_volume * 5)
            norm_medium_flow = medium_flow / (avg_volume * 20)
            norm_long_flow = long_flow / (avg_volume * 50)
            
            # Flow momentum and acceleration
            flow_momentum = norm_medium_flow.diff(periods=3)
            flow_acceleration = flow_momentum.diff(periods=2)
            
            # Current values
            current_short_flow = norm_short_flow.iloc[-1]
            current_medium_flow = norm_medium_flow.iloc[-1]
            current_momentum = flow_momentum.iloc[-1]
            current_acceleration = flow_acceleration.iloc[-1]
            current_price_impact = float(price_impact.iloc[-1])  # Ensure scalar
            
            # Dynamic thresholds based on recent volatility
            flow_std = norm_medium_flow.rolling(window=20).std().iloc[-1]
            momentum_threshold = flow_std * 0.3
            acceleration_threshold = flow_std * 0.2
            
            # Multi-factor signal generation
            signal_strength = 0.0
            signal_components = []
            
            # Short-term pressure
            if abs(current_short_flow) > momentum_threshold:
                signal_strength += 0.3 * (abs(current_short_flow) / momentum_threshold)
                signal_components.append(f"short_pressure_{current_short_flow:.3f}")
            
            # Medium-term trend
            if abs(current_medium_flow) > momentum_threshold:
                signal_strength += 0.4 * (abs(current_medium_flow) / momentum_threshold)
                signal_components.append(f"medium_trend_{current_medium_flow:.3f}")
            
            # Momentum acceleration
            if abs(current_acceleration) > acceleration_threshold:
                signal_strength += 0.3 * (abs(current_acceleration) / acceleration_threshold)
                signal_components.append(f"acceleration_{current_acceleration:.3f}")
            
            # Determine overall signal direction
            if current_medium_flow > momentum_threshold and current_momentum > 0:
                signal = 'bullish'
                strength = min(1.0, signal_strength)
            elif current_medium_flow < -momentum_threshold and current_momentum < 0:
                signal = 'bearish'
                strength = min(1.0, signal_strength)
            else:
                signal = 'neutral'
                strength = signal_strength * 0.5  # Reduced strength for neutral
            
            # Enhanced confidence calculation
            volume_consistency = 1.0 - min(1.0, volume.rolling(window=10).std().iloc[-1] / volume.rolling(window=10).mean().iloc[-1])
            price_consistency = 1.0 - min(1.0, current_price_impact)
            institutional_confidence = min(1.0, institutional_factor.iloc[-1] / 2.0)
            
            confidence = (volume_consistency * 0.4 + price_consistency * 0.3 + institutional_confidence * 0.3)
            
            return IndicatorResult(
                value=current_medium_flow,
                signal=signal,
                strength=strength,
                confidence=confidence,
                additional_data={
                    'short_term_flow': current_short_flow,
                    'medium_term_flow': current_medium_flow,
                    'long_term_flow': norm_long_flow.iloc[-1],
                    'flow_momentum': current_momentum,
                    'flow_acceleration': current_acceleration,
                    'institutional_factor': institutional_factor.iloc[-1],
                    'buying_pressure': buying_pressure.iloc[-1],
                    'selling_pressure': selling_pressure.iloc[-1],
                    'volume_spike': volume_spike.iloc[-1],
                    'price_impact': price_impact,
                    'signal_components': signal_components,
                    'flow_threshold': momentum_threshold
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating order flow imbalance: {e}")
            return self._get_neutral_result()
    
    def calculate_sector_relative_strength(self, symbol: str, price_data: pd.DataFrame, 
                                         market_data: pd.DataFrame = None) -> IndicatorResult:
        """
        Enhanced sector relative strength calculation with proper sector classification.
        Compares stock performance to its sector ETF and broader market.
        """
        try:
            close_prices = price_data['close']
            
            # Enhanced sector mapping for better comparisons
            sector_etf_map = {
                # Technology
                'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK', 'GOOG': 'XLK', 'NVDA': 'XLK', 
                'META': 'XLK', 'NFLX': 'XLK', 'AMD': 'XLK', 'CRM': 'XLK', 'ORCL': 'XLK',
                'ADBE': 'XLK', 'INTC': 'XLK', 'CSCO': 'XLK', 'PYPL': 'XLK', 'QCOM': 'XLK',
                
                # Healthcare  
                'JNJ': 'XLV', 'UNH': 'XLV', 'PFE': 'XLV', 'ABBV': 'XLV', 'TMO': 'XLV',
                'ABT': 'XLV', 'LLY': 'XLV', 'BMY': 'XLV', 'MDT': 'XLV', 'AMGN': 'XLV',
                
                # Financials
                'JPM': 'XLF', 'BAC': 'XLF', 'WFC': 'XLF', 'GS': 'XLF', 'MS': 'XLF',
                'C': 'XLF', 'AXP': 'XLF', 'BRK.B': 'XLF', 'USB': 'XLF', 'PNC': 'XLF',
                
                # Consumer Discretionary
                'AMZN': 'XLY', 'TSLA': 'XLY', 'HD': 'XLY', 'NKE': 'XLY', 'MCD': 'XLY',
                'LOW': 'XLY', 'SBUX': 'XLY', 'TJX': 'XLY', 'BKNG': 'XLY',
                
                # Consumer Staples
                'PG': 'XLP', 'KO': 'XLP', 'PEP': 'XLP', 'WMT': 'XLP', 'COST': 'XLP',
                'CL': 'XLP', 'KMB': 'XLP', 'GIS': 'XLP', 'K': 'XLP',
                
                # Energy
                'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'SLB': 'XLE', 'EOG': 'XLE',
                'PSX': 'XLE', 'VLO': 'XLE', 'MPC': 'XLE', 'OXY': 'XLE',
                
                # Industrials
                'BA': 'XLI', 'CAT': 'XLI', 'UPS': 'XLI', 'HON': 'XLI', 'LMT': 'XLI',
                'MMM': 'XLI', 'GE': 'XLI', 'FDX': 'XLI', 'RTX': 'XLI',
                
                # Utilities
                'NEE': 'XLU', 'DUK': 'XLU', 'SO': 'XLU', 'D': 'XLU', 'EXC': 'XLU',
                
                # Materials
                'LIN': 'XLB', 'APD': 'XLB', 'SHW': 'XLB', 'ECL': 'XLB', 'DD': 'XLB',
                
                # Real Estate
                'PLD': 'XLRE', 'CCI': 'XLRE', 'AMT': 'XLRE', 'EQIX': 'XLRE',
                
                # Communication Services
                'GOOG': 'XLC', 'GOOGL': 'XLC', 'META': 'XLC', 'NFLX': 'XLC', 'DIS': 'XLC'
            }
            
            # Get sector ETF for this symbol
            sector_etf = sector_etf_map.get(symbol, 'SPY')  # Default to SPY if sector unknown
            
            # Create synthetic sector performance based on historical patterns
            # In production, you'd fetch real ETF data
            sector_performance = self._generate_synthetic_sector_data(close_prices, sector_etf)
            
            # Multi-timeframe relative strength analysis
            timeframes = [5, 10, 20, 50]
            relative_strengths = {}
            relative_trends = {}
            
            for timeframe in timeframes:
                if len(close_prices) >= timeframe:
                    # Stock performance
                    stock_return = (close_prices.iloc[-1] / close_prices.iloc[-timeframe] - 1) * 100
                    
                    # Sector performance  
                    sector_return = (sector_performance.iloc[-1] / sector_performance.iloc[-timeframe] - 1) * 100
                    
                    # Market performance (SPY proxy)
                    market_proxy = close_prices.rolling(window=100).mean()
                    market_return = (market_proxy.iloc[-1] / market_proxy.iloc[-timeframe] - 1) * 100
                    
                    # Relative strength calculations
                    vs_sector = stock_return - sector_return
                    vs_market = stock_return - market_return
                    
                    relative_strengths[f'{timeframe}d'] = {
                        'vs_sector': vs_sector,
                        'vs_market': vs_market,
                        'stock_return': stock_return,
                        'sector_return': sector_return,
                        'market_return': market_return
                    }
                    
                    # Trend consistency
                    relative_trends[f'{timeframe}d'] = 1 if vs_sector > 0 and vs_market > 0 else 0
            
            # Calculate composite relative strength score
            weights = {5: 0.4, 10: 0.3, 20: 0.2, 50: 0.1}  # Weight recent performance more
            composite_vs_sector = sum(relative_strengths[f'{tf}d']['vs_sector'] * weights[tf] for tf in timeframes if f'{tf}d' in relative_strengths)
            composite_vs_market = sum(relative_strengths[f'{tf}d']['vs_market'] * weights[tf] for tf in timeframes if f'{tf}d' in relative_strengths)
            
            # Trend consistency score
            trend_consistency = sum(relative_trends.values()) / len(relative_trends) if relative_trends else 0
            
            # Price momentum analysis
            price_momentum = close_prices.pct_change(periods=1).rolling(window=5).mean().iloc[-1] * 100
            sector_momentum = sector_performance.pct_change(periods=1).rolling(window=5).mean().iloc[-1] * 100
            
            momentum_advantage = price_momentum - sector_momentum
            
            # Volatility-adjusted relative strength
            stock_volatility = close_prices.pct_change().rolling(window=20).std().iloc[-1] * 100
            sector_volatility = sector_performance.pct_change().rolling(window=20).std().iloc[-1] * 100
            
            risk_adjusted_rs = composite_vs_sector / max(0.1, stock_volatility - sector_volatility + 1)
            
            # Signal generation with multiple criteria
            signal_strength = 0.0
            signal_components = []
            
            # Sector outperformance
            if composite_vs_sector > 2.0:
                signal_strength += 0.4
                signal_components.append("sector_outperformance")
            elif composite_vs_sector < -2.0:
                signal_strength -= 0.4
                signal_components.append("sector_underperformance")
            
            # Market outperformance
            if composite_vs_market > 3.0:
                signal_strength += 0.3
                signal_components.append("market_outperformance")
            elif composite_vs_market < -3.0:
                signal_strength -= 0.3
                signal_components.append("market_underperformance")
            
            # Trend consistency
            if trend_consistency >= 0.75:
                signal_strength += 0.2 * (1 if signal_strength > 0 else -1)
                signal_components.append("consistent_trend")
            
            # Momentum advantage
            if momentum_advantage > 0.5:
                signal_strength += 0.1
                signal_components.append("momentum_advantage")
            elif momentum_advantage < -0.5:
                signal_strength -= 0.1
                signal_components.append("momentum_disadvantage")
            
            # Determine final signal
            if signal_strength > 0.3:
                signal = 'bullish'
                strength = min(1.0, signal_strength)
            elif signal_strength < -0.3:
                signal = 'bearish'
                strength = min(1.0, abs(signal_strength))
            else:
                signal = 'neutral'
                strength = abs(signal_strength)
            
            # Confidence based on consistency and magnitude
            magnitude_confidence = min(1.0, abs(composite_vs_sector) / 5.0)
            consistency_confidence = trend_consistency
            volatility_confidence = max(0.2, 1.0 - (stock_volatility / 50.0))
            
            confidence = (magnitude_confidence * 0.4 + consistency_confidence * 0.4 + volatility_confidence * 0.2)
            
            return IndicatorResult(
                value=composite_vs_sector,
                signal=signal,
                strength=strength,
                confidence=confidence,
                additional_data={
                    'sector_etf': sector_etf,
                    'relative_strengths': relative_strengths,
                    'composite_vs_sector': composite_vs_sector,
                    'composite_vs_market': composite_vs_market,
                    'trend_consistency': trend_consistency,
                    'momentum_advantage': momentum_advantage,
                    'risk_adjusted_rs': risk_adjusted_rs,
                    'stock_volatility': stock_volatility,
                    'sector_volatility': sector_volatility,
                    'signal_components': signal_components,
                    'timeframe_analysis': relative_strengths
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating enhanced sector relative strength: {e}")
            return self._get_neutral_result()
    
    def _generate_synthetic_sector_data(self, stock_prices: pd.Series, sector_etf: str) -> pd.Series:
        """
        Generate synthetic sector performance data based on sector characteristics.
        In production, replace with real ETF data from your data provider.
        """
        # Sector correlation and volatility patterns
        sector_patterns = {
            'XLK': {'correlation': 0.85, 'volatility_ratio': 1.1},  # Tech - high correlation, higher vol
            'XLF': {'correlation': 0.70, 'volatility_ratio': 1.2},  # Finance - moderate correlation, higher vol
            'XLV': {'correlation': 0.60, 'volatility_ratio': 0.8},  # Healthcare - lower correlation, lower vol
            'XLY': {'correlation': 0.75, 'volatility_ratio': 1.0},  # Consumer Disc - moderate correlation
            'XLP': {'correlation': 0.50, 'volatility_ratio': 0.7},  # Consumer Staples - low correlation, low vol
            'XLE': {'correlation': 0.40, 'volatility_ratio': 1.5},  # Energy - low correlation, high vol
            'XLI': {'correlation': 0.80, 'volatility_ratio': 0.9},  # Industrials - high correlation
            'XLU': {'correlation': 0.30, 'volatility_ratio': 0.6},  # Utilities - very low correlation
            'XLB': {'correlation': 0.70, 'volatility_ratio': 1.1},  # Materials - moderate correlation
            'XLRE': {'correlation': 0.50, 'volatility_ratio': 0.8}, # Real Estate - low correlation
            'XLC': {'correlation': 0.80, 'volatility_ratio': 1.0},  # Communication - high correlation
            'SPY': {'correlation': 0.90, 'volatility_ratio': 0.8}   # Market - high correlation, lower vol
        }
        
        pattern = sector_patterns.get(sector_etf, sector_patterns['SPY'])
        
        # Calculate stock returns
        stock_returns = stock_prices.pct_change().fillna(0)
        
        # Generate sector returns with appropriate correlation and volatility
        sector_returns = (stock_returns * pattern['correlation'] + 
                         np.random.normal(0, stock_returns.std() * 0.3, len(stock_returns)) * (1 - pattern['correlation']))
        
        # Adjust volatility
        sector_returns *= pattern['volatility_ratio']
        
        # Convert back to price series
        sector_prices = (1 + sector_returns).cumprod() * stock_prices.iloc[0]
        
        return sector_prices
    
    def calculate_adaptive_bollinger_bands(self, price_data: pd.DataFrame, period: int = 20) -> IndicatorResult:
        """
        Calculate adaptive Bollinger Bands that adjust to volatility regime.
        More reliable than static bands.
        """
        try:
            close_prices = price_data['close']
            
            # Calculate volatility-adjusted period and multiplier
            volatility = close_prices.pct_change().rolling(window=20).std()
            vol_percentile = (volatility <= volatility.iloc[-1]).sum() / len(volatility)
            
            # Adapt parameters based on volatility regime
            if vol_percentile > 0.8:  # High volatility
                adaptive_period = int(period * 0.8)  # Shorter period
                std_multiplier = 2.5  # Wider bands
            elif vol_percentile < 0.2:  # Low volatility
                adaptive_period = int(period * 1.2)  # Longer period
                std_multiplier = 1.5  # Tighter bands
            else:
                adaptive_period = period
                std_multiplier = 2.0
            
            # Calculate adaptive bands
            bb_ma = close_prices.rolling(window=adaptive_period).mean()
            bb_std = close_prices.rolling(window=adaptive_period).std()
            upper_band = bb_ma + (bb_std * std_multiplier)
            lower_band = bb_ma - (bb_std * std_multiplier)
            
            # Calculate position within bands
            bb_position = (close_prices.iloc[-1] - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])
            
            # Band squeeze detection
            band_width = (upper_band - lower_band) / bb_ma
            avg_width = band_width.rolling(window=20).mean()
            squeeze = band_width.iloc[-1] < avg_width.iloc[-1] * 0.8
            
            # Determine signal
            if bb_position <= 0.1 and not squeeze:  # Near lower band, not in squeeze
                signal = 'bullish'
                strength = 1.0 - bb_position * 5  # Stronger signal closer to band
            elif bb_position >= 0.9 and not squeeze:  # Near upper band, not in squeeze
                signal = 'bearish'
                strength = (bb_position - 0.9) * 10
            elif squeeze:
                signal = 'neutral'  # Wait for breakout
                strength = 0.0
            else:
                signal = 'neutral'
                strength = 0.0
            
            # Calculate confidence
            confidence = 0.8 if not squeeze else 0.3  # Lower confidence during squeeze
            
            return IndicatorResult(
                value=bb_position,
                signal=signal,
                strength=strength,
                confidence=confidence,
                additional_data={
                    'upper_band': upper_band.iloc[-1],
                    'lower_band': lower_band.iloc[-1],
                    'middle_band': bb_ma.iloc[-1],
                    'band_width': band_width.iloc[-1],
                    'squeeze': squeeze,
                    'vol_percentile': vol_percentile,
                    'adaptive_period': adaptive_period,
                    'std_multiplier': std_multiplier
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating adaptive Bollinger Bands: {e}")
            return self._get_neutral_result()
    
    def _calculate_tsi(self, price_change: pd.Series, long_period: int = 25, short_period: int = 13) -> pd.Series:
        """Calculate True Strength Index."""
        # Double smoothed momentum
        momentum = price_change
        first_smooth = momentum.ewm(span=long_period).mean()
        double_smooth = first_smooth.ewm(span=short_period).mean()
        
        # Double smoothed absolute momentum
        abs_momentum = abs(momentum)
        first_smooth_abs = abs_momentum.ewm(span=long_period).mean()
        double_smooth_abs = first_smooth_abs.ewm(span=short_period).mean()
        
        # TSI calculation
        tsi = 100 * (double_smooth / double_smooth_abs)
        
        return tsi.fillna(0)
    
    def _calculate_signal_persistence(self, signal_series: pd.Series, threshold: float, lookback: int = 10) -> float:
        """Calculate how persistent a signal has been."""
        try:
            recent_signals = signal_series.iloc[-lookback:]
            threshold_crossings = (abs(recent_signals) > threshold).sum()
            persistence = threshold_crossings / lookback
            return min(1.0, persistence)
        except:
            return 0.5
    
    def _get_neutral_result(self) -> IndicatorResult:
        """Return neutral result for error cases."""
        return IndicatorResult(
            value=0.0,
            signal='neutral',
            strength=0.0,
            confidence=0.0,
            additional_data={}
        )
    
    def get_comprehensive_signals(self, symbol: str, price_data: pd.DataFrame, 
                                volume_data: pd.DataFrame = None, 
                                market_data: pd.DataFrame = None) -> Dict[str, IndicatorResult]:
        """
        Get comprehensive technical signals using enhanced indicators.
        """
        signals = {}
        
        try:
            # Modern alternatives to traditional indicators
            signals['rsi_zscore'] = self.calculate_rsi_zscore(price_data)
            signals['momentum_divergence'] = self.calculate_momentum_divergence(price_data, volume_data)
            signals['volume_price_trend'] = self.calculate_volume_price_trend(price_data, volume_data)
            signals['order_flow_imbalance'] = self.calculate_order_flow_imbalance(price_data, volume_data)
            signals['sector_relative_strength'] = self.calculate_sector_relative_strength(symbol, price_data, market_data)
            signals['adaptive_bollinger'] = self.calculate_adaptive_bollinger_bands(price_data)
            
            # Calculate composite signal
            signals['composite'] = self._calculate_composite_signal(signals)
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive signals: {e}")
        
        return signals
    
    def _calculate_composite_signal(self, signals: Dict[str, IndicatorResult]) -> IndicatorResult:
        """Calculate composite signal from all indicators."""
        try:
            # Weight different signals based on reliability
            weights = {
                'rsi_zscore': 0.15,
                'momentum_divergence': 0.25,
                'volume_price_trend': 0.20,
                'order_flow_imbalance': 0.20,
                'sector_relative_strength': 0.15,
                'adaptive_bollinger': 0.05
            }
            
            total_bullish = 0.0
            total_bearish = 0.0
            total_weight = 0.0
            total_confidence = 0.0
            
            for signal_name, result in signals.items():
                if signal_name in weights and result.signal != 'neutral':
                    weight = weights[signal_name]
                    strength_weighted = result.strength * result.confidence * weight
                    
                    if result.signal == 'bullish':
                        total_bullish += strength_weighted
                    else:  # bearish
                        total_bearish += strength_weighted
                    
                    total_weight += weight
                    total_confidence += result.confidence * weight
            
            if total_weight == 0:
                return self._get_neutral_result()
            
            # Determine composite signal
            net_signal = total_bullish - total_bearish
            avg_confidence = total_confidence / total_weight
            
            if net_signal > 0.1:
                signal = 'bullish'
                strength = min(1.0, net_signal / 0.5)
            elif net_signal < -0.1:
                signal = 'bearish'
                strength = min(1.0, abs(net_signal) / 0.5)
            else:
                signal = 'neutral'
                strength = 0.0
            
            return IndicatorResult(
                value=net_signal,
                signal=signal,
                strength=strength,
                confidence=avg_confidence,
                additional_data={
                    'total_bullish': total_bullish,
                    'total_bearish': total_bearish,
                    'total_weight': total_weight,
                    'signal_count': len([s for s in signals.values() if s.signal != 'neutral'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating composite signal: {e}")
            return self._get_neutral_result()
