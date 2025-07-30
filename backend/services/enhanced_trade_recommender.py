"""
Enhanced Signal Flow Integration with Performance Tracking
Connects the trading system with comprehensive logging and analysis
"""
from loguru import logger
from utils.performance_tracker import performance_tracker
from services.enhanced_indicators import EnhancedIndicators
from services.market_regime_detector import MarketRegimeDetector
from services.enhanced_position_sizer import EnhancedPositionSizer


class EnhancedTradeRecommender:
    """
    Enhanced trade recommender with comprehensive performance tracking.
    Integrates all optimized components with detailed logging.
    """
    
    def __init__(self):
        """Initialize enhanced components."""
        self.enhanced_indicators = EnhancedIndicators()
        self.regime_detector = MarketRegimeDetector()
        self.position_sizer = EnhancedPositionSizer()
        logger.info("Enhanced trade recommender initialized with performance tracking")
    
    async def generate_recommendation(self, ticker: str, data: dict) -> dict:
        """
        Generate trading recommendation with full performance tracking.
        
        Args:
            ticker: Stock ticker symbol
            data: Market data for analysis
            
        Returns:
            Enhanced recommendation with tracking metadata
        """
        try:
            # Detect market regime
            regime_info = self.regime_detector.detect_market_regime(data)
            
            # Get enhanced indicators
            indicators = self.enhanced_indicators.get_comprehensive_signals(
                ticker, data, regime_info
            )
            
            # Calculate position size
            position_info = self.position_sizer.calculate_position_size(
                ticker, data, indicators, regime_info
            )
            
            # Build comprehensive recommendation
            recommendation = {
                'ticker': ticker,
                'timestamp': data.get('timestamp'),
                'signal_type': indicators.get('signal_direction', 'neutral'),
                'confidence': indicators.get('composite_confidence', 0),
                'market_regime': regime_info.get('regime', 'uncertain'),
                'regime_confidence': regime_info.get('confidence', 0),
                
                # Enhanced indicator details
                'rsi_zscore': indicators.get('rsi_zscore', 0),
                'momentum_divergence': indicators.get('momentum_divergence', 'none'),
                'volume_trend': indicators.get('volume_trend', 'neutral'),
                'order_flow_signal': indicators.get('order_flow', 'neutral'),
                'sector_strength': indicators.get('sector_relative_strength', 0),
                'volatility_percentile': regime_info.get('volatility_percentile', 50),
                'trend_strength': regime_info.get('trend_strength', 0),
                
                # Position sizing details
                'position_size': position_info.get('position_size_usd', 0),
                'kelly_fraction': position_info.get('kelly_fraction', 0),
                'expected_move': indicators.get('expected_move', 0),
                'stop_loss': indicators.get('stop_loss', 0),
                'take_profit': indicators.get('take_profit', 0),
                'risk_reward_ratio': indicators.get('risk_reward_ratio', 0),
                
                # Trading decision
                'should_trade': self._should_execute_trade(indicators, regime_info),
                'execution_priority': self._calculate_priority(indicators, regime_info)
            }
            
            # Log signal for performance tracking
            if recommendation['should_trade']:
                signal_id = performance_tracker.log_signal(recommendation)
                recommendation['signal_id'] = signal_id
                
                logger.info(f"🎯 Enhanced signal generated: {ticker} - {recommendation['signal_type']} "
                          f"(Confidence: {recommendation['confidence']:.1f}, "
                          f"Regime: {recommendation['market_regime']})")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating enhanced recommendation for {ticker}: {e}")
            return self._fallback_recommendation(ticker)
    
    def _should_execute_trade(self, indicators: dict, regime_info: dict) -> bool:
        """
        Determine if trade should be executed based on regime-aware thresholds.
        
        Args:
            indicators: Enhanced indicator signals
            regime_info: Current market regime information
            
        Returns:
            Boolean indicating if trade should be executed
        """
        confidence = indicators.get('composite_confidence', 0)
        regime = regime_info.get('regime', 'uncertain')
        
        # Dynamic confidence thresholds by regime
        thresholds = {
            'trending_high_vol': 8.5,      # Higher threshold in volatile trending markets
            'trending_low_vol': 7.5,       # Lower threshold in stable trending markets
            'mean_reverting_high_vol': 9.0, # Highest threshold in choppy markets
            'mean_reverting_low_vol': 8.0,  # Moderate threshold in stable mean-reverting
            'uncertain': 9.5               # Very high threshold when regime unclear
        }
        
        min_confidence = thresholds.get(regime, 8.0)
        
        # Additional quality filters
        rsi_zscore = abs(indicators.get('rsi_zscore', 0))
        volume_confirmation = indicators.get('volume_trend') != 'weak'
        
        should_trade = (
            confidence >= min_confidence and
            rsi_zscore >= 1.5 and  # Significant RSI deviation
            volume_confirmation and
            indicators.get('risk_reward_ratio', 0) >= 2.0
        )
        
        if should_trade:
            logger.info(f"✅ Trade criteria met: confidence {confidence:.1f} >= {min_confidence} "
                       f"(regime: {regime})")
        
        return should_trade
    
    def _calculate_priority(self, indicators: dict, regime_info: dict) -> int:
        """
        Calculate execution priority (1-10, higher = more urgent).
        
        Args:
            indicators: Enhanced indicator signals
            regime_info: Current market regime information
            
        Returns:
            Priority score for trade execution
        """
        base_priority = int(indicators.get('composite_confidence', 0))
        
        # Boost priority for high-conviction signals
        if indicators.get('momentum_divergence') in ['bullish', 'bearish']:
            base_priority += 2
        
        # Boost priority for strong volume confirmation
        if indicators.get('volume_trend') == 'strong':
            base_priority += 1
        
        # Boost priority in clear trending regimes
        if regime_info.get('regime', '').startswith('trending'):
            base_priority += 1
        
        return min(base_priority, 10)
    
    def _fallback_recommendation(self, ticker: str) -> dict:
        """Generate safe fallback recommendation on error."""
        return {
            'ticker': ticker,
            'signal_type': 'neutral',
            'confidence': 0,
            'should_trade': False,
            'error': True,
            'message': 'Error generating recommendation - using fallback'
        }
    
    async def log_execution(self, signal_id: int, execution_details: dict) -> int:
        """
        Log trade execution with performance tracking.
        
        Args:
            signal_id: ID of the original signal
            execution_details: Details of the executed trade
            
        Returns:
            Execution ID for tracking
        """
        execution_id = performance_tracker.log_execution(signal_id, execution_details)
        
        logger.info(f"📈 Trade executed: {execution_details.get('ticker')} - "
                   f"${execution_details.get('position_size_usd', 0):.2f} @ "
                   f"${execution_details.get('price', 0):.2f}")
        
        return execution_id
    
    async def log_exit(self, execution_id: int, exit_details: dict):
        """
        Log trade exit with P&L calculation.
        
        Args:
            execution_id: ID of the original execution
            exit_details: Details of the trade exit
        """
        performance_tracker.log_exit(execution_id, exit_details)
        
        pnl = exit_details.get('pnl_usd', 0)
        win_loss = "WIN" if pnl > 0 else "LOSS"
        
        logger.info(f"🎯 Trade closed: {exit_details.get('ticker')} - "
                   f"{win_loss} ${pnl:.2f} ({exit_details.get('exit_reason', 'unknown')})")
        
        # Update daily performance after each trade
        performance_tracker.update_daily_performance()
    
    def get_performance_summary(self, days: int = 7) -> dict:
        """Get recent performance summary."""
        return performance_tracker.get_regime_performance_summary(days)


