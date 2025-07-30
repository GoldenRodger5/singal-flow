"""
Williams %R Indicator for Signal Flow Trading System.
More sensitive than RSI for momentum detection in low-cap stocks.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from loguru import logger

class WilliamsRIndicator:
    """Williams %R oscillator for momentum detection."""
    
    def __init__(self, period: int = 14, overbought: float = -20, oversold: float = -80):
        """
        Initialize Williams %R indicator.
        
        Args:
            period: Lookback period (default 14)
            overbought: Overbought threshold (default -20)
            oversold: Oversold threshold (default -80)
        """
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def calculate(self, high: List[float], low: List[float], close: List[float]) -> Dict[str, Any]:
        """
        Calculate Williams %R and generate signals.
        
        Args:
            high: High prices
            low: Low prices  
            close: Close prices
            
        Returns:
            Dictionary with Williams %R data and signals
        """
        try:
            if len(high) < self.period or len(low) < self.period or len(close) < self.period:
                return self._default_result()
            
            # Convert to numpy arrays
            high_array = np.array(high)
            low_array = np.array(low)
            close_array = np.array(close)
            
            # Calculate Williams %R
            williams_r_values = []
            
            for i in range(self.period - 1, len(close_array)):
                period_high = np.max(high_array[i - self.period + 1:i + 1])
                period_low = np.min(low_array[i - self.period + 1:i + 1])
                current_close = close_array[i]
                
                if period_high == period_low:
                    williams_r = -50  # Neutral when no range
                else:
                    williams_r = ((period_high - current_close) / (period_high - period_low)) * -100
                
                williams_r_values.append(williams_r)
            
            if not williams_r_values:
                return self._default_result()
            
            current_wr = williams_r_values[-1]
            
            # Generate signals
            signals = self._generate_signals(williams_r_values, current_wr)
            
            # Calculate momentum strength
            momentum_strength = self._calculate_momentum_strength(williams_r_values)
            
            return {
                'williams_r': current_wr,
                'is_oversold': current_wr <= self.oversold,
                'is_overbought': current_wr >= self.overbought,
                'momentum_strength': momentum_strength,
                'signals': signals,
                'trend_direction': self._determine_trend(williams_r_values),
                'reversal_probability': self._calculate_reversal_probability(williams_r_values),
                'values_history': williams_r_values[-10:] if len(williams_r_values) >= 10 else williams_r_values
            }
            
        except Exception as e:
            logger.error(f"Error calculating Williams %R: {e}")
            return self._default_result()
    
    def _generate_signals(self, williams_r_values: List[float], current_wr: float) -> List[str]:
        """Generate trading signals based on Williams %R."""
        signals = []
        
        try:
            # Oversold bounce signal
            if current_wr <= self.oversold:
                signals.append(f"Williams %R Oversold ({current_wr:.1f})")
                
                # Check for potential reversal
                if len(williams_r_values) >= 3:
                    recent_values = williams_r_values[-3:]
                    if recent_values[-1] > recent_values[-2]:  # Starting to turn up
                        signals.append("Williams %R Reversal Signal")
            
            # Overbought warning
            elif current_wr >= self.overbought:
                signals.append(f"Williams %R Overbought ({current_wr:.1f})")
            
            # Momentum signals
            if len(williams_r_values) >= 5:
                recent_trend = self._calculate_recent_trend(williams_r_values[-5:])
                if recent_trend > 10:  # Strong upward momentum
                    signals.append("Williams %R Strong Momentum")
                elif recent_trend < -10:  # Strong downward momentum
                    signals.append("Williams %R Momentum Decline")
            
            # Divergence detection
            if len(williams_r_values) >= 10:
                divergence = self._detect_divergence(williams_r_values[-10:])
                if divergence:
                    signals.append(f"Williams %R {divergence}")
            
        except Exception as e:
            logger.error(f"Error generating Williams %R signals: {e}")
        
        return signals
    
    def _calculate_momentum_strength(self, williams_r_values: List[float]) -> float:
        """Calculate momentum strength (0-10 scale)."""
        try:
            if len(williams_r_values) < 5:
                return 5.0
            
            current_wr = williams_r_values[-1]
            recent_avg = np.mean(williams_r_values[-5:])
            
            # Base strength on distance from neutral (-50)
            distance_from_neutral = abs(current_wr + 50)
            base_strength = min(distance_from_neutral / 5, 10)  # Scale to 0-10
            
            # Adjust for trend consistency
            if len(williams_r_values) >= 3:
                trend_consistency = self._calculate_trend_consistency(williams_r_values[-5:])
                base_strength *= (1 + trend_consistency * 0.2)  # Up to 20% boost
            
            return min(max(base_strength, 0), 10)
            
        except Exception:
            return 5.0
    
    def _determine_trend(self, williams_r_values: List[float]) -> str:
        """Determine the overall trend direction."""
        try:
            if len(williams_r_values) < 3:
                return 'neutral'
            
            recent_trend = self._calculate_recent_trend(williams_r_values[-5:])
            
            if recent_trend > 5:
                return 'bullish'
            elif recent_trend < -5:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def _calculate_reversal_probability(self, williams_r_values: List[float]) -> float:
        """Calculate probability of trend reversal (0-1 scale)."""
        try:
            if len(williams_r_values) < 5:
                return 0.5
            
            current_wr = williams_r_values[-1]
            
            # Higher probability at extremes
            if current_wr <= -90:  # Very oversold
                return 0.8
            elif current_wr <= self.oversold:  # Oversold
                return 0.7
            elif current_wr >= -10:  # Very overbought
                return 0.8
            elif current_wr >= self.overbought:  # Overbought
                return 0.7
            else:
                return 0.3  # Low reversal probability in middle range
                
        except Exception:
            return 0.5
    
    def _calculate_recent_trend(self, values: List[float]) -> float:
        """Calculate recent trend direction and strength."""
        try:
            if len(values) < 2:
                return 0
            
            # Simple slope calculation
            x = np.arange(len(values))
            y = np.array(values)
            slope = np.polyfit(x, y, 1)[0]
            
            return slope * len(values)  # Scale by period
            
        except Exception:
            return 0
    
    def _calculate_trend_consistency(self, values: List[float]) -> float:
        """Calculate how consistent the trend is (0-1 scale)."""
        try:
            if len(values) < 3:
                return 0
            
            # Count directional changes
            changes = 0
            for i in range(1, len(values)):
                if i > 1:
                    prev_direction = values[i-1] - values[i-2]
                    curr_direction = values[i] - values[i-1]
                    if (prev_direction > 0) != (curr_direction > 0):
                        changes += 1
            
            # More changes = less consistent
            max_possible_changes = len(values) - 2
            if max_possible_changes <= 0:
                return 1
            
            consistency = 1 - (changes / max_possible_changes)
            return max(0, consistency)
            
        except Exception:
            return 0
    
    def _detect_divergence(self, williams_r_values: List[float]) -> Optional[str]:
        """Detect potential divergence patterns."""
        try:
            if len(williams_r_values) < 6:
                return None
            
            # Simple divergence detection
            first_half = williams_r_values[:len(williams_r_values)//2]
            second_half = williams_r_values[len(williams_r_values)//2:]
            
            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)
            
            difference = second_avg - first_avg
            
            if difference > 15:
                return "Bullish Divergence"
            elif difference < -15:
                return "Bearish Divergence"
            
            return None
            
        except Exception:
            return None
    
    def _default_result(self) -> Dict[str, Any]:
        """Return default result when calculation fails."""
        return {
            'williams_r': -50,
            'is_oversold': False,
            'is_overbought': False,
            'momentum_strength': 5.0,
            'signals': [],
            'trend_direction': 'neutral',
            'reversal_probability': 0.5,
            'values_history': []
        }
    
    def is_momentum_signal(self, williams_r_data: Dict[str, Any], volume_confirmation: bool = False) -> bool:
        """
        Determine if current Williams %R setup indicates a momentum opportunity.
        
        Args:
            williams_r_data: Williams %R calculation result
            volume_confirmation: Whether volume confirms the signal
            
        Returns:
            True if momentum signal detected
        """
        try:
            # Require oversold condition for momentum entry
            if not williams_r_data.get('is_oversold', False):
                return False
            
            # Check momentum strength
            momentum_strength = williams_r_data.get('momentum_strength', 0)
            if momentum_strength < 6.0:  # Require decent momentum
                return False
            
            # Check for reversal probability
            reversal_prob = williams_r_data.get('reversal_probability', 0)
            if reversal_prob < 0.6:  # Require good reversal probability
                return False
            
            # Volume confirmation bonus
            if volume_confirmation:
                return True
            
            # Without volume confirmation, require higher standards
            return momentum_strength >= 7.0 and reversal_prob >= 0.7
            
        except Exception as e:
            logger.error(f"Error checking Williams %R momentum signal: {e}")
            return False
