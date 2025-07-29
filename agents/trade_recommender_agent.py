"""
Trade Recommender Agent - Makes final trading decisions based on all available data.
Enhanced with AI learning capabilities, regime awareness, and modern position sizing.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from services.config import Config
from services.indicators import TechnicalIndicators
from services.ai_learning_engine import AILearningEngine, TradePrediction, DecisionContext
from services.enhanced_decision_logger import EnhancedDecisionLogger, DecisionContext as LoggerContext

# Import enhanced components
try:
    from services.market_regime_detector import MarketRegimeDetector
    from services.enhanced_indicators import EnhancedIndicators
    from services.enhanced_position_sizer import EnhancedPositionSizer
    ENHANCED_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced components not available in trade recommender")
    ENHANCED_AVAILABLE = False


class TradeRecommenderAgent:
    """Agent that makes final trading recommendations with enhanced regime-aware analysis."""
    
    def __init__(self):
        """Initialize the trade recommender agent."""
        self.config = Config()
        self.daily_trade_count = 0
        self.active_recommendations = []
        
        # Initialize core components
        self.learning_engine = AILearningEngine()
        self.decision_logger = EnhancedDecisionLogger()
        self.indicators = TechnicalIndicators(self.config, getattr(self.learning_engine, 'regime_detector', None))
        
        # Initialize enhanced components if available
        if ENHANCED_AVAILABLE and hasattr(self.learning_engine, 'regime_detector'):
            self.regime_detector = self.learning_engine.regime_detector
            self.enhanced_indicators = self.learning_engine.enhanced_indicators
            self.position_sizer = self.learning_engine.position_sizer
            logger.info("Enhanced trade recommender components initialized")
        else:
            self.regime_detector = None
            self.enhanced_indicators = None
            self.position_sizer = None
            logger.warning("Using basic trade recommender without enhanced components")
        
    async def evaluate_setup(self, setup: Dict[str, Any], sentiment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate a setup and sentiment to make a trading recommendation."""
        try:
            ticker = setup.get('ticker')
            logger.info(f"Evaluating trade setup for {ticker}")
            
            # Check daily trade limits
            if self.daily_trade_count >= self.config.MAX_DAILY_TRADES:
                logger.warning(f"Daily trade limit reached ({self.config.MAX_DAILY_TRADES})")
                return None
            
            # Create decision context for enhanced logging
            context = self._create_decision_context(setup, sentiment)
            
            # Start decision logging
            decision_id = await self.decision_logger.start_decision_logging(ticker, context)
            
            # Get adaptive thresholds from learning engine
            adaptive_thresholds = self.learning_engine.get_adaptive_thresholds()
            
            # Calculate comprehensive recommendation with AI learning
            recommendation = await self._analyze_setup_with_learning(setup, sentiment, decision_id, adaptive_thresholds)
            
            if not recommendation:
                await self.decision_logger.finalize_decision(
                    decision_id, 'no_trade', 0.0, {}, [], ['insufficient_signals']
                )
                return None
            
            # Add risk management
            recommendation = self._add_risk_management(recommendation, setup)
            
            # Final validation
            if self._validate_recommendation(recommendation, adaptive_thresholds):
                # Record prediction for learning
                prediction = self._create_prediction_from_recommendation(recommendation, setup, sentiment)
                prediction_id = await self.learning_engine.record_prediction(prediction)
                recommendation['prediction_id'] = prediction_id
                
                # Finalize decision logging
                await self.decision_logger.finalize_decision(
                    decision_id,
                    'buy',
                    recommendation['confidence'],
                    recommendation.get('expected_outcome', {}),
                    recommendation.get('key_factors', []),
                    recommendation.get('risk_factors', [])
                )
                
                logger.info(f"AI-enhanced trade recommendation generated for {ticker} "
                           f"with confidence {recommendation['confidence']:.1f}")
                return recommendation
            else:
                await self.decision_logger.finalize_decision(
                    decision_id, 'no_trade', recommendation.get('confidence', 0.0), 
                    {}, [], ['failed_validation']
                )
                logger.info(f"Trade recommendation failed validation for {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Error evaluating setup: {e}")
            return None
    
    def _analyze_setup_quality(self, setup: Dict[str, Any], sentiment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze the quality of the trading setup."""
        try:
            ticker = setup.get('ticker')
            current_price = setup.get('current_price', 0)
            
            if current_price == 0:
                return None
            
            # Start with base setup data
            recommendation = {
                'ticker': ticker,
                'entry_price': current_price,
                'timestamp': datetime.now().isoformat(),
                'setup_type': self._identify_setup_type(setup),
                'technical_signals': self._extract_technical_signals(setup),
                'sentiment_signals': self._extract_sentiment_signals(sentiment),
            }
            
            # Calculate comprehensive confidence
            confidence = self._calculate_comprehensive_confidence(setup, sentiment)
            recommendation['confidence'] = confidence
            
            # Calculate position size
            position_size = self._calculate_position_size(current_price, confidence)
            recommendation['position_size'] = position_size
            
            # Add trade levels
            trade_levels = self._calculate_trade_levels(setup, confidence)
            recommendation.update(trade_levels)
            
            # Add expected move and probability
            recommendation['expected_move'] = self._calculate_expected_move(setup, sentiment)
            recommendation['success_probability'] = self._estimate_success_probability(setup, sentiment)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error analyzing setup quality: {e}")
            return None
    
    def _identify_setup_type(self, setup: Dict[str, Any]) -> str:
        """Identify the primary setup type."""
        setup_reasons = setup.get('setup_reasons', [])
        
        if any('VWAP bounce' in reason for reason in setup_reasons):
            return 'VWAP Bounce'
        elif any('RSI oversold' in reason for reason in setup_reasons):
            return 'RSI Oversold'
        elif any('MACD bullish' in reason for reason in setup_reasons):
            return 'MACD Breakout'
        elif any('Volume spike' in reason for reason in setup_reasons):
            return 'Volume Breakout'
        else:
            return 'Multi-Factor Setup'
    
    def _extract_technical_signals(self, setup: Dict[str, Any]) -> List[str]:
        """Extract and format technical signals."""
        signals = []
        
        # RSI signals
        rsi_data = setup.get('rsi', {})
        if rsi_data.get('is_oversold', False):
            signals.append(f"RSI Oversold ({rsi_data.get('rsi_value', 0):.1f})")
        
        # VWAP signals
        vwap_data = setup.get('vwap', {})
        if vwap_data.get('is_bounce', False):
            distance = vwap_data.get('distance', 0) * 100
            signals.append(f"VWAP Bounce ({distance:+.1f}% from VWAP)")
        
        # MACD signals
        macd_data = setup.get('macd', {})
        if macd_data.get('is_bullish_cross', False):
            signals.append("MACD Bullish Crossover")
        
        # Volume signals
        volume_data = setup.get('volume_data', {})
        if volume_data.get('spike', False):
            avg_vol = volume_data.get('average', 1)
            current_vol = volume_data.get('current', 1)
            ratio = current_vol / avg_vol if avg_vol > 0 else 1
            signals.append(f"Volume Spike ({ratio:.1f}x average)")
        
        return signals
    
    def _extract_sentiment_signals(self, sentiment: Dict[str, Any]) -> List[str]:
        """Extract and format sentiment signals."""
        signals = []
        
        news_sentiment = sentiment.get('news_sentiment', 'neutral')
        sentiment_score = sentiment.get('sentiment_score', 0)
        news_count = sentiment.get('news_count', 0)
        
        if news_count > 0:
            if news_sentiment == 'bullish' and sentiment_score > 0.3:
                signals.append(f"Bullish News Sentiment ({sentiment_score:.2f})")
            elif news_sentiment == 'bearish' and sentiment_score < -0.3:
                signals.append(f"Bearish News Sentiment ({sentiment_score:.2f})")
            else:
                signals.append(f"Neutral News Sentiment")
        
        # Add key themes
        themes = sentiment.get('key_themes', [])
        if themes:
            signals.append(f"Key Themes: {', '.join(themes[:2])}")
        
        return signals
    
    def _calculate_comprehensive_confidence(self, setup: Dict[str, Any], sentiment: Dict[str, Any]) -> float:
        """Calculate comprehensive confidence score incorporating all factors."""
        try:
            # Start with base technical confidence
            base_confidence = setup.get('confidence', 0)
            
            # Sentiment adjustment
            sentiment_impact = self._calculate_sentiment_impact(sentiment)
            
            # Risk/Reward adjustment
            rr_ratio = setup.get('risk_reward', {}).get('rr_ratio', 0)
            rr_bonus = min(2.0, (rr_ratio - 2.0) * 0.5) if rr_ratio > 2.0 else 0
            
            # Volume confirmation
            volume_data = setup.get('volume_data', {})
            volume_bonus = 0.5 if volume_data.get('spike', False) else 0
            
            # Multiple signal confirmation
            setup_score = setup.get('setup_score', 0)
            signal_bonus = min(1.0, (setup_score - 3) * 0.2) if setup_score > 3 else 0
            
            # Market volatility bonus
            volatility_bonus = 0.3 if setup.get('is_volatile_session', False) else 0
            
            # Calculate final confidence
            final_confidence = (
                base_confidence +
                sentiment_impact +
                rr_bonus +
                volume_bonus +
                signal_bonus +
                volatility_bonus
            )
            
            # Normalize to 0-10 scale
            return max(0.0, min(10.0, final_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive confidence: {e}")
            return 0.0
    
    def _calculate_sentiment_impact(self, sentiment: Dict[str, Any]) -> float:
        """Calculate sentiment impact on confidence."""
        try:
            news_sentiment = sentiment.get('news_sentiment', 'neutral')
            sentiment_score = sentiment.get('sentiment_score', 0)
            sentiment_confidence = sentiment.get('sentiment_confidence', 0)
            
            if news_sentiment == 'bullish' and sentiment_score > 0.3:
                return sentiment_confidence * 1.5  # Up to +1.5 points
            elif news_sentiment == 'bearish' and sentiment_score < -0.3:
                return -sentiment_confidence * 1.0  # Up to -1.0 points
            else:
                return sentiment_confidence * 0.2  # Small bonus for having news
                
        except Exception:
            return 0.0
    
    def _calculate_position_size(self, entry_price: float, confidence: float) -> Dict[str, Any]:
        """Calculate appropriate position size based on confidence and risk management."""
        try:
            # Base position size as percentage of account
            base_size_percent = self.config.POSITION_SIZE_PERCENT or 0.1  # 10% default
            
            # Adjust based on confidence (scale 0.5x to 1.5x)
            confidence_multiplier = 0.5 + (confidence / 10.0)
            
            # Final position size percentage
            position_size_percent = base_size_percent * confidence_multiplier
            
            # Ensure reasonable limits
            position_size_percent = max(0.02, min(0.15, position_size_percent))  # 2-15%
            
            return {
                'percentage': position_size_percent,
                'confidence_multiplier': confidence_multiplier,
                'max_risk_per_trade': position_size_percent * 0.02  # 2% max risk
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {'percentage': 0.05, 'confidence_multiplier': 1.0, 'max_risk_per_trade': 0.01}
    
    def _calculate_trade_levels(self, setup: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Calculate entry, stop loss, and take profit levels."""
        try:
            current_price = setup.get('current_price', 0)
            risk_reward = setup.get('risk_reward', {})
            
            entry = current_price
            stop_loss = risk_reward.get('stop_loss', entry * 0.97)
            take_profit = risk_reward.get('take_profit', entry * 1.04)
            
            # Adjust levels based on confidence
            if confidence >= 8.0:
                # Higher confidence: tighter stop, higher target
                stop_loss = max(stop_loss, entry * 0.98)
                take_profit = min(take_profit * 1.1, entry * 1.06)
            elif confidence <= 6.0:
                # Lower confidence: wider stop, conservative target
                stop_loss = min(stop_loss, entry * 0.96)
                take_profit = max(take_profit * 0.9, entry * 1.02)
            
            # Calculate actual risk/reward
            risk = entry - stop_loss
            reward = take_profit - entry
            actual_rr = reward / risk if risk > 0 else 0
            
            return {
                'entry': round(entry, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'risk_amount': round(risk, 2),
                'reward_amount': round(reward, 2),
                'risk_reward_ratio': round(actual_rr, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade levels: {e}")
            return {
                'entry': 0, 'stop_loss': 0, 'take_profit': 0,
                'risk_amount': 0, 'reward_amount': 0, 'risk_reward_ratio': 0
            }
    
    def _calculate_expected_move(self, setup: Dict[str, Any], sentiment: Dict[str, Any]) -> float:
        """Calculate expected price move percentage."""
        try:
            base_move = self.config.MIN_EXPECTED_MOVE  # 3% default
            
            # Adjust based on volatility indicators
            if setup.get('is_volatile_session', False):
                base_move *= 1.5
            
            # Adjust based on volume
            volume_data = setup.get('volume_data', {})
            if volume_data.get('spike', False):
                base_move *= 1.3
            
            # Adjust based on sentiment strength
            sentiment_score = abs(sentiment.get('sentiment_score', 0))
            if sentiment_score > 0.5:
                base_move *= (1 + sentiment_score * 0.5)
            
            return min(0.10, base_move)  # Cap at 10%
            
        except Exception:
            return self.config.MIN_EXPECTED_MOVE
    
    def _estimate_success_probability(self, setup: Dict[str, Any], sentiment: Dict[str, Any]) -> float:
        """Estimate probability of trade success."""
        try:
            # Base probability from setup score
            setup_score = setup.get('setup_score', 0)
            base_prob = min(0.7, 0.4 + (setup_score * 0.05))  # 40-70% range
            
            # Adjust for R:R ratio
            rr_ratio = setup.get('risk_reward', {}).get('rr_ratio', 0)
            if rr_ratio >= 3.0:
                base_prob += 0.1
            elif rr_ratio < 2.0:
                base_prob -= 0.1
            
            # Adjust for sentiment
            sentiment_score = sentiment.get('sentiment_score', 0)
            if sentiment.get('news_sentiment') == 'bullish' and sentiment_score > 0.3:
                base_prob += 0.05
            elif sentiment.get('news_sentiment') == 'bearish' and sentiment_score < -0.3:
                base_prob -= 0.05
            
            return max(0.3, min(0.8, base_prob))  # 30-80% range
            
        except Exception:
            return 0.5  # 50% default
    
    def _add_risk_management(self, recommendation: Dict[str, Any], setup: Dict[str, Any]) -> Dict[str, Any]:
        """Add comprehensive risk management to the recommendation."""
        try:
            # Add timing constraints
            recommendation['valid_until'] = self._calculate_validity_period()
            
            # Add market condition requirements
            recommendation['market_conditions'] = {
                'min_volume': setup.get('volume_data', {}).get('average', 0) * 0.5,
                'max_spread_percent': 0.02,  # 2% max spread
                'trading_hours_only': True
            }
            
            # Add exit strategy
            recommendation['exit_strategy'] = {
                'stop_loss_type': 'market',
                'take_profit_type': 'limit',
                'trailing_stop': recommendation['confidence'] >= 8.0,
                'max_hold_time': '2 hours'
            }
            
            # Add alerts
            recommendation['alerts'] = {
                'entry_filled': True,
                'stop_hit': True,
                'target_reached': True,
                'time_based_exit': True
            }
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error adding risk management: {e}")
            return recommendation
    
    def _calculate_validity_period(self) -> str:
        """Calculate how long the recommendation remains valid."""
        from datetime import timedelta
        
        # Recommendations are valid for 30 minutes
        valid_until = datetime.now() + timedelta(minutes=30)
        return valid_until.isoformat()
    
    def _validate_recommendation(self, recommendation: Dict[str, Any]) -> bool:
        """Final validation of the recommendation."""
        try:
            # Check minimum confidence
            confidence = recommendation.get('confidence', 0)
            if confidence < self.config.MIN_CONFIDENCE_SCORE:
                logger.warning(f"Confidence {confidence} < minimum {self.config.MIN_CONFIDENCE_SCORE}")
                return False
            
            # Check minimum R:R ratio
            rr_ratio = recommendation.get('risk_reward_ratio', 0)
            if rr_ratio < self.config.RR_THRESHOLD:
                logger.warning(f"R:R ratio {rr_ratio} < threshold {self.config.RR_THRESHOLD}")
                return False
            
            # Check price range
            entry_price = recommendation.get('entry', 0)
            if not (self.config.TICKER_PRICE_MIN <= entry_price <= self.config.TICKER_PRICE_MAX):
                logger.warning(f"Entry price {entry_price} outside range [{self.config.TICKER_PRICE_MIN}, {self.config.TICKER_PRICE_MAX}]")
                return False
            
            # Check position size is reasonable
            position_size = recommendation.get('position_size', {}).get('percentage', 0)
            if position_size <= 0 or position_size > 0.2:  # Max 20%
                logger.warning(f"Position size {position_size} outside valid range (0, 0.2]")
                return False
            
            # Check trade levels are logical
            entry = recommendation.get('entry', 0)
            stop_loss = recommendation.get('stop_loss', 0)
            take_profit = recommendation.get('take_profit', 0)
            
            if not (stop_loss < entry < take_profit):
                logger.warning(f"Trade levels not logical: stop {stop_loss} < entry {entry} < target {take_profit}")
                return False
            
            logger.info(f"All validation checks passed for {recommendation.get('ticker', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating recommendation: {e}")
            return False
    
    def update_daily_trade_count(self, count: int) -> None:
        """Update the daily trade count."""
        self.daily_trade_count = count
    
    def reset_daily_counter(self) -> None:
        """Reset daily trade counter (called at market open)."""
        self.daily_trade_count = 0
        logger.info("Daily trade counter reset")
    
    def get_active_recommendations(self) -> List[Dict[str, Any]]:
        """Get list of active recommendations."""
        return self.active_recommendations.copy()
    
    def add_active_recommendation(self, recommendation: Dict[str, Any]) -> None:
        """Add a recommendation to active list."""
        self.active_recommendations.append(recommendation)
    
    def remove_active_recommendation(self, ticker: str) -> None:
        """Remove a recommendation from active list."""
        self.active_recommendations = [
            rec for rec in self.active_recommendations 
            if rec.get('ticker') != ticker
        ]

    # ============ AI-ENHANCED METHODS ============
    
    def _create_decision_context(self, setup: Dict[str, Any], sentiment: Dict[str, Any]) -> LoggerContext:
        """Create comprehensive decision context for logging."""
        return LoggerContext(
            ticker=setup.get('ticker'),
            market_data={
                'current_price': setup.get('current_price'),
                'volume': setup.get('volume_data', {}),
                'price_action': setup.get('price_action', {}),
                'market_conditions': setup.get('market_conditions', {})
            },
            technical_indicators={
                'rsi': setup.get('rsi_data', {}),
                'vwap': setup.get('vwap_data', {}),
                'macd': setup.get('macd_data', {}),
                'volume_profile': setup.get('volume_data', {})
            },
            sentiment_data={
                'news_sentiment': sentiment.get('news_sentiment'),
                'sentiment_score': sentiment.get('sentiment_score'),
                'social_sentiment': sentiment.get('social_media', {}),
                'market_mood': sentiment.get('market_context', {})
            },
            market_conditions={
                'market_trend': setup.get('market_conditions', {}).get('trend'),
                'volatility': setup.get('market_conditions', {}).get('volatility'),
                'sector_performance': setup.get('market_conditions', {}).get('sector_performance', {}),
                'economic_events': setup.get('market_conditions', {}).get('economic_events', [])
            },
            time_context={
                'timestamp': datetime.now().isoformat(),
                'market_session': self._get_market_session(),
                'time_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday()
            },
            portfolio_context={
                'current_positions': len(self.active_recommendations),
                'daily_trades': self.daily_trade_count,
                'available_capital': setup.get('portfolio_info', {}).get('available_capital', 0),
                'risk_exposure': setup.get('portfolio_info', {}).get('risk_exposure', 0)
            }
        )
    
    async def _analyze_setup_with_learning(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                         decision_id: str, adaptive_thresholds: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Enhanced setup analysis with AI learning integration."""
        try:
            ticker = setup.get('ticker')
            current_price = setup.get('current_price', 0)
            
            if current_price == 0:
                return None
            
            # Log technical analysis reasoning
            await self.decision_logger.log_technical_analysis(decision_id, {
                'rsi': setup.get('rsi_data', {}),
                'vwap': setup.get('vwap_data', {}),
                'macd': setup.get('macd_data', {}),
                'volume_data': setup.get('volume_data', {})
            })
            
            # Log sentiment analysis reasoning
            await self.decision_logger.log_sentiment_analysis(decision_id, {
                'sentiment_score': sentiment.get('sentiment_score', 0),
                'news_sentiment': sentiment.get('news_sentiment', 'neutral'),
                'news_count': len(sentiment.get('news_articles', [])),
                'social_sentiment': sentiment.get('social_media', {})
            })
            
            # Log market context
            await self.decision_logger.log_market_context(decision_id, {
                'market_trend': setup.get('market_conditions', {}).get('trend', 'neutral'),
                'vix_level': setup.get('market_conditions', {}).get('vix_level', 'normal'),
                'time_of_day': self._get_market_session(),
                'sector_performance': setup.get('market_conditions', {}).get('sector_performance', {})
            })
            
            # Extract enhanced technical signals
            technical_signals = self._extract_enhanced_technical_signals(setup)
            sentiment_signals = self._extract_enhanced_sentiment_signals(sentiment)
            market_context = self._extract_market_context(setup)
            
            # Use AI learning engine for adaptive confidence calculation
            ai_confidence = self.learning_engine.get_adaptive_confidence_score(
                technical_signals, sentiment_signals, market_context
            )
            
            # Log confidence calculation
            await self.decision_logger.log_reasoning_step(
                decision_id, 'ai_confidence_calculation',
                {
                    'technical_signals': technical_signals,
                    'sentiment_signals': sentiment_signals,
                    'market_context': market_context,
                    'ai_confidence': ai_confidence,
                    'reasoning': f"AI learning engine calculated confidence: {ai_confidence:.1f}/10"
                },
                0.0  # No additional impact, this is the final calculation
            )
            
            # Check if confidence meets adaptive threshold
            min_confidence = adaptive_thresholds.get('min_confidence_score', 7.0)
            if ai_confidence < min_confidence:
                await self.decision_logger.log_reasoning_step(
                    decision_id, 'confidence_insufficient',
                    {
                        'ai_confidence': ai_confidence,
                        'required_confidence': min_confidence,
                        'reasoning': f"Confidence {ai_confidence:.1f} below adaptive threshold {min_confidence:.1f}"
                    },
                    0.0
                )
                return None
            
            # Create enhanced recommendation
            recommendation = {
                'ticker': ticker,
                'entry_price': current_price,
                'timestamp': datetime.now().isoformat(),
                'setup_type': self._identify_setup_type(setup),
                'confidence': ai_confidence,
                'technical_signals': technical_signals,
                'sentiment_signals': sentiment_signals,
                'market_context': market_context,
                'adaptive_thresholds': adaptive_thresholds,
                'decision_id': decision_id
            }
            
            # Calculate position size using AI confidence
            position_size = self._calculate_adaptive_position_size(current_price, ai_confidence, adaptive_thresholds)
            recommendation['position_size'] = position_size
            
            # Calculate trade levels with adaptive parameters
            trade_levels = self._calculate_adaptive_trade_levels(setup, ai_confidence, adaptive_thresholds)
            recommendation.update(trade_levels)
            
            # Add AI prediction data
            expected_move = self._calculate_ai_expected_move(setup, sentiment, ai_confidence)
            recommendation['expected_move'] = expected_move
            recommendation['expected_outcome'] = {
                'direction': 'up' if expected_move > 0 else 'down',
                'price_move_percent': abs(expected_move),
                'duration_hours': self._estimate_trade_duration(setup, ai_confidence),
                'success_probability': min(ai_confidence / 10.0, 0.95)
            }
            
            # Identify key factors and risks
            recommendation['key_factors'] = self._identify_key_factors(technical_signals, sentiment_signals)
            recommendation['risk_factors'] = self._identify_risk_factors(setup, market_context)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error in AI-enhanced setup analysis: {e}")
            return None
    
    def _extract_enhanced_technical_signals(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enhanced technical signals for AI learning."""
        rsi_data = setup.get('rsi_data', {})
        vwap_data = setup.get('vwap_data', {})
        macd_data = setup.get('macd_data', {})
        volume_data = setup.get('volume_data', {})
        
        return {
            'rsi': {
                'present': rsi_data.get('rsi_value', 50) <= 30,
                'value': rsi_data.get('rsi_value', 50),
                'is_oversold': rsi_data.get('rsi_value', 50) <= 30,
                'is_overbought': rsi_data.get('rsi_value', 50) >= 70
            },
            'vwap': {
                'present': vwap_data.get('distance_from_vwap', 0) < -0.01,
                'price_vs_vwap': vwap_data.get('distance_from_vwap', 0),
                'is_bounce': vwap_data.get('distance_from_vwap', 0) < -0.01
            },
            'macd': {
                'present': macd_data.get('is_bullish_cross', False),
                'macd': macd_data.get('macd_value', 0),
                'signal': macd_data.get('signal_value', 0),
                'is_bullish_cross': macd_data.get('is_bullish_cross', False)
            },
            'volume_data': {
                'spike': volume_data.get('volume_ratio', 1) >= 2.0,
                'volume_ratio': volume_data.get('volume_ratio', 1),
                'avg_volume': volume_data.get('avg_volume', 0),
                'current_volume': volume_data.get('current_volume', 0)
            }
        }
    
    def _extract_enhanced_sentiment_signals(self, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enhanced sentiment signals for AI learning."""
        return {
            'sentiment_score': sentiment.get('sentiment_score', 0),
            'news_sentiment': sentiment.get('news_sentiment', 'neutral'),
            'social_media_sentiment': sentiment.get('social_media', {}).get('sentiment', 'neutral'),
            'news_count': len(sentiment.get('news_articles', [])),
            'sentiment_confidence': sentiment.get('confidence', 0.5)
        }
    
    def _extract_market_context(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """Extract market context for AI learning."""
        market_conditions = setup.get('market_conditions', {})
        
        return {
            'market_trend': market_conditions.get('trend', 'neutral'),
            'volatility_level': market_conditions.get('volatility', 'normal'),
            'is_volatile_session': market_conditions.get('volatility') == 'high',
            'sector_performance': market_conditions.get('sector_performance', {}),
            'time_of_day': self._get_market_session(),
            'economic_events': len(market_conditions.get('economic_events', []))
        }
    
    def _calculate_adaptive_position_size(self, price: float, confidence: float, 
                                        adaptive_thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Calculate position size based on AI confidence and adaptive learning."""
        # Base position size from config
        base_percentage = self.config.POSITION_SIZE_PERCENT
        
        # Adjust based on confidence (higher confidence = larger position)
        confidence_multiplier = min(confidence / 7.0, 1.5)  # Cap at 1.5x
        
        # Adjust based on learning performance
        learning_status = self.learning_engine.get_learning_status()
        current_metrics = learning_status.get('current_metrics', {})
        
        if current_metrics:
            win_rate = current_metrics.get('win_rate', 0.5)
            if win_rate > 0.7:  # High win rate, can be more aggressive
                learning_multiplier = 1.2
            elif win_rate < 0.4:  # Low win rate, be more conservative
                learning_multiplier = 0.7
            else:
                learning_multiplier = 1.0
        else:
            learning_multiplier = 1.0
        
        final_percentage = base_percentage * confidence_multiplier * learning_multiplier
        final_percentage = max(0.02, min(final_percentage, 0.15))  # Between 2% and 15%
        
        return {
            'percentage': final_percentage,
            'base_percentage': base_percentage,
            'confidence_multiplier': confidence_multiplier,
            'learning_multiplier': learning_multiplier,
            'reasoning': f'Position size: {final_percentage*100:.1f}% (base: {base_percentage*100:.1f}%, '
                        f'confidence: {confidence_multiplier:.2f}x, learning: {learning_multiplier:.2f}x)'
        }
    
    def _calculate_adaptive_trade_levels(self, setup: Dict[str, Any], confidence: float,
                                       adaptive_thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Calculate trade levels using adaptive parameters."""
        current_price = setup.get('current_price', 0)
        
        # Get adaptive stop loss and take profit levels
        base_stop_percent = 0.03  # 3% base stop
        base_target_percent = 0.06  # 6% base target
        
        # Adjust based on confidence
        if confidence >= 9.0:  # Very high confidence
            stop_percent = base_stop_percent * 0.8  # Tighter stop
            target_percent = base_target_percent * 1.3  # Higher target
        elif confidence <= 7.5:  # Lower confidence
            stop_percent = base_stop_percent * 1.2  # Wider stop
            target_percent = base_target_percent * 0.9  # Lower target
        else:
            stop_percent = base_stop_percent
            target_percent = base_target_percent
        
        entry_price = current_price
        stop_loss = entry_price * (1 - stop_percent)
        take_profit = entry_price * (1 + target_percent)
        
        return {
            'entry': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward_ratio': target_percent / stop_percent,
            'stop_percent': stop_percent,
            'target_percent': target_percent
        }
    
    def _calculate_ai_expected_move(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                  confidence: float) -> float:
        """Calculate expected price move using AI analysis."""
        # Base expected move from technical indicators
        rsi_value = setup.get('rsi_data', {}).get('rsi_value', 50)
        vwap_distance = setup.get('vwap_data', {}).get('distance_from_vwap', 0)
        
        base_move = 0.03  # 3% base expectation
        
        # Adjust for RSI oversold condition
        if rsi_value <= 30:
            base_move += (30 - rsi_value) / 30 * 0.02  # Up to 2% additional
        
        # Adjust for VWAP distance
        if vwap_distance < -0.02:  # 2% below VWAP
            base_move += abs(vwap_distance) * 0.5  # Partial reversion expectation
        
        # Adjust for sentiment
        sentiment_score = sentiment.get('sentiment_score', 0)
        if sentiment_score > 0.3:
            base_move += sentiment_score * 0.02  # Up to 2% from strong sentiment
        
        # Adjust for confidence
        confidence_multiplier = confidence / 7.0  # Scale based on confidence
        
        return base_move * confidence_multiplier
    
    def _estimate_trade_duration(self, setup: Dict[str, Any], confidence: float) -> float:
        """Estimate expected trade duration in hours."""
        # Base duration expectations
        setup_type = self._identify_setup_type(setup)
        
        if 'VWAP' in setup_type:
            base_hours = 4  # VWAP bounces often quick
        elif 'RSI' in setup_type:
            base_hours = 8  # RSI oversold can take longer
        elif 'Volume' in setup_type:
            base_hours = 2  # Volume breakouts often immediate
        else:
            base_hours = 6  # Default
        
        # Adjust for confidence (higher confidence = potentially faster moves)
        if confidence >= 9.0:
            base_hours *= 0.7
        elif confidence <= 7.0:
            base_hours *= 1.3
        
        return base_hours
    
    def _identify_key_factors(self, technical_signals: Dict[str, Any], 
                            sentiment_signals: Dict[str, Any]) -> List[str]:
        """Identify the key factors driving the trade decision."""
        factors = []
        
        if technical_signals.get('rsi', {}).get('is_oversold'):
            factors.append('RSI oversold condition')
        
        if technical_signals.get('vwap', {}).get('is_bounce'):
            factors.append('VWAP bounce setup')
        
        if technical_signals.get('macd', {}).get('is_bullish_cross'):
            factors.append('MACD bullish crossover')
        
        if technical_signals.get('volume_data', {}).get('spike'):
            factors.append('Volume spike confirmation')
        
        if sentiment_signals.get('news_sentiment') == 'bullish':
            factors.append('Positive news sentiment')
        
        return factors
    
    def _identify_risk_factors(self, setup: Dict[str, Any], market_context: Dict[str, Any]) -> List[str]:
        """Identify potential risk factors for the trade."""
        risks = []
        
        if market_context.get('volatility_level') == 'high':
            risks.append('High market volatility')
        
        if market_context.get('market_trend') == 'bearish':
            risks.append('Overall bearish market trend')
        
        if setup.get('current_price', 0) > self.config.TICKER_PRICE_MAX * 0.8:
            risks.append('Price near upper limit')
        
        if self.daily_trade_count >= self.config.MAX_DAILY_TRADES * 0.8:
            risks.append('Approaching daily trade limit')
        
        return risks
    
    def _create_prediction_from_recommendation(self, recommendation: Dict[str, Any], 
                                             setup: Dict[str, Any], sentiment: Dict[str, Any]) -> TradePrediction:
        """Create a prediction object for learning system."""
        return TradePrediction(
            ticker=recommendation['ticker'],
            predicted_direction='up',  # Focus on long trades
            predicted_move_percent=recommendation['expected_move'],
            predicted_timeframe_hours=recommendation['expected_outcome']['duration_hours'],
            confidence_score=recommendation['confidence'],
            reasoning_factors=recommendation['key_factors'],
            technical_signals=recommendation['technical_signals'],
            sentiment_signals=recommendation['sentiment_signals'],
            market_context=recommendation['market_context'],
            timestamp=datetime.now()
        )
    
    def _validate_recommendation(self, recommendation: Dict[str, Any], 
                               adaptive_thresholds: Dict[str, float]) -> bool:
        """Enhanced validation using adaptive thresholds."""
        try:
            # Check adaptive minimum confidence
            confidence = recommendation.get('confidence', 0)
            min_confidence = adaptive_thresholds.get('min_confidence_score', 7.0)
            if confidence < min_confidence:
                logger.warning(f"Confidence {confidence} < adaptive minimum {min_confidence}")
                return False
            
            # Check minimum R:R ratio
            rr_ratio = recommendation.get('risk_reward_ratio', 0)
            if rr_ratio < self.config.RR_THRESHOLD:
                logger.warning(f"R:R ratio {rr_ratio} < threshold {self.config.RR_THRESHOLD}")
                return False
            
            # Check price range
            entry_price = recommendation.get('entry', 0)
            if not (self.config.TICKER_PRICE_MIN <= entry_price <= self.config.TICKER_PRICE_MAX):
                logger.warning(f"Entry price {entry_price} outside range [{self.config.TICKER_PRICE_MIN}, {self.config.TICKER_PRICE_MAX}]")
                return False
            
            # Check position size is reasonable
            position_size = recommendation.get('position_size', {}).get('percentage', 0)
            if position_size <= 0 or position_size > 0.2:  # Max 20%
                logger.warning(f"Position size {position_size} outside valid range (0, 0.2]")
                return False
            
            # Check if we have too many risk factors
            risk_factors = recommendation.get('risk_factors', [])
            if len(risk_factors) > 3:
                logger.warning(f"Too many risk factors ({len(risk_factors)}) for trade")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating recommendation: {e}")
            return False
    
    def _get_market_session(self) -> str:
        """Get current market session."""
        hour = datetime.now().hour
        
        if 9 <= hour < 10:
            return 'market_open'
        elif 10 <= hour < 12:
            return 'morning_session'
        elif 12 <= hour < 14:
            return 'midday_session'
        elif 14 <= hour < 16:
            return 'afternoon_session'
        else:
            return 'after_hours'
    
    async def record_trade_outcome(self, recommendation: Dict[str, Any], outcome: Dict[str, Any]) -> None:
        """Record the outcome of a trade for AI learning."""
        try:
            prediction_id = recommendation.get('prediction_id')
            decision_id = recommendation.get('decision_id')
            
            if prediction_id:
                # Record outcome for learning engine
                from services.ai_learning_engine import TradeOutcome
                
                trade_outcome = TradeOutcome(
                    trade_id=prediction_id,
                    ticker=recommendation['ticker'],
                    entry_price=outcome.get('entry_price', 0),
                    exit_price=outcome.get('exit_price', 0),
                    actual_move_percent=outcome.get('move_percent', 0),
                    actual_duration_hours=outcome.get('duration_hours', 0),
                    exit_reason=outcome.get('exit_reason', 'unknown'),
                    max_favorable_excursion=outcome.get('max_favorable_excursion', 0),
                    max_adverse_excursion=outcome.get('max_adverse_excursion', 0),
                    prediction_accuracy=outcome.get('prediction_accuracy', 0),
                    success=outcome.get('success', False),
                    timestamp=datetime.now()
                )
                
                await self.learning_engine.record_outcome(trade_outcome)
            
            if decision_id:
                # Record outcome for decision logger
                await self.decision_logger.log_decision_outcome(decision_id, outcome)
            
            logger.info(f"Recorded trade outcome for {recommendation['ticker']}: "
                       f"{'SUCCESS' if outcome.get('success') else 'LOSS'}")
            
        except Exception as e:
            logger.error(f"Error recording trade outcome: {e}")
