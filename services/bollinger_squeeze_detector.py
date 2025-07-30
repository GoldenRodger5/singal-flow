"""
Bollinger Band Squeeze Detector for Signal Flow Trading System.
Identifies volatility contraction patterns that often precede explosive moves.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

class BollingerSqueezeDetector:
    """Detects Bollinger Band squeeze patterns for breakout trading."""
    
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, 
                 keltner_period: int = 20, keltner_multiplier: float = 1.5):
        """
        Initialize Bollinger Band Squeeze detector.
        
        Args:
            bb_period: Period for Bollinger Bands
            bb_std: Standard deviation multiplier for BB
            keltner_period: Period for Keltner Channels
            keltner_multiplier: ATR multiplier for Keltner Channels
        """
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.keltner_period = keltner_period
        self.keltner_multiplier = keltner_multiplier
    
    def detect_squeeze(self, high: List[float], low: List[float], 
                      close: List[float], volume: List[float] = None) -> Dict[str, Any]:
        """
        Detect Bollinger Band squeeze conditions.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume data (optional)
            
        Returns:
            Dictionary with squeeze analysis
        """
        try:
            if len(close) < max(self.bb_period, self.keltner_period):
                return self._default_result()
            
            # Calculate Bollinger Bands
            bb_data = self._calculate_bollinger_bands(close)
            
            # Calculate Keltner Channels
            kc_data = self._calculate_keltner_channels(high, low, close)
            
            # Detect squeeze condition
            squeeze_analysis = self._analyze_squeeze(bb_data, kc_data, close)
            
            # Add volume analysis if available
            if volume:
                volume_analysis = self._analyze_volume_pattern(volume, squeeze_analysis)
                squeeze_analysis.update(volume_analysis)
            
            # Generate signals
            signals = self._generate_squeeze_signals(squeeze_analysis, close)
            squeeze_analysis['signals'] = signals
            
            return squeeze_analysis
            
        except Exception as e:
            logger.error(f"Error detecting Bollinger squeeze: {e}")
            return self._default_result()
    
    def _calculate_bollinger_bands(self, close: List[float]) -> Dict[str, Any]:
        """Calculate Bollinger Bands."""
        try:
            close_array = np.array(close)
            
            # Calculate moving average and standard deviation
            sma = np.convolve(close_array, np.ones(self.bb_period)/self.bb_period, mode='valid')
            
            bb_upper = []
            bb_lower = []
            bb_width = []
            
            for i in range(self.bb_period - 1, len(close_array)):
                period_data = close_array[i - self.bb_period + 1:i + 1]
                std = np.std(period_data)
                sma_value = np.mean(period_data)
                
                upper = sma_value + (self.bb_std * std)
                lower = sma_value - (self.bb_std * std)
                width = upper - lower
                
                bb_upper.append(upper)
                bb_lower.append(lower)
                bb_width.append(width)
            
            return {
                'upper': bb_upper,
                'lower': bb_lower,
                'width': bb_width,
                'current_width': bb_width[-1] if bb_width else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {'upper': [], 'lower': [], 'width': [], 'current_width': 0}
    
    def _calculate_keltner_channels(self, high: List[float], low: List[float], 
                                  close: List[float]) -> Dict[str, Any]:
        """Calculate Keltner Channels using ATR."""
        try:
            # Calculate True Range
            tr_values = []
            for i in range(1, len(close)):
                high_low = high[i] - low[i]
                high_close_prev = abs(high[i] - close[i-1])
                low_close_prev = abs(low[i] - close[i-1])
                tr = max(high_low, high_close_prev, low_close_prev)
                tr_values.append(tr)
            
            if len(tr_values) < self.keltner_period:
                return {'upper': [], 'lower': [], 'width': [], 'current_width': 0}
            
            # Calculate ATR
            atr_values = []
            for i in range(self.keltner_period - 1, len(tr_values)):
                atr = np.mean(tr_values[i - self.keltner_period + 1:i + 1])
                atr_values.append(atr)
            
            # Calculate Keltner Channels
            kc_upper = []
            kc_lower = []
            kc_width = []
            
            close_start_idx = len(close) - len(atr_values)
            
            for i, atr in enumerate(atr_values):
                close_idx = close_start_idx + i
                if close_idx < len(close):
                    # EMA of close (simplified as SMA for this implementation)
                    ema_period = min(self.keltner_period, close_idx + 1)
                    ema = np.mean(close[close_idx - ema_period + 1:close_idx + 1])
                    
                    upper = ema + (self.keltner_multiplier * atr)
                    lower = ema - (self.keltner_multiplier * atr)
                    width = upper - lower
                    
                    kc_upper.append(upper)
                    kc_lower.append(lower)
                    kc_width.append(width)
            
            return {
                'upper': kc_upper,
                'lower': kc_lower,
                'width': kc_width,
                'current_width': kc_width[-1] if kc_width else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating Keltner Channels: {e}")
            return {'upper': [], 'lower': [], 'width': [], 'current_width': 0}
    
    def _analyze_squeeze(self, bb_data: Dict, kc_data: Dict, close: List[float]) -> Dict[str, Any]:
        """Analyze squeeze conditions."""
        try:
            bb_width = bb_data.get('current_width', 0)
            kc_width = kc_data.get('current_width', 0)
            
            # Squeeze occurs when Bollinger Bands are inside Keltner Channels
            in_squeeze = bb_width < kc_width if kc_width > 0 else False
            
            # Calculate squeeze intensity
            squeeze_intensity = self._calculate_squeeze_intensity(bb_data, kc_data)
            
            # Calculate volatility percentile
            volatility_percentile = self._calculate_volatility_percentile(bb_data['width']) if bb_data['width'] else 50
            
            # Determine squeeze duration
            squeeze_duration = self._calculate_squeeze_duration(bb_data, kc_data)
            
            # Detect potential breakout direction
            breakout_direction = self._detect_breakout_direction(close, bb_data, kc_data)
            
            return {
                'in_squeeze': in_squeeze,
                'squeeze_intensity': squeeze_intensity,
                'volatility_percentile': volatility_percentile,
                'squeeze_duration': squeeze_duration,
                'breakout_direction': breakout_direction,
                'bb_width': bb_width,
                'kc_width': kc_width,
                'squeeze_strength': self._calculate_squeeze_strength(squeeze_intensity, squeeze_duration, volatility_percentile)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing squeeze: {e}")
            return self._default_squeeze_analysis()
    
    def _calculate_squeeze_intensity(self, bb_data: Dict, kc_data: Dict) -> float:
        """Calculate how tight the squeeze is (0-10 scale)."""
        try:
            bb_width = bb_data.get('current_width', 0)
            kc_width = kc_data.get('current_width', 0)
            
            if kc_width <= 0:
                return 0
            
            # Ratio of BB width to KC width
            ratio = bb_width / kc_width
            
            # Convert to 0-10 scale (lower ratio = higher intensity)
            intensity = (1 - ratio) * 10
            return max(0, min(10, intensity))
            
        except Exception:
            return 0
    
    def _calculate_volatility_percentile(self, bb_widths: List[float]) -> float:
        """Calculate current volatility percentile."""
        try:
            if len(bb_widths) < 20:
                return 50  # Default to median
            
            current_width = bb_widths[-1]
            recent_widths = bb_widths[-50:] if len(bb_widths) >= 50 else bb_widths
            
            percentile = (sum(1 for w in recent_widths if w <= current_width) / len(recent_widths)) * 100
            return percentile
            
        except Exception:
            return 50
    
    def _calculate_squeeze_duration(self, bb_data: Dict, kc_data: Dict) -> int:
        """Calculate how long the squeeze has been active."""
        try:
            bb_widths = bb_data.get('width', [])
            kc_widths = kc_data.get('width', [])
            
            if len(bb_widths) != len(kc_widths) or len(bb_widths) == 0:
                return 0
            
            duration = 0
            for i in range(len(bb_widths) - 1, -1, -1):
                if bb_widths[i] < kc_widths[i]:
                    duration += 1
                else:
                    break
            
            return duration
            
        except Exception:
            return 0
    
    def _detect_breakout_direction(self, close: List[float], bb_data: Dict, kc_data: Dict) -> str:
        """Detect potential breakout direction."""
        try:
            if len(close) < 5:
                return 'neutral'
            
            # Simple momentum-based direction detection
            recent_prices = close[-5:]
            price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            # Check position relative to middle of bands
            bb_upper = bb_data.get('upper', [])
            bb_lower = bb_data.get('lower', [])
            
            if bb_upper and bb_lower:
                current_price = close[-1]
                bb_middle = (bb_upper[-1] + bb_lower[-1]) / 2
                
                if current_price > bb_middle and price_momentum > 0.01:  # 1% momentum
                    return 'bullish'
                elif current_price < bb_middle and price_momentum < -0.01:
                    return 'bearish'
            
            return 'neutral'
            
        except Exception:
            return 'neutral'
    
    def _calculate_squeeze_strength(self, intensity: float, duration: int, volatility_percentile: float) -> float:
        """Calculate overall squeeze strength (0-10 scale)."""
        try:
            # Base strength from intensity
            strength = intensity * 0.4  # 40% weight
            
            # Duration bonus (longer squeeze = more potential energy)
            duration_bonus = min(duration * 0.2, 3.0)  # Up to 3 points
            strength += duration_bonus
            
            # Low volatility bonus
            if volatility_percentile < 20:  # Very low volatility
                strength += 2.0
            elif volatility_percentile < 40:  # Low volatility
                strength += 1.0
            
            return max(0, min(10, strength))
            
        except Exception:
            return 0
    
    def _analyze_volume_pattern(self, volume: List[float], squeeze_data: Dict) -> Dict[str, Any]:
        """Analyze volume patterns during squeeze."""
        try:
            if len(volume) < 10:
                return {'volume_pattern': 'insufficient_data', 'volume_confirmation': False}
            
            recent_volume = volume[-5:]
            historical_volume = volume[-20:-5] if len(volume) >= 20 else volume[:-5]
            
            avg_recent = np.mean(recent_volume)
            avg_historical = np.mean(historical_volume)
            
            volume_ratio = avg_recent / avg_historical if avg_historical > 0 else 1
            
            # Determine volume pattern
            if volume_ratio > 1.5:
                pattern = 'expanding'
                confirmation = True
            elif volume_ratio < 0.7:
                pattern = 'contracting'
                confirmation = squeeze_data.get('in_squeeze', False)  # Good for squeeze
            else:
                pattern = 'neutral'
                confirmation = False
            
            return {
                'volume_pattern': pattern,
                'volume_ratio': volume_ratio,
                'volume_confirmation': confirmation
            }
            
        except Exception:
            return {'volume_pattern': 'error', 'volume_confirmation': False}
    
    def _generate_squeeze_signals(self, squeeze_data: Dict, close: List[float]) -> List[str]:
        """Generate trading signals based on squeeze analysis."""
        signals = []
        
        try:
            if squeeze_data.get('in_squeeze', False):
                strength = squeeze_data.get('squeeze_strength', 0)
                duration = squeeze_data.get('squeeze_duration', 0)
                
                signals.append(f"Bollinger Squeeze Active (Strength: {strength:.1f})")
                
                if duration >= 5:
                    signals.append(f"Extended Squeeze ({duration} periods)")
                
                if strength >= 7:
                    signals.append("High-Tension Squeeze")
                
                # Breakout alerts
                direction = squeeze_data.get('breakout_direction', 'neutral')
                if direction != 'neutral':
                    signals.append(f"Potential {direction.title()} Breakout Setup")
                
                # Volume confirmation
                if squeeze_data.get('volume_confirmation', False):
                    signals.append("Volume Confirms Squeeze")
            
            else:
                # Check for recent breakout
                if len(close) >= 2:
                    signals.append("No Active Squeeze")
            
        except Exception as e:
            logger.error(f"Error generating squeeze signals: {e}")
        
        return signals
    
    def is_breakout_setup(self, squeeze_data: Dict[str, Any], min_strength: float = 6.0) -> bool:
        """
        Determine if current conditions indicate a high-probability breakout setup.
        
        Args:
            squeeze_data: Squeeze analysis results
            min_strength: Minimum squeeze strength required
            
        Returns:
            True if breakout setup detected
        """
        try:
            # Must be in active squeeze
            if not squeeze_data.get('in_squeeze', False):
                return False
            
            # Require minimum strength
            strength = squeeze_data.get('squeeze_strength', 0)
            if strength < min_strength:
                return False
            
            # Prefer longer duration squeezes
            duration = squeeze_data.get('squeeze_duration', 0)
            if duration < 3:
                return False
            
            # Low volatility environment preferred
            vol_percentile = squeeze_data.get('volatility_percentile', 50)
            if vol_percentile > 60:  # High volatility already
                return False
            
            # Volume confirmation helps
            volume_confirmation = squeeze_data.get('volume_confirmation', False)
            
            # Direction bias helps
            direction = squeeze_data.get('breakout_direction', 'neutral')
            
            # Calculate overall probability
            base_prob = strength / 10  # Base probability from strength
            
            if duration >= 7:
                base_prob += 0.2  # Bonus for extended squeeze
            
            if vol_percentile < 30:
                base_prob += 0.1  # Bonus for very low volatility
            
            if volume_confirmation:
                base_prob += 0.1  # Volume confirmation bonus
            
            if direction != 'neutral':
                base_prob += 0.1  # Directional bias bonus
            
            return base_prob >= 0.7  # 70% probability threshold
            
        except Exception as e:
            logger.error(f"Error checking breakout setup: {e}")
            return False
    
    def _default_result(self) -> Dict[str, Any]:
        """Return default result when calculation fails."""
        return {
            'in_squeeze': False,
            'squeeze_intensity': 0,
            'volatility_percentile': 50,
            'squeeze_duration': 0,
            'breakout_direction': 'neutral',
            'bb_width': 0,
            'kc_width': 0,
            'squeeze_strength': 0,
            'signals': [],
            'volume_pattern': 'unknown',
            'volume_confirmation': False
        }
    
    def _default_squeeze_analysis(self) -> Dict[str, Any]:
        """Return default squeeze analysis."""
        return {
            'in_squeeze': False,
            'squeeze_intensity': 0,
            'volatility_percentile': 50,
            'squeeze_duration': 0,
            'breakout_direction': 'neutral',
            'bb_width': 0,
            'kc_width': 0,
            'squeeze_strength': 0
        }