class PaperTradingMonitor:
    """
    Paper trading monitor for the 7-14 day stability phase.
    Simulates real trading with detailed logging.
    """
    
    def __init__(self):
        self.positions = {}
        self.execution_log = []
        logger.info("Paper trading monitor initialized for stability phase")
    
    async def simulate_execution(self, recommendation: dict) -> dict:
        """
        Simulate trade execution for paper trading.
        
        Args:
            recommendation: Trading recommendation to simulate
            
        Returns:
            Simulated execution details
        """
        if not recommendation.get('should_trade', False):
            return None
        
        ticker = recommendation['ticker']
        current_price = recommendation.get('current_price', 100)  # Mock price
        position_size = recommendation.get('position_size', 0)
        
        # Simulate execution details
        execution = {
            'ticker': ticker,
            'action': 'BUY' if recommendation['signal_type'] == 'bullish' else 'SELL',
            'price': current_price * (1 + 0.001),  # Small slippage simulation
            'quantity': int(position_size / current_price),
            'position_size_usd': position_size,
            'market_regime': recommendation.get('market_regime'),
            'commission': position_size * 0.001,  # 0.1% commission
            'slippage': position_size * 0.0005    # 0.05% slippage
        }
        
        # Store position for exit simulation
        self.positions[ticker] = {
            'entry_price': execution['price'],
            'quantity': execution['quantity'],
            'entry_time': recommendation.get('timestamp'),
            'stop_loss': recommendation.get('stop_loss'),
            'take_profit': recommendation.get('take_profit'),
            'signal_id': recommendation.get('signal_id'),
            'market_regime': recommendation.get('market_regime')
        }
        
        self.execution_log.append(execution)
        logger.info(f"📝 Paper trade simulated: {ticker} - {execution['action']} "
                   f"${execution['position_size_usd']:.2f}")
        
        return execution
    
    async def check_exits(self, current_prices: dict):
        """
        Check for position exits based on stop loss, take profit, or time.
        
        Args:
            current_prices: Dictionary of current prices by ticker
        """
        for ticker, position in list(self.positions.items()):
            current_price = current_prices.get(ticker)
            if not current_price:
                continue
            
            exit_reason = None
            
            # Check stop loss
            if current_price <= position['stop_loss']:
                exit_reason = 'stop_loss'
            
            # Check take profit
            elif current_price >= position['take_profit']:
                exit_reason = 'take_profit'
            
            # Check time-based exit (e.g., end of day)
            # elif position.get('entry_time') and time_condition:
            #     exit_reason = 'time_exit'
            
            if exit_reason:
                await self._simulate_exit(ticker, position, current_price, exit_reason)
    
    async def _simulate_exit(self, ticker: str, position: dict, exit_price: float, reason: str):
        """Simulate position exit."""
        entry_price = position['entry_price']
        quantity = position['quantity']
        
        # Calculate P&L
        pnl_per_share = exit_price - entry_price
        total_pnl = pnl_per_share * quantity
        pnl_percent = (pnl_per_share / entry_price) * 100
        
        exit_details = {
            'ticker': ticker,
            'exit_price': exit_price,
            'exit_reason': reason,
            'pnl_usd': total_pnl,
            'pnl_percent': pnl_percent,
            'hold_duration_minutes': 60,  # Mock duration
            'market_regime_entry': position['market_regime'],
            'market_regime_exit': position['market_regime']  # Would be current regime
        }
        
        # Remove position
        del self.positions[ticker]
        
        logger.info(f"📤 Paper exit simulated: {ticker} - {reason} - P&L: ${total_pnl:.2f}")
        
        return exit_details
