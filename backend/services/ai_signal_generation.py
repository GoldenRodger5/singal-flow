"""
AI Signal Generation Service
Provides real-time AI trading signals using the AI learning engine
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from loguru import logger
from dataclasses import dataclass
import json
import os

# Import existing services
from services.ai_learning_engine import ai_learning_engine
from services.real_time_market_data import market_data_service
from services.database_manager import db_manager

@dataclass
class AISignal:
    """AI-generated trading signal."""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 to 1.0
    price_target: Optional[float]
    stop_loss: Optional[float]
    timestamp: datetime
    reasoning: str
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'
    entry_price: float
    expected_return: float
    time_horizon: str  # 'SHORT', 'MEDIUM', 'LONG'

class AISignalGenerationService:
    """AI Signal Generation Service using machine learning models."""
    
    def __init__(self):
        """Initialize AI Signal Generation Service."""
        self.confidence_threshold = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.65'))
        self.max_signals_per_day = int(os.getenv('MAX_DAILY_TRADES', '50'))
        self.enable_ai_explanations = os.getenv('ENABLE_AI_EXPLANATIONS', 'True').lower() == 'true'
        
        logger.info(f"AI Signal Generation Service initialized")
        logger.info(f"Confidence threshold: {self.confidence_threshold}")
        logger.info(f"Max signals per day: {self.max_signals_per_day}")
        logger.info(f"AI explanations enabled: {self.enable_ai_explanations}")
    
    async def generate_signals_for_watchlist(self) -> List[AISignal]:
        """Generate AI signals for all watchlist symbols."""
        signals = []
        
        try:
            # Get real-time market data for all watchlist symbols
            async with market_data_service:
                market_data = await market_data_service.get_multiple_quotes(self.watchlist)
            
            # Generate signals for each symbol
            for symbol in self.watchlist:
                if symbol in market_data:
                    signal = await self._generate_signal_for_symbol(symbol, market_data[symbol])
                    if signal and signal.confidence >= self.min_confidence_threshold:
                        signals.append(signal)
                        self.active_signals[symbol] = signal
            
            # Store signals in database
            if signals:
                await self._store_signals_to_database(signals)
            
            logger.info(f"Generated {len(signals)} AI signals from {len(self.watchlist)} watchlist symbols")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for watchlist: {e}")
            return []
    
    async def _generate_signal_for_symbol(self, symbol: str, market_data) -> Optional[AISignal]:
        """Generate AI signal for a specific symbol."""
        try:
            # Get historical data for analysis
            async with market_data_service:
                historical_data = await market_data_service.get_historical_data(symbol, days=30)
            
            if not historical_data:
                return None
            
            # Prepare data for AI analysis
            analysis_data = {
                'symbol': symbol,
                'current_price': market_data.price,
                'volume': market_data.volume,
                'change': market_data.change,
                'change_percent': market_data.change_percent,
                'day_high': market_data.day_high,
                'day_low': market_data.day_low,
                'historical_data': historical_data[-10:],  # Last 10 days
                'timestamp': market_data.timestamp.isoformat()
            }
            
            # Use AI learning engine to make prediction
            prediction = await ai_learning_engine.make_prediction(analysis_data)
            
            if not prediction:
                return None
            
            # Convert prediction to trading signal
            signal = await self._convert_prediction_to_signal(symbol, market_data, prediction)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    async def _convert_prediction_to_signal(self, symbol: str, market_data, prediction: Dict) -> Optional[AISignal]:
        """Convert AI prediction to trading signal."""
        try:
            current_price = market_data.price
            
            # Extract prediction components
            signal_strength = float(prediction.get('confidence', 0.5))
            predicted_direction = prediction.get('direction', 'HOLD')
            predicted_price_target = prediction.get('price_target', current_price)
            risk_assessment = prediction.get('risk_level', 'MEDIUM')
            reasoning = prediction.get('reasoning', 'AI model prediction based on technical analysis')
            
            # Determine signal type based on prediction
            if predicted_direction == 'UP' and signal_strength > self.min_confidence_threshold:
                signal_type = 'BUY'
                price_target = predicted_price_target
                stop_loss = current_price * (1 - self.risk_tolerance)
                expected_return = (price_target / current_price - 1) * 100
                
            elif predicted_direction == 'DOWN' and signal_strength > self.min_confidence_threshold:
                signal_type = 'SELL'
                price_target = predicted_price_target
                stop_loss = current_price * (1 + self.risk_tolerance)
                expected_return = (current_price / price_target - 1) * 100
                
            else:
                signal_type = 'HOLD'
                price_target = current_price
                stop_loss = None
                expected_return = 0.0
            
            # Determine time horizon based on signal strength and volatility
            if market_data.change_percent > 5:
                time_horizon = 'SHORT'  # High volatility = short term
            elif signal_strength > 0.8:
                time_horizon = 'LONG'   # High confidence = long term
            else:
                time_horizon = 'MEDIUM'
            
            signal = AISignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=signal_strength,
                price_target=price_target,
                stop_loss=stop_loss,
                timestamp=datetime.now(timezone.utc),
                reasoning=reasoning,
                risk_level=risk_assessment,
                entry_price=current_price,
                expected_return=expected_return,
                time_horizon=time_horizon
            )
            
            logger.debug(f"Generated {signal_type} signal for {symbol} with {signal_strength:.2f} confidence")
            return signal
            
        except Exception as e:
            logger.error(f"Error converting prediction to signal for {symbol}: {e}")
            return None
    
    async def get_active_signals(self) -> List[AISignal]:
        """Get all currently active AI signals."""
        try:
            # Filter out old signals (older than 4 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=4)
            active_signals = []
            
            for symbol, signal in self.active_signals.items():
                if signal.timestamp > cutoff_time:
                    active_signals.append(signal)
                else:
                    # Remove expired signal
                    del self.active_signals[symbol]
            
            return active_signals
            
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    async def get_signal_for_symbol(self, symbol: str) -> Optional[AISignal]:
        """Get the latest AI signal for a specific symbol."""
        try:
            # Check if we have an active signal
            if symbol in self.active_signals:
                signal = self.active_signals[symbol]
                
                # Check if signal is still fresh (within 4 hours)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=4)
                if signal.timestamp > cutoff_time:
                    return signal
                else:
                    # Remove expired signal
                    del self.active_signals[symbol]
            
            # Generate new signal
            async with market_data_service:
                market_data = await market_data_service.get_real_time_quote(symbol)
            
            if market_data:
                signal = await self._generate_signal_for_symbol(symbol, market_data)
                if signal:
                    self.active_signals[symbol] = signal
                    await self._store_signals_to_database([signal])
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting signal for {symbol}: {e}")
            return None
    
    async def get_signal_performance(self, days: int = 7) -> Dict[str, Any]:
        """Analyze AI signal performance over the last N days."""
        try:
            # Get signals from database
            signals_data = await db_manager.get_recent_signals(days)
            
            if not signals_data:
                return {
                    'total_signals': 0,
                    'successful_signals': 0,
                    'success_rate': 0.0,
                    'average_return': 0.0,
                    'best_signal': None,
                    'worst_signal': None
                }
            
            total_signals = len(signals_data)
            successful_signals = 0
            total_return = 0.0
            best_return = float('-inf')
            worst_return = float('inf')
            best_signal = None
            worst_signal = None
            
            for signal_data in signals_data:
                # Calculate actual return if we have outcome data
                actual_return = signal_data.get('actual_return', 0.0)
                total_return += actual_return
                
                if actual_return > 0:
                    successful_signals += 1
                
                if actual_return > best_return:
                    best_return = actual_return
                    best_signal = {
                        'symbol': signal_data.get('symbol'),
                        'return': actual_return,
                        'signal_type': signal_data.get('signal_type'),
                        'date': signal_data.get('timestamp')
                    }
                
                if actual_return < worst_return:
                    worst_return = actual_return
                    worst_signal = {
                        'symbol': signal_data.get('symbol'),
                        'return': actual_return,
                        'signal_type': signal_data.get('signal_type'),
                        'date': signal_data.get('timestamp')
                    }
            
            success_rate = (successful_signals / total_signals) * 100 if total_signals > 0 else 0
            average_return = total_return / total_signals if total_signals > 0 else 0
            
            return {
                'total_signals': total_signals,
                'successful_signals': successful_signals,
                'success_rate': round(success_rate, 2),
                'average_return': round(average_return, 2),
                'best_signal': best_signal,
                'worst_signal': worst_signal
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signal performance: {e}")
            return {}
    
    async def _store_signals_to_database(self, signals: List[AISignal]):
        """Store AI signals to database for tracking."""
        try:
            signals_data = []
            
            for signal in signals:
                signal_doc = {
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type,
                    'confidence': signal.confidence,
                    'price_target': signal.price_target,
                    'stop_loss': signal.stop_loss,
                    'timestamp': signal.timestamp,
                    'reasoning': signal.reasoning,
                    'risk_level': signal.risk_level,
                    'entry_price': signal.entry_price,
                    'expected_return': signal.expected_return,
                    'time_horizon': signal.time_horizon,
                    'status': 'ACTIVE'
                }
                signals_data.append(signal_doc)
            
            await db_manager.store_ai_signals(signals_data)
            logger.debug(f"Stored {len(signals)} AI signals to database")
            
        except Exception as e:
            logger.error(f"Error storing signals to database: {e}")
    
    async def update_signal_outcomes(self):
        """Update outcomes for active signals based on current market prices."""
        try:
            active_signals = await self.get_active_signals()
            
            if not active_signals:
                return
            
            # Get current market prices
            symbols = [signal.symbol for signal in active_signals]
            async with market_data_service:
                current_prices = await market_data_service.get_multiple_quotes(symbols)
            
            updates = []
            
            for signal in active_signals:
                if signal.symbol in current_prices:
                    current_data = current_prices[signal.symbol]
                    current_price = current_data.price
                    
                    # Calculate actual return
                    if signal.signal_type == 'BUY':
                        actual_return = (current_price / signal.entry_price - 1) * 100
                    elif signal.signal_type == 'SELL':
                        actual_return = (signal.entry_price / current_price - 1) * 100
                    else:
                        actual_return = 0.0
                    
                    updates.append({
                        'symbol': signal.symbol,
                        'timestamp': signal.timestamp,
                        'actual_return': actual_return,
                        'current_price': current_price
                    })
            
            if updates:
                await db_manager.update_signal_outcomes(updates)
                logger.debug(f"Updated outcomes for {len(updates)} signals")
                
        except Exception as e:
            logger.error(f"Error updating signal outcomes: {e}")

# Global instance
ai_signal_service = AISignalGenerationService()
signal_generation_service = ai_signal_service  # Alias for consistency

# Export for easy importing
__all__ = ['ai_signal_service', 'signal_generation_service', 'AISignalGenerationService', 'TradingSignal']
