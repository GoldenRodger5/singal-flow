"""
Momentum Multiplier Service for Signal Flow Trading System.
Identifies explosive momentum opportunities in low-cap stocks.
"""
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime, timedelta

class MomentumMultiplier:
    """Detects and scores explosive momentum opportunities."""
    
    def __init__(self):
        """Initialize momentum multiplier service."""
        self.min_momentum_score = 6.0  # Lowered threshold for more signals
        self.volume_spike_threshold = 3.0  # 3x average volume (more sensitive)
        self.price_acceleration_threshold = 0.10  # 10% acceleration
    
    def calculate_momentum_multiplier(self, price_data: Dict[str, Any], volume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate momentum multiplier score for explosive potential.
        
        Returns:
            Dictionary with momentum analysis and multiplier
        """
        try:
            closes = price_data.get('closes', [])
            volumes = volume_data.get('volumes', [])
            
            if len(closes) < 10 or len(volumes) < 10:
                return self._default_multiplier()
            
            # Calculate price acceleration
            price_acceleration = self._calculate_price_acceleration(closes)
            
            # Calculate volume surge strength
            volume_surge = self._calculate_volume_surge(volumes)
            
            # Calculate momentum persistence
            momentum_persistence = self._calculate_momentum_persistence(closes)
            
            # Calculate breakout confirmation
            breakout_strength = self._calculate_breakout_confirmation(closes, volumes)
            
            # Composite momentum multiplier (1-10 scale)
            multiplier = (
                price_acceleration * 0.40 +  # Increased weight for price moves
                volume_surge * 0.30 +        # Slightly reduced volume weight
                momentum_persistence * 0.20 +
                breakout_strength * 0.10     # Reduced breakout weight
            )
            
            # Apply low-cap specific boosts
            current_price = closes[-1]
            if current_price <= 1.0:
                multiplier *= 1.35  # 35% boost for penny stocks
            elif current_price <= 3.0:
                multiplier *= 1.25  # 25% boost for sub-$3 stocks
            elif current_price <= 5.0:
                multiplier *= 1.15  # 15% boost for sub-$5 stocks
            
            return {
                'momentum_multiplier': min(10.0, multiplier),
                'price_acceleration': price_acceleration,
                'volume_surge': volume_surge,
                'momentum_persistence': momentum_persistence,
                'breakout_strength': breakout_strength,
                'explosive_potential': multiplier >= self.min_momentum_score,
                'recommended_hold_time': self._calculate_hold_time(multiplier),
                'profit_target_adjustment': self._calculate_profit_adjustment(multiplier)
            }
            
        except Exception as e:
            logger.error(f"Error calculating momentum multiplier: {e}")
            return self._default_multiplier()
    
    def _calculate_price_acceleration(self, closes: List[float]) -> float:
        """Calculate price acceleration score (0-10)."""
        try:
            if len(closes) < 5:
                return 0.0
            
            # Calculate overall move vs time
            total_change = (closes[-1] / closes[0] - 1) * 100
            days = len(closes) - 1
            daily_avg_change = total_change / days if days > 0 else 0
            
            # Also check recent acceleration
            if len(closes) >= 6:
                recent_change = (closes[-1] / closes[-4] - 1) * 100  # Last 3 days
                previous_change = (closes[-4] / closes[-7] - 1) * 100 if len(closes) >= 7 else daily_avg_change
                acceleration = recent_change - previous_change
            else:
                acceleration = daily_avg_change
            
            # Score based on total move and acceleration
            score = 0.0
            
            # Points for total move
            if total_change >= 50:  # 50%+ total move
                score += 5.0
            elif total_change >= 25:  # 25%+ move
                score += 3.0
            elif total_change >= 10:  # 10%+ move
                score += 1.0
            
            # Points for acceleration
            if acceleration >= 15:
                score += 5.0
            elif acceleration >= 10:
                score += 3.0
            elif acceleration >= 5:
                score += 2.0
            elif acceleration >= 2:
                score += 1.0
            
            return min(10.0, score)
                
        except Exception:
            return 0.0
    
    def _calculate_volume_surge(self, volumes: List[float]) -> float:
        """Calculate volume surge strength (0-10)."""
        try:
            if len(volumes) < 10:
                return 0.0
            
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[-20:-1]) if len(volumes) >= 20 else np.mean(volumes[:-1])
            
            if avg_volume == 0:
                return 0.0
            
            volume_ratio = current_volume / avg_volume
            
            # Score based on volume surge
            if volume_ratio >= 10:
                return 10.0
            elif volume_ratio >= 5:
                return 8.5
            elif volume_ratio >= 3:
                return 7.0
            elif volume_ratio >= 2:
                return 5.0
            else:
                return max(0.0, volume_ratio * 2.5)
                
        except Exception:
            return 0.0
    
    def _calculate_momentum_persistence(self, closes: List[float]) -> float:
        """Calculate how persistent the momentum is (0-10)."""
        try:
            if len(closes) < 5:
                return 0.0
            
            # Count consecutive up days
            up_days = 0
            for i in range(len(closes) - 1, 0, -1):
                if closes[i] > closes[i-1]:
                    up_days += 1
                else:
                    break
            
            # Higher score for more consecutive days
            persistence_score = min(10.0, up_days * 2.5)
            
            # Bonus for strong daily moves
            recent_moves = []
            for i in range(max(1, len(closes) - 5), len(closes)):
                if i > 0:
                    daily_change = (closes[i] / closes[i-1] - 1) * 100
                    recent_moves.append(daily_change)
            
            if recent_moves:
                avg_move = np.mean([m for m in recent_moves if m > 0])
                if avg_move >= 5:  # Average 5%+ moves
                    persistence_score *= 1.2
            
            return min(10.0, persistence_score)
            
        except Exception:
            return 0.0
    
    def _calculate_breakout_confirmation(self, closes: List[float], volumes: List[float]) -> float:
        """Calculate breakout confirmation strength (0-10)."""
        try:
            if len(closes) < 20 or len(volumes) < 20:
                return 0.0
            
            current_price = closes[-1]
            
            # Check if breaking resistance levels
            resistance_levels = []
            for i in range(5, min(20, len(closes))):
                high_period = max(closes[-i-5:-i])
                resistance_levels.append(high_period)
            
            if not resistance_levels:
                return 0.0
            
            avg_resistance = np.mean(resistance_levels)
            
            # Score based on how much above resistance
            if current_price > avg_resistance:
                breakout_strength = ((current_price / avg_resistance) - 1) * 100
                if breakout_strength >= 10:
                    return 10.0
                elif breakout_strength >= 5:
                    return 8.0
                elif breakout_strength >= 2:
                    return 6.0
                else:
                    return max(0.0, breakout_strength * 2)
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _calculate_hold_time(self, multiplier: float) -> str:
        """Calculate recommended hold time based on momentum."""
        if multiplier >= 9:
            return "2-3 days"  # Explosive moves are short-lived
        elif multiplier >= 7:
            return "3-5 days"
        elif multiplier >= 5:
            return "5-10 days"
        else:
            return "10+ days"
    
    def _calculate_profit_adjustment(self, multiplier: float) -> float:
        """Calculate profit target adjustment multiplier."""
        if multiplier >= 9:
            return 2.0  # Double profit targets for explosive moves
        elif multiplier >= 7:
            return 1.5
        elif multiplier >= 5:
            return 1.25
        else:
            return 1.0
    
    def _default_multiplier(self) -> Dict[str, Any]:
        """Return default multiplier values."""
        return {
            'momentum_multiplier': 0.0,
            'price_acceleration': 0.0,
            'volume_surge': 0.0,
            'momentum_persistence': 0.0,
            'breakout_strength': 0.0,
            'explosive_potential': False,
            'recommended_hold_time': "10+ days",
            'profit_target_adjustment': 1.0
        }
