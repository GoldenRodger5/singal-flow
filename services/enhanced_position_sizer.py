"""
Enhanced Position Sizing Service for Signal Flow Trading System.
Implements volatility-scaled position sizing, Kelly Criterion, and correlation adjustments.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class PositionSizeResult:
    """Container for position sizing results."""
    position_size: float  # Dollar amount
    position_percentage: float  # Percentage of portfolio
    risk_per_trade: float  # Dollar risk amount
    kelly_fraction: float  # Kelly Criterion fraction
    volatility_adjustment: float  # Volatility scaling factor
    confidence_adjustment: float  # Confidence-based adjustment
    max_position_limit: float  # Maximum allowed position
    reasoning: str  # Explanation of sizing decision

class EnhancedPositionSizer:
    """Enhanced position sizing with multiple risk management techniques."""
    
    def __init__(self, config, regime_detector=None):
        self.config = config
        self.regime_detector = regime_detector
        self.position_history_file = "data/position_history.json"
        self.position_history = []
        
        # Risk management parameters
        self.max_portfolio_risk = 0.02  # 2% portfolio risk per trade
        self.max_position_size = 0.15   # 15% max position size
        self.max_sector_exposure = 0.30  # 30% max sector exposure
        self.volatility_target = config.MAX_PORTFOLIO_VOLATILITY if hasattr(config, 'MAX_PORTFOLIO_VOLATILITY') else 0.15
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Load position history
        self._load_position_history()
    
    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float,
                              confidence: float, technical_signals: Dict[str, Any],
                              portfolio_value: float, current_positions: List[Dict] = None) -> PositionSizeResult:
        """
        Calculate optimal position size using multiple methods.
        
        Args:
            symbol: Stock symbol
            entry_price: Planned entry price
            stop_loss: Stop loss price
            confidence: Signal confidence (0-10)
            technical_signals: Technical analysis signals
            portfolio_value: Current portfolio value
            current_positions: List of current positions
            
        Returns:
            PositionSizeResult with sizing recommendation
        """
        try:
            # Calculate base risk parameters
            price_risk = abs(entry_price - stop_loss)
            risk_per_share = price_risk
            risk_percentage = risk_per_share / entry_price
            
            # Get market regime for volatility adjustment
            volatility_adjustment = self._calculate_volatility_adjustment(symbol, technical_signals)
            
            # Calculate Kelly Criterion sizing
            kelly_fraction = self._calculate_kelly_fraction(confidence, risk_percentage, technical_signals)
            
            # Calculate confidence-based adjustment
            confidence_adjustment = self._calculate_confidence_adjustment(confidence)
            
            # Calculate correlation adjustment
            correlation_adjustment = self._calculate_correlation_adjustment(symbol, current_positions)
            
            # Base position size using portfolio risk
            base_risk_amount = portfolio_value * self.max_portfolio_risk
            base_position_shares = base_risk_amount / risk_per_share
            base_position_value = base_position_shares * entry_price
            
            # Apply Kelly Criterion
            kelly_position_value = portfolio_value * kelly_fraction
            
            # Apply adjustments
            adjusted_position_value = min(base_position_value, kelly_position_value)
            adjusted_position_value *= volatility_adjustment
            adjusted_position_value *= confidence_adjustment
            adjusted_position_value *= correlation_adjustment
            
            # Apply maximum position limits
            max_position_value = portfolio_value * self.max_position_size
            final_position_value = min(adjusted_position_value, max_position_value)
            
            # Ensure minimum trade size
            min_trade_value = 1000  # $1000 minimum
            if final_position_value < min_trade_value:
                final_position_value = 0
                reasoning = f"Position too small (${final_position_value:.0f} < ${min_trade_value})"
            else:
                reasoning = self._generate_sizing_reasoning(
                    base_position_value, kelly_position_value, volatility_adjustment,
                    confidence_adjustment, correlation_adjustment, final_position_value
                )
            
            # Calculate final metrics
            final_shares = final_position_value / entry_price if final_position_value > 0 else 0
            risk_amount = final_shares * risk_per_share
            position_percentage = final_position_value / portfolio_value
            
            result = PositionSizeResult(
                position_size=final_position_value,
                position_percentage=position_percentage,
                risk_per_trade=risk_amount,
                kelly_fraction=kelly_fraction,
                volatility_adjustment=volatility_adjustment,
                confidence_adjustment=confidence_adjustment,
                max_position_limit=max_position_value,
                reasoning=reasoning
            )
            
            # Log the sizing decision
            self._log_sizing_decision(symbol, result, technical_signals)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self._get_default_position_size(portfolio_value)
    
    def _calculate_volatility_adjustment(self, symbol: str, technical_signals: Dict[str, Any]) -> float:
        """Calculate position size adjustment based on volatility."""
        try:
            # Get volatility from technical signals or use default
            if 'volatility' in technical_signals:
                current_vol = technical_signals['volatility']
            else:
                # Estimate from price data if available
                current_vol = 0.25  # Default assumption
            
            # Get regime-based volatility adjustment
            if self.regime_detector and self.regime_detector.current_regime:
                regime = self.regime_detector.current_regime
                vol_percentile = regime.volatility_percentile
                
                # Reduce position size in high volatility
                if vol_percentile > 0.8:  # High volatility
                    vol_adjustment = 0.7
                elif vol_percentile > 0.6:  # Medium-high volatility
                    vol_adjustment = 0.85
                elif vol_percentile < 0.2:  # Low volatility
                    vol_adjustment = 1.15
                else:  # Normal volatility
                    vol_adjustment = 1.0
            else:
                # Simple volatility scaling
                target_vol = self.volatility_target
                vol_adjustment = min(1.5, max(0.5, target_vol / current_vol))
            
            return vol_adjustment
            
        except Exception as e:
            logger.warning(f"Error calculating volatility adjustment: {e}")
            return 1.0
    
    def _calculate_kelly_fraction(self, confidence: float, risk_percentage: float, 
                                technical_signals: Dict[str, Any]) -> float:
        """Calculate Kelly Criterion fraction."""
        try:
            # Convert confidence to win probability
            # Confidence 10 = 80% win rate, Confidence 5 = 50% win rate
            win_probability = 0.3 + (confidence / 10.0) * 0.5
            
            # Estimate win/loss ratio from technical signals
            # Strong signals suggest better risk/reward
            signal_strength = technical_signals.get('composite_strength', 0.5)
            base_win_loss_ratio = 1.5  # Base 1.5:1 ratio
            adjusted_ratio = base_win_loss_ratio * (1 + signal_strength * 0.5)
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds (win/loss ratio), p = win probability, q = loss probability
            kelly_fraction = (adjusted_ratio * win_probability - (1 - win_probability)) / adjusted_ratio
            
            # Cap Kelly at reasonable levels
            kelly_fraction = max(0.0, min(0.25, kelly_fraction))  # Max 25% of portfolio
            
            return kelly_fraction
            
        except Exception as e:
            logger.warning(f"Error calculating Kelly fraction: {e}")
            return 0.05  # Conservative default
    
    def _calculate_confidence_adjustment(self, confidence: float) -> float:
        """Calculate position size adjustment based on signal confidence."""
        # Normalize confidence to 0-1 scale
        normalized_confidence = confidence / 10.0
        
        # Conservative scaling: high confidence allows larger positions
        if normalized_confidence >= 0.8:
            return 1.2  # 20% increase for very high confidence
        elif normalized_confidence >= 0.7:
            return 1.1  # 10% increase for high confidence
        elif normalized_confidence >= 0.6:
            return 1.0  # Normal sizing for medium confidence
        elif normalized_confidence >= 0.5:
            return 0.8  # 20% reduction for low confidence
        else:
            return 0.6  # 40% reduction for very low confidence
    
    def _calculate_correlation_adjustment(self, symbol: str, current_positions: List[Dict] = None) -> float:
        """Calculate position size adjustment based on portfolio correlation."""
        try:
            if not current_positions:
                return 1.0
            
            # Simple sector-based correlation proxy
            # In production, you'd use actual correlation calculations
            
            # Check for sector concentration
            sector_exposure = 0.0
            same_sector_positions = 0
            
            for position in current_positions:
                if position.get('symbol') == symbol:
                    continue  # Skip same symbol
                
                # Simple sector detection (would need actual sector data)
                if self._is_same_sector(symbol, position.get('symbol', '')):
                    sector_exposure += position.get('position_value', 0)
                    same_sector_positions += 1
            
            # Reduce position size if sector is overweight
            total_portfolio_value = sum(p.get('position_value', 0) for p in current_positions)
            if total_portfolio_value > 0:
                sector_percentage = sector_exposure / total_portfolio_value
                
                if sector_percentage > self.max_sector_exposure:
                    return 0.5  # Significantly reduce position
                elif sector_percentage > 0.2:
                    return 0.8  # Moderately reduce position
                elif same_sector_positions >= 3:
                    return 0.9  # Slightly reduce for many similar positions
            
            return 1.0
            
        except Exception as e:
            logger.warning(f"Error calculating correlation adjustment: {e}")
            return 1.0
    
    def _is_same_sector(self, symbol1: str, symbol2: str) -> bool:
        """
        Simple sector detection based on symbol patterns.
        In production, you'd use actual sector classification data.
        """
        # Tech stocks patterns
        tech_patterns = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX']
        financial_patterns = ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS']
        
        tech1 = any(pattern in symbol1 for pattern in tech_patterns)
        tech2 = any(pattern in symbol2 for pattern in tech_patterns)
        
        financial1 = any(pattern in symbol1 for pattern in financial_patterns)
        financial2 = any(pattern in symbol2 for pattern in financial_patterns)
        
        return (tech1 and tech2) or (financial1 and financial2)
    
    def calculate_portfolio_risk_metrics(self, current_positions: List[Dict], 
                                       portfolio_value: float) -> Dict[str, float]:
        """Calculate current portfolio risk metrics."""
        try:
            total_risk = 0.0
            total_exposure = 0.0
            position_count = len(current_positions)
            
            for position in current_positions:
                position_value = position.get('position_value', 0)
                position_risk = position.get('risk_amount', 0)
                
                total_exposure += position_value
                total_risk += position_risk
            
            portfolio_risk_percentage = total_risk / portfolio_value if portfolio_value > 0 else 0
            portfolio_exposure_percentage = total_exposure / portfolio_value if portfolio_value > 0 else 0
            
            # Calculate concentration risk
            if current_positions:
                position_values = [p.get('position_value', 0) for p in current_positions]
                largest_position = max(position_values) if position_values else 0
                concentration_risk = largest_position / portfolio_value if portfolio_value > 0 else 0
            else:
                concentration_risk = 0
            
            return {
                'total_risk_percentage': portfolio_risk_percentage,
                'total_exposure_percentage': portfolio_exposure_percentage,
                'position_count': position_count,
                'concentration_risk': concentration_risk,
                'average_position_size': total_exposure / position_count if position_count > 0 else 0,
                'risk_per_position': total_risk / position_count if position_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk metrics: {e}")
            return {}
    
    def get_position_sizing_recommendations(self, portfolio_metrics: Dict[str, float]) -> List[str]:
        """Get position sizing recommendations based on current portfolio state."""
        recommendations = []
        
        try:
            risk_percentage = portfolio_metrics.get('total_risk_percentage', 0)
            exposure_percentage = portfolio_metrics.get('total_exposure_percentage', 0)
            concentration_risk = portfolio_metrics.get('concentration_risk', 0)
            position_count = portfolio_metrics.get('position_count', 0)
            
            # Risk level recommendations
            if risk_percentage > 0.1:  # 10% portfolio risk
                recommendations.append("⚠️  Portfolio risk is high (>10%). Consider reducing position sizes.")
            elif risk_percentage < 0.02:  # 2% portfolio risk
                recommendations.append("📈 Portfolio risk is conservative. Could increase position sizes for more growth.")
            
            # Exposure recommendations
            if exposure_percentage > 0.8:  # 80% deployed
                recommendations.append("💰 Portfolio is highly deployed (>80%). Limited dry powder for new opportunities.")
            elif exposure_percentage < 0.3:  # 30% deployed
                recommendations.append("💵 Portfolio has significant cash. Consider increasing position sizes or finding new opportunities.")
            
            # Concentration risk
            if concentration_risk > 0.2:  # 20% in single position
                recommendations.append(f"⚖️  High concentration risk ({concentration_risk:.1%} in largest position). Consider diversifying.")
            
            # Position count
            if position_count > 8:
                recommendations.append("📊 Many open positions. Consider focusing on best opportunities.")
            elif position_count < 3 and exposure_percentage > 0.5:
                recommendations.append("🎯 Few positions with high exposure. Consider diversifying.")
            
            if not recommendations:
                recommendations.append("✅ Portfolio sizing appears well-balanced.")
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("❌ Unable to analyze portfolio metrics.")
        
        return recommendations
    
    def _generate_sizing_reasoning(self, base_value: float, kelly_value: float,
                                 vol_adj: float, conf_adj: float, corr_adj: float,
                                 final_value: float) -> str:
        """Generate human-readable reasoning for position sizing."""
        reasoning_parts = []
        
        reasoning_parts.append(f"Base risk sizing: ${base_value:.0f}")
        reasoning_parts.append(f"Kelly Criterion: ${kelly_value:.0f}")
        
        if vol_adj != 1.0:
            reasoning_parts.append(f"Volatility adjustment: {vol_adj:.2f}x")
        
        if conf_adj != 1.0:
            reasoning_parts.append(f"Confidence adjustment: {conf_adj:.2f}x")
        
        if corr_adj != 1.0:
            reasoning_parts.append(f"Correlation adjustment: {corr_adj:.2f}x")
        
        reasoning_parts.append(f"Final position: ${final_value:.0f}")
        
        return " | ".join(reasoning_parts)
    
    def _log_sizing_decision(self, symbol: str, result: PositionSizeResult, 
                           technical_signals: Dict[str, Any]):
        """Log position sizing decision for analysis."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'position_size': result.position_size,
                'position_percentage': result.position_percentage,
                'kelly_fraction': result.kelly_fraction,
                'volatility_adjustment': result.volatility_adjustment,
                'confidence_adjustment': result.confidence_adjustment,
                'reasoning': result.reasoning,
                'technical_signals': {
                    'confidence': technical_signals.get('confidence', 0),
                    'composite_strength': technical_signals.get('composite_strength', 0)
                }
            }
            
            self.position_history.append(log_entry)
            
            # Keep only last 100 entries
            self.position_history = self.position_history[-100:]
            
            # Save to file
            with open(self.position_history_file, 'w') as f:
                json.dump(self.position_history, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not log sizing decision: {e}")
    
    def _load_position_history(self):
        """Load position sizing history from file."""
        try:
            if os.path.exists(self.position_history_file):
                with open(self.position_history_file, 'r') as f:
                    self.position_history = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load position history: {e}")
            self.position_history = []
    
    def _get_default_position_size(self, portfolio_value: float) -> PositionSizeResult:
        """Get default conservative position size."""
        default_size = portfolio_value * 0.05  # 5% default
        
        return PositionSizeResult(
            position_size=default_size,
            position_percentage=0.05,
            risk_per_trade=default_size * 0.02,  # 2% risk
            kelly_fraction=0.05,
            volatility_adjustment=1.0,
            confidence_adjustment=1.0,
            max_position_limit=portfolio_value * 0.15,
            reasoning="Default conservative sizing due to calculation error"
        )
    
    def analyze_sizing_performance(self, days: int = 30) -> Dict[str, Any]:
        """Analyze position sizing performance over time."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_decisions = [
                entry for entry in self.position_history
                if datetime.fromisoformat(entry['timestamp']) > cutoff_date
            ]
            
            if not recent_decisions:
                return {'error': 'No recent sizing decisions found'}
            
            # Calculate statistics
            position_sizes = [entry['position_size'] for entry in recent_decisions]
            kelly_fractions = [entry['kelly_fraction'] for entry in recent_decisions]
            vol_adjustments = [entry['volatility_adjustment'] for entry in recent_decisions]
            
            analysis = {
                'total_decisions': len(recent_decisions),
                'avg_position_size': np.mean(position_sizes),
                'median_position_size': np.median(position_sizes),
                'avg_kelly_fraction': np.mean(kelly_fractions),
                'avg_volatility_adjustment': np.mean(vol_adjustments),
                'position_size_std': np.std(position_sizes),
                'decisions_by_day': len(recent_decisions) / days,
                'max_position_size': max(position_sizes),
                'min_position_size': min(position_sizes)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing sizing performance: {e}")
            return {'error': str(e)}
