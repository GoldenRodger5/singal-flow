"""
Technical indicators for trading analysis.
Enhanced with modern alternatives to traditional indicators.
Integrated with LLM routing and time-window trading strategies.
"""
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Tuple, Optional, Any
from datetime import datetime
from loguru import logger

# Import enhanced indicators and new systems
try:
    from .enhanced_indicators import EnhancedIndicators
    from .market_regime_detector import MarketRegimeDetector
    from .llm_router import LLMRouter, TaskType
    from .trading_window_config import TradingWindowManager, StrategyType
    ENHANCED_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced indicators not available, falling back to traditional indicators")
    ENHANCED_AVAILABLE = False


class TechnicalIndicators:
    """Calculate various technical indicators for trading analysis."""
    
    def __init__(self, config=None, regime_detector=None):
        self.config = config
        self.regime_detector = regime_detector
        
        # Initialize enhanced indicators if available
        if ENHANCED_AVAILABLE and config:
            self.enhanced_indicators = EnhancedIndicators(config, regime_detector)
            self.llm_router = LLMRouter(config)
            self.window_manager = TradingWindowManager()
        else:
            self.enhanced_indicators = None
            self.llm_router = None
            self.window_manager = None
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        try:
            return ta.rsi(df['close'], length=period)
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(dtype=float)
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        try:
            macd_data = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
            return {
                'macd': macd_data[f'MACD_{fast}_{slow}_{signal}'],
                'signal': macd_data[f'MACDs_{fast}_{slow}_{signal}'],
                'histogram': macd_data[f'MACDh_{fast}_{slow}_{signal}']
            }
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {'macd': pd.Series(dtype=float), 'signal': pd.Series(dtype=float), 
                   'histogram': pd.Series(dtype=float)}
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price."""
        try:
            return ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return pd.Series(dtype=float)
    
    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, 
                                 std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        try:
            bb = ta.bbands(df['close'], length=period, std=std_dev)
            return {
                'upper': bb[f'BBU_{period}_{std_dev}.0'],
                'middle': bb[f'BBM_{period}_{std_dev}.0'],
                'lower': bb[f'BBL_{period}_{std_dev}.0']
            }
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {'upper': pd.Series(dtype=float), 'middle': pd.Series(dtype=float), 
                   'lower': pd.Series(dtype=float)}
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average."""
        try:
            return ta.ema(df['close'], length=period)
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return pd.Series(dtype=float)
    
    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Simple Moving Average."""
        try:
            return ta.sma(df['close'], length=period)
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            return pd.Series(dtype=float)
    
    def get_enhanced_signals(self, symbol: str, df: pd.DataFrame, volume_data: pd.DataFrame = None,
                           market_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Get enhanced technical signals using modern indicators with time-window optimization.
        Falls back to traditional indicators if enhanced not available.
        """
        try:
            if self.enhanced_indicators and ENHANCED_AVAILABLE:
                # Get current trading window
                current_window = self.window_manager.get_current_window()
                window_config = self.window_manager.get_window_config(current_window)
                
                # Use enhanced indicators with regime awareness
                enhanced_signals = self.enhanced_indicators.get_comprehensive_signals(
                    symbol, df, volume_data, market_data
                )
                
                # Apply time-window filtering
                filtered_signals = self._filter_signals_by_window(enhanced_signals, current_window)
                
                # Convert to format expected by existing code
                signals = {
                    'rsi_zscore': filtered_signals.get('rsi_zscore'),
                    'momentum_divergence': filtered_signals.get('momentum_divergence'),
                    'volume_price_trend': filtered_signals.get('volume_price_trend'),
                    'order_flow': filtered_signals.get('order_flow_imbalance'),
                    'relative_strength': filtered_signals.get('sector_relative_strength'),
                    'adaptive_bollinger': filtered_signals.get('adaptive_bollinger'),
                    'composite': filtered_signals.get('composite')
                }
                
                # Add regime information if available
                if self.regime_detector and self.regime_detector.current_regime:
                    signals['market_regime'] = {
                        'regime': self.regime_detector.current_regime.regime.value,
                        'confidence': self.regime_detector.current_regime.confidence,
                        'adaptive_thresholds': self.regime_detector.current_regime.adaptive_thresholds
                    }
                
                # Add window-specific information
                signals['trading_window'] = {
                    'current_window': current_window.value,
                    'risk_level': window_config.risk_level if window_config else 'UNKNOWN',
                    'position_multiplier': window_config.position_size_multiplier if window_config else 1.0,
                    'confidence_threshold': window_config.min_confidence_threshold if window_config else 0.6
                }
                
                # Generate AI explanation for signals using LLM
                if self.llm_router:
                    explanation = self._generate_signal_explanation(symbol, signals, df)
                    signals['ai_explanation'] = explanation
                
                return signals
            else:
                # Fall back to traditional indicators
                return self._get_traditional_signals(df)
                
        except Exception as e:
            logger.error(f"Error getting enhanced signals: {e}")
            return self._get_traditional_signals(df)
    
    def _get_traditional_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get traditional technical signals as fallback."""
        try:
            rsi = self.calculate_rsi(df)
            macd_data = self.calculate_macd(df)
            vwap = self.calculate_vwap(df)
            bb_data = self.calculate_bollinger_bands(df)
            
            # Create simplified signal format
            signals = {
                'rsi': {
                    'value': rsi.iloc[-1] if not rsi.empty else 50,
                    'signal': 'bullish' if rsi.iloc[-1] < 30 else 'bearish' if rsi.iloc[-1] > 70 else 'neutral',
                    'strength': 0.5,
                    'confidence': 0.6
                },
                'macd': {
                    'value': macd_data['macd'].iloc[-1] if not macd_data['macd'].empty else 0,
                    'signal': 'bullish' if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1] else 'bearish',
                    'strength': 0.5,
                    'confidence': 0.6
                },
                'vwap': {
                    'value': vwap.iloc[-1] if not vwap.empty else df['close'].iloc[-1],
                    'signal': 'bullish' if df['close'].iloc[-1] > vwap.iloc[-1] else 'bearish',
                    'strength': 0.5,
                    'confidence': 0.6
                }
            }
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting traditional signals: {e}")
            return {}
    
    def _filter_signals_by_window(self, signals: Dict[str, Any], current_window) -> Dict[str, Any]:
        """Filter and adjust signals based on current trading window."""
        if not self.window_manager or not signals:
            return signals
        
        try:
            window_config = self.window_manager.get_window_config(current_window)
            if not window_config:
                return signals
            
            filtered_signals = signals.copy()
            
            # Adjust confidence thresholds based on window
            confidence_adjustment = window_config.min_confidence_threshold
            
            for signal_name, signal_data in filtered_signals.items():
                if isinstance(signal_data, dict) and 'confidence' in signal_data:
                    # Reduce signal strength if confidence is below window threshold
                    if signal_data['confidence'] < confidence_adjustment:
                        signal_data['strength'] *= 0.5
                        signal_data['adjusted_for_window'] = True
                        signal_data['window_reason'] = f"Confidence below {confidence_adjustment} threshold"
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error filtering signals by window: {e}")
            return signals
    
    def _generate_signal_explanation(self, symbol: str, signals: Dict[str, Any], df: pd.DataFrame) -> str:
        """Generate AI explanation for trading signals."""
        try:
            if not self.llm_router:
                return "AI explanation not available"
            
            # Prepare context for LLM
            current_price = df['close'].iloc[-1]
            price_change = ((current_price - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
            volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
            
            context = {
                'symbol': symbol,
                'current_price': current_price,
                'price_change_pct': price_change,
                'volume_ratio': volume_ratio,
                'signals': signals,
                'window': signals.get('trading_window', {}).get('current_window', 'unknown')
            }
            
            prompt = f"""
            Explain the trading signals for {symbol}:
            
            Current Price: ${current_price:.2f} ({price_change:+.2f}%)
            Volume: {volume_ratio:.1f}x average
            Trading Window: {context['window']}
            
            Signals detected: {list(signals.keys())}
            
            Provide a concise explanation of:
            1. What the signals indicate
            2. Why this might be a trading opportunity (or not)
            3. Key risks to consider
            4. How the current trading window affects the setup
            """
            
            result = self.llm_router.route_task(TaskType.TRADE_EXPLANATION, prompt, context)
            return result['response']
            
        except Exception as e:
            logger.error(f"Error generating signal explanation: {e}")
            return f"Error generating explanation: {str(e)}"
    
    def get_window_optimized_strategy(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Get strategy recommendation optimized for current trading window."""
        try:
            if not self.window_manager:
                return {'strategy': 'unknown', 'confidence': 0}
            
            current_window = self.window_manager.get_current_window()
            window_config = self.window_manager.get_window_config(current_window)
            
            if not window_config:
                return {'strategy': 'market_closed', 'confidence': 0}
            
            # Analyze signals to determine best strategy for window
            strategy_scores = {}
            
            for strategy in window_config.allowed_strategies:
                score = self._score_strategy_for_signals(strategy, signals)
                strategy_scores[strategy.value] = score
            
            # Get best strategy
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
            
            return {
                'recommended_strategy': best_strategy[0],
                'confidence': best_strategy[1],
                'window': current_window.value,
                'all_scores': strategy_scores,
                'position_multiplier': window_config.position_size_multiplier,
                'risk_level': window_config.risk_level
            }
            
        except Exception as e:
            logger.error(f"Error getting window optimized strategy: {e}")
            return {'strategy': 'error', 'confidence': 0}
    
    def _score_strategy_for_signals(self, strategy: StrategyType, signals: Dict[str, Any]) -> float:
        """Score how well a strategy matches current signals."""
        try:
            # Strategy-signal compatibility matrix
            strategy_signal_weights = {
                StrategyType.RSI_ZSCORE_FADE: {
                    'rsi_zscore': 0.8,
                    'mean_reversion': 0.6,
                    'volume_confirmation': 0.4
                },
                StrategyType.MOMENTUM_CONTINUATION: {
                    'momentum_divergence': 0.8,
                    'volume_price_trend': 0.7,
                    'trend_strength': 0.6
                },
                StrategyType.VWAP_RECLAIM: {
                    'vwap_position': 0.9,
                    'volume_spike': 0.7,
                    'order_flow': 0.5
                },
                StrategyType.SECTOR_ROTATION: {
                    'relative_strength': 0.9,
                    'sector_momentum': 0.8,
                    'correlation': 0.6
                }
            }
            
            weights = strategy_signal_weights.get(strategy, {})
            total_score = 0.0
            total_weight = 0.0
            
            for signal_name, weight in weights.items():
                if signal_name in signals:
                    signal_data = signals[signal_name]
                    if isinstance(signal_data, dict):
                        strength = signal_data.get('strength', 0)
                        confidence = signal_data.get('confidence', 0)
                        signal_score = (strength * confidence) * weight
                        total_score += signal_score
                        total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error scoring strategy {strategy}: {e}")
            return 0.0
    
    @staticmethod
    def calculate_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Simple Moving Average of volume."""
        try:
            return ta.sma(df['volume'], length=period)
        except Exception as e:
            logger.error(f"Error calculating Volume SMA: {e}")
            return pd.Series(dtype=float)
    
    @staticmethod
    def detect_volume_spike(df: pd.DataFrame, multiplier: float = 2.0) -> pd.Series:
        """Detect volume spikes above average."""
        try:
            volume_sma = TechnicalIndicators.calculate_volume_sma(df, 20)
            return df['volume'] > (volume_sma * multiplier)
        except Exception as e:
            logger.error(f"Error detecting volume spikes: {e}")
            return pd.Series(dtype=bool)
    
    @staticmethod
    def detect_vwap_bounce(df: pd.DataFrame, tolerance: float = 0.02) -> Dict[str, Any]:
        """Detect VWAP bounce pattern."""
        try:
            vwap = TechnicalIndicators.calculate_vwap(df)
            current_price = df['close'].iloc[-1]
            current_vwap = vwap.iloc[-1]
            
            if pd.isna(current_vwap):
                return {'is_bounce': False, 'distance': 0}
            
            # Calculate distance from VWAP as percentage
            distance = (current_price - current_vwap) / current_vwap
            
            # Check if price is near VWAP and bouncing up
            near_vwap = abs(distance) <= tolerance
            price_above_vwap = current_price > current_vwap
            
            # Look for recent bounce (price was below VWAP recently)
            recent_below = False
            if len(df) >= 5:
                recent_prices = df['close'].iloc[-5:-1]
                recent_vwap = vwap.iloc[-5:-1]
                recent_below = any(recent_prices < recent_vwap)
            
            is_bounce = near_vwap and price_above_vwap and recent_below
            
            return {
                'is_bounce': is_bounce,
                'distance': distance,
                'current_price': current_price,
                'current_vwap': current_vwap
            }
            
        except Exception as e:
            logger.error(f"Error detecting VWAP bounce: {e}")
            return {'is_bounce': False, 'distance': 0}
    
    @staticmethod
    def detect_macd_bullish_cross(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect MACD bullish crossover."""
        try:
            macd_data = TechnicalIndicators.calculate_macd(df)
            macd = macd_data['macd']
            signal = macd_data['signal']
            
            if len(macd) < 2 or pd.isna(macd.iloc[-1]) or pd.isna(signal.iloc[-1]):
                return {'is_bullish_cross': False, 'macd_value': 0, 'signal_value': 0}
            
            # Current values
            current_macd = macd.iloc[-1]
            current_signal = signal.iloc[-1]
            
            # Previous values
            prev_macd = macd.iloc[-2]
            prev_signal = signal.iloc[-2]
            
            # Bullish cross: MACD crosses above signal line
            bullish_cross = (prev_macd <= prev_signal) and (current_macd > current_signal)
            
            return {
                'is_bullish_cross': bullish_cross,
                'macd_value': current_macd,
                'signal_value': current_signal,
                'histogram': current_macd - current_signal
            }
            
        except Exception as e:
            logger.error(f"Error detecting MACD bullish cross: {e}")
            return {'is_bullish_cross': False, 'macd_value': 0, 'signal_value': 0}
    
    @staticmethod
    def is_rsi_oversold(df: pd.DataFrame, threshold: float = 30) -> Dict[str, Any]:
        """Check if RSI indicates oversold condition."""
        try:
            rsi = TechnicalIndicators.calculate_rsi(df)
            
            if pd.isna(rsi.iloc[-1]):
                return {'is_oversold': False, 'rsi_value': 0}
            
            current_rsi = rsi.iloc[-1]
            is_oversold = current_rsi < threshold
            
            return {
                'is_oversold': is_oversold,
                'rsi_value': current_rsi
            }
            
        except Exception as e:
            logger.error(f"Error checking RSI oversold: {e}")
            return {'is_oversold': False, 'rsi_value': 0}
    
    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
        """Calculate basic support and resistance levels."""
        try:
            if len(df) < window:
                return {'support': 0, 'resistance': 0}
            
            recent_data = df.tail(window)
            support = recent_data['low'].min()
            resistance = recent_data['high'].max()
            
            return {
                'support': support,
                'resistance': resistance
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {'support': 0, 'resistance': 0}
    
    @staticmethod
    def calculate_risk_reward_levels(current_price: float, support: float, 
                                   resistance: float, rr_ratio: float = 2.0) -> Dict[str, float]:
        """Calculate entry, stop loss, and take profit levels."""
        try:
            entry = current_price
            stop_loss = support * 0.99  # Slightly below support
            
            # Calculate take profit based on risk-reward ratio
            risk = entry - stop_loss
            reward = risk * rr_ratio
            take_profit = entry + reward
            
            # Don't let take profit exceed resistance
            if take_profit > resistance:
                take_profit = resistance * 0.99
                # Recalculate actual R:R ratio
                actual_reward = take_profit - entry
                actual_rr = actual_reward / risk if risk > 0 else 0
            else:
                actual_rr = rr_ratio
            
            return {
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk': risk,
                'reward': take_profit - entry,
                'rr_ratio': actual_rr
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk/reward levels: {e}")
            return {'entry': 0, 'stop_loss': 0, 'take_profit': 0, 'risk': 0, 'reward': 0, 'rr_ratio': 0}
    
    @staticmethod
    def analyze_ticker_setup(df: pd.DataFrame, ticker: str) -> Dict[str, Any]:
        """Comprehensive analysis of a ticker for trading setup."""
        try:
            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {ticker}")
                return None
            
            # Calculate all indicators
            rsi_data = TechnicalIndicators.is_rsi_oversold(df)
            vwap_data = TechnicalIndicators.detect_vwap_bounce(df)
            macd_data = TechnicalIndicators.detect_macd_bullish_cross(df)
            volume_spike = TechnicalIndicators.detect_volume_spike(df)
            support_resistance = TechnicalIndicators.calculate_support_resistance(df)
            
            current_price = df['close'].iloc[-1]
            current_volume = df['volume'].iloc[-1]
            avg_volume = TechnicalIndicators.calculate_volume_sma(df, 20).iloc[-1]
            
            # Calculate risk/reward levels
            rr_levels = TechnicalIndicators.calculate_risk_reward_levels(
                current_price, 
                support_resistance['support'], 
                support_resistance['resistance']
            )
            
            # Determine if this is a valid setup
            setup_score = 0
            setup_reasons = []
            
            if rsi_data['is_oversold']:
                setup_score += 2
                setup_reasons.append(f"RSI oversold at {rsi_data['rsi_value']:.1f}")
            
            if vwap_data['is_bounce']:
                setup_score += 3
                setup_reasons.append("VWAP bounce detected")
            
            if macd_data['is_bullish_cross']:
                setup_score += 2
                setup_reasons.append("MACD bullish crossover")
            
            if volume_spike.iloc[-1] if not volume_spike.empty else False:
                setup_score += 1
                setup_reasons.append("Volume spike detected")
            
            # Check minimum R:R ratio
            valid_rr = rr_levels['rr_ratio'] >= 2.0
            if valid_rr:
                setup_score += 1
                setup_reasons.append(f"Good R:R ratio: {rr_levels['rr_ratio']:.1f}")
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'setup_score': setup_score,
                'setup_reasons': setup_reasons,
                'rsi': rsi_data,
                'vwap': vwap_data,
                'macd': macd_data,
                'volume_data': {
                    'current': current_volume,
                    'average': avg_volume,
                    'spike': volume_spike.iloc[-1] if not volume_spike.empty else False
                },
                'support_resistance': support_resistance,
                'risk_reward': rr_levels,
                'timestamp': df.index[-1]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing setup for {ticker}: {e}")
            return None
