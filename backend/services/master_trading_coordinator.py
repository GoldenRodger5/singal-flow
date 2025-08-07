"""
Master Trading Strategy Coordinator
Integrates all trading engines for maximum profitability
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass, asdict

from services.anomaly_detection import anomaly_engine, TradingAnomaly
from services.websocket_engine import websocket_engine
from services.short_squeeze_detector import squeeze_detector, ShortSqueezeSignal
from services.sentiment_trading import sentiment_engine, SentimentSignal
from services.market_schedule_manager import market_schedule

@dataclass
class UnifiedTradingSignal:
    """Master trading signal combining all strategies."""
    symbol: str
    primary_strategy: str  # 'anomaly', 'squeeze', 'sentiment', 'combined'
    signal_strength: float  # 0-100
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: float  # % of portfolio
    confidence: float
    expected_return: float  # Expected % return
    risk_reward_ratio: float
    timeframe: str  # 'scalp', 'day', 'swing'
    timestamp: datetime
    
    # Supporting data
    anomaly_data: Optional[Dict] = None
    squeeze_data: Optional[Dict] = None
    sentiment_data: Optional[Dict] = None

class MasterTradingCoordinator:
    """
    Master coordinator that integrates all trading strategies.
    Makes intelligent decisions based on multiple signal sources.
    """
    
    def __init__(self):
        self.watchlist = [
            'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN',
            'SPY', 'QQQ', 'IWM', 'VIX', 'NFLX', 'BABA', 'CRM', 'UBER'
        ]
        
        self.active_signals = {}
        self.position_limits = {
            'max_positions': 5,
            'max_portfolio_risk': 25.0,  # 25% max portfolio risk
            'single_position_max': 8.0   # 8% max per position
        }
        
        self.is_running = False
        logger.info("🎯 Master Trading Coordinator initialized")
    
    async def start_trading_system(self):
        """Start the complete trading system."""
        logger.info("🚀 Starting Master Trading System")
        
        if not market_schedule.is_market_open():
            logger.info("📅 Market is closed - running in analysis mode")
        
        self.is_running = True
        
        # Start all subsystems
        await asyncio.gather(
            self._run_signal_generation(),
            self._run_websocket_monitoring(),
            self._run_position_management(),
            return_exceptions=True
        )
    
    async def _run_signal_generation(self):
        """Main signal generation loop."""
        while self.is_running:
            try:
                logger.info("🔍 Scanning for trading opportunities...")
                
                # Run all detection engines in parallel
                results = await asyncio.gather(
                    anomaly_engine.detect_anomalies(self.watchlist),
                    squeeze_detector.scan_for_squeeze_opportunities(self.watchlist),
                    sentiment_engine.analyze_sentiment_signals(self.watchlist),
                    return_exceptions=True
                )
                
                anomalies, squeezes, sentiments = results
                
                # Process results
                if isinstance(anomalies, list):
                    await self._process_anomaly_signals(anomalies)
                
                if isinstance(squeezes, list):
                    await self._process_squeeze_signals(squeezes)
                
                if isinstance(sentiments, list):
                    await self._process_sentiment_signals(sentiments)
                
                # Generate unified signals
                unified_signals = await self._generate_unified_signals()
                
                # Execute highest confidence signals
                await self._execute_best_signals(unified_signals)
                
                # Wait before next scan
                scan_interval = 30 if market_schedule.is_market_open() else 300
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in signal generation: {e}")
                await asyncio.sleep(60)
    
    async def _process_anomaly_signals(self, anomalies: List[TradingAnomaly]):
        """Process anomaly detection signals."""
        for anomaly in anomalies[:5]:  # Top 5 anomalies
            signal_data = {
                'type': 'anomaly',
                'data': asdict(anomaly),
                'timestamp': datetime.now(),
                'confidence': anomaly.confidence
            }
            
            self.active_signals[f"anomaly_{anomaly.symbol}"] = signal_data
            
            logger.info(f"🚨 ANOMALY: {anomaly.symbol} - {anomaly.anomaly_type} "
                       f"(Confidence: {anomaly.confidence:.1f}%)")
    
    async def _process_squeeze_signals(self, squeezes: List[ShortSqueezeSignal]):
        """Process short squeeze signals."""
        for squeeze in squeezes[:3]:  # Top 3 squeezes
            signal_data = {
                'type': 'squeeze',
                'data': asdict(squeeze),
                'timestamp': datetime.now(),
                'confidence': squeeze.squeeze_probability
            }
            
            self.active_signals[f"squeeze_{squeeze.symbol}"] = signal_data
            
            logger.info(f"💥 SQUEEZE: {squeeze.symbol} - {squeeze.squeeze_probability:.1f}% "
                       f"probability (Risk: {squeeze.risk_level})")
    
    async def _process_sentiment_signals(self, sentiments: List[SentimentSignal]):
        """Process sentiment analysis signals."""
        for sentiment in sentiments[:5]:  # Top 5 sentiment signals
            signal_data = {
                'type': 'sentiment',
                'data': asdict(sentiment),
                'timestamp': datetime.now(),
                'confidence': sentiment.confidence
            }
            
            self.active_signals[f"sentiment_{sentiment.symbol}"] = signal_data
            
            logger.info(f"📰 SENTIMENT: {sentiment.symbol} - {sentiment.signal_type} "
                       f"(Confidence: {sentiment.confidence:.1f}%)")
    
    async def _generate_unified_signals(self) -> List[UnifiedTradingSignal]:
        """Generate unified trading signals by combining strategies."""
        unified_signals = []
        
        # Group signals by symbol
        symbol_signals = {}
        for signal_id, signal_data in self.active_signals.items():
            symbol = signal_data['data']['symbol']
            if symbol not in symbol_signals:
                symbol_signals[symbol] = []
            symbol_signals[symbol].append(signal_data)
        
        # Create unified signals
        for symbol, signals in symbol_signals.items():
            unified_signal = await self._create_unified_signal(symbol, signals)
            if unified_signal and unified_signal.signal_strength > 70:
                unified_signals.append(unified_signal)
        
        # Sort by signal strength
        unified_signals.sort(key=lambda x: x.signal_strength, reverse=True)
        
        return unified_signals
    
    async def _create_unified_signal(self, symbol: str, signals: List[Dict]) -> Optional[UnifiedTradingSignal]:
        """Create unified signal from multiple strategy signals."""
        try:
            if not signals:
                return None
            
            # Determine primary strategy (highest confidence)
            primary_signal = max(signals, key=lambda x: x['confidence'])
            primary_strategy = primary_signal['type']
            
            # Calculate combined signal strength
            combined_confidence = 0
            weights = {'anomaly': 0.4, 'squeeze': 0.35, 'sentiment': 0.25}
            
            for signal in signals:
                weight = weights.get(signal['type'], 0.2)
                combined_confidence += signal['confidence'] * weight
            
            # Boost if multiple strategies agree
            if len(signals) > 1:
                combined_confidence *= 1.2  # 20% boost for multi-strategy confirmation
            
            combined_confidence = min(100, combined_confidence)
            
            # Get price targets from primary signal
            primary_data = primary_signal['data']
            entry_price = primary_data.get('entry_price', primary_data.get('current_price', 0))
            target_price = primary_data.get('target_price', entry_price * 1.05)
            stop_loss = primary_data.get('stop_loss', entry_price * 0.95)
            
            # Calculate risk-reward ratio
            potential_gain = target_price - entry_price
            potential_loss = entry_price - stop_loss
            risk_reward = potential_gain / potential_loss if potential_loss > 0 else 0
            
            # Calculate expected return
            expected_return = ((target_price / entry_price) - 1) * 100
            
            # Calculate position size based on risk and confidence
            position_size = self._calculate_position_size(combined_confidence, risk_reward)
            
            # Determine timeframe
            timeframe = self._determine_timeframe(signals)
            
            return UnifiedTradingSignal(
                symbol=symbol,
                primary_strategy=primary_strategy,
                signal_strength=combined_confidence,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size=position_size,
                confidence=combined_confidence,
                expected_return=expected_return,
                risk_reward_ratio=risk_reward,
                timeframe=timeframe,
                timestamp=datetime.now(),
                anomaly_data=next((s['data'] for s in signals if s['type'] == 'anomaly'), None),
                squeeze_data=next((s['data'] for s in signals if s['type'] == 'squeeze'), None),
                sentiment_data=next((s['data'] for s in signals if s['type'] == 'sentiment'), None)
            )
            
        except Exception as e:
            logger.error(f"Error creating unified signal for {symbol}: {e}")
            return None
    
    def _calculate_position_size(self, confidence: float, risk_reward: float) -> float:
        """Calculate optimal position size based on confidence and risk-reward."""
        # Base position size on confidence
        base_size = (confidence / 100) * self.position_limits['single_position_max']
        
        # Adjust for risk-reward ratio
        if risk_reward > 2.0:
            base_size *= 1.2  # Increase for good risk-reward
        elif risk_reward < 1.0:
            base_size *= 0.7  # Decrease for poor risk-reward
        
        # Cap at maximum single position
        return min(base_size, self.position_limits['single_position_max'])
    
    def _determine_timeframe(self, signals: List[Dict]) -> str:
        """Determine optimal timeframe based on signal types."""
        has_anomaly = any(s['type'] == 'anomaly' for s in signals)
        has_squeeze = any(s['type'] == 'squeeze' for s in signals)
        has_sentiment = any(s['type'] == 'sentiment' for s in signals)
        
        if has_anomaly and has_sentiment:
            return 'scalp'  # Quick profits from anomaly + news
        elif has_squeeze:
            return 'swing'  # Squeezes take time to develop
        else:
            return 'day'    # Standard day trade
    
    async def _execute_best_signals(self, signals: List[UnifiedTradingSignal]):
        """Execute the best trading signals."""
        if not signals:
            logger.info("📊 No high-confidence signals found")
            return
        
        # Log best opportunities
        logger.info(f"🎯 TOP TRADING OPPORTUNITIES:")
        for i, signal in enumerate(signals[:3], 1):
            logger.info(
                f"  {i}. {signal.symbol} ({signal.primary_strategy.upper()}) - "
                f"Strength: {signal.signal_strength:.1f}% | "
                f"Expected Return: {signal.expected_return:.1f}% | "
                f"R/R: {signal.risk_reward_ratio:.1f}"
            )
        
        # In live trading, this would connect to broker API
        # For now, we log the trade recommendations
        best_signal = signals[0]
        logger.info(f"🚀 RECOMMENDED TRADE:")
        logger.info(f"   Symbol: {best_signal.symbol}")
        logger.info(f"   Strategy: {best_signal.primary_strategy}")
        logger.info(f"   Entry: ${best_signal.entry_price:.2f}")
        logger.info(f"   Target: ${best_signal.target_price:.2f}")
        logger.info(f"   Stop: ${best_signal.stop_loss:.2f}")
        logger.info(f"   Position Size: {best_signal.position_size:.1f}%")
        logger.info(f"   Confidence: {best_signal.confidence:.1f}%")
    
    async def _run_websocket_monitoring(self):
        """Run WebSocket monitoring for real-time data."""
        if not market_schedule.is_market_open():
            return
        
        try:
            # Connect to WebSocket
            await websocket_engine.connect()
            
            # Subscribe to watchlist
            await websocket_engine.subscribe_quotes(self.watchlist)
            await websocket_engine.subscribe_trades(self.watchlist)
            
            logger.info("📡 WebSocket monitoring active")
            
            # Keep running while system is active
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"WebSocket monitoring error: {e}")
    
    async def _run_position_management(self):
        """Monitor and manage active positions."""
        while self.is_running:
            try:
                # Clean up old signals
                cutoff_time = datetime.now() - timedelta(minutes=30)
                expired_signals = [
                    signal_id for signal_id, signal_data in self.active_signals.items()
                    if signal_data['timestamp'] < cutoff_time
                ]
                
                for signal_id in expired_signals:
                    del self.active_signals[signal_id]
                
                if expired_signals:
                    logger.debug(f"🧹 Cleaned up {len(expired_signals)} expired signals")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Position management error: {e}")
                await asyncio.sleep(60)
    
    async def get_system_status(self) -> Dict:
        """Get current system status."""
        return {
            'is_running': self.is_running,
            'market_open': market_schedule.is_market_open(),
            'active_signals': len(self.active_signals),
            'watchlist_size': len(self.watchlist),
            'websocket_connected': websocket_engine.is_connected if hasattr(websocket_engine, 'is_connected') else False,
            'last_scan': datetime.now().isoformat()
        }
    
    async def stop_trading_system(self):
        """Stop the trading system."""
        self.is_running = False
        await websocket_engine.disconnect()
        logger.info("🛑 Master Trading System stopped")

# Global instance
master_coordinator = MasterTradingCoordinator()

# Export
__all__ = ['master_coordinator', 'MasterTradingCoordinator', 'UnifiedTradingSignal']
