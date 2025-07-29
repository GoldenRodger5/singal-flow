"""
Debug trade recommender validation
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.trade_recommender_agent import TradeRecommenderAgent
from services.config import Config

async def debug_recommender():
    config = Config()
    print(f"MIN_CONFIDENCE_SCORE: {config.MIN_CONFIDENCE_SCORE}")
    print(f"RR_THRESHOLD: {config.RR_THRESHOLD}")
    print(f"TICKER_PRICE_MIN: {config.TICKER_PRICE_MIN}")
    print(f"TICKER_PRICE_MAX: {config.TICKER_PRICE_MAX}")
    
    recommender = TradeRecommenderAgent()
    
    # Create mock setup data with higher confidence
    mock_setup = {
        'ticker': 'SIRI',  # Use a cheaper stock
        'current_price': 25.50,  # Within range
        'setup_score': 8,  # Higher score
        'setup_reasons': ['RSI oversold at 28.5', 'VWAP bounce detected'],
        'confidence': 8.5,  # Higher confidence
        'rsi': {'is_oversold': True, 'rsi_value': 28.5},
        'vwap': {'is_bounce': True, 'distance': 0.01},
        'macd': {'is_bullish_cross': True},
        'volume_data': {'spike': True, 'current': 50000, 'average': 25000},
        'risk_reward': {'stop_loss': 24.0, 'take_profit': 28.0, 'rr_ratio': 2.2},
        'is_volatile_session': True
    }
    
    mock_sentiment = {
        'news_sentiment': 'bullish',
        'sentiment_score': 0.6,
        'sentiment_confidence': 0.8,
        'news_count': 3
    }
    
    # Manual confidence calculation to debug
    base_confidence = mock_setup.get('confidence', 0)
    print(f"Base confidence from setup: {base_confidence}")
    
    # Calculate sentiment impact
    sentiment_score = mock_sentiment.get('sentiment_score', 0)
    sentiment_confidence = mock_sentiment.get('sentiment_confidence', 0)
    sentiment_impact = sentiment_confidence * 1.5  # Bullish with score > 0.3
    print(f"Sentiment impact: {sentiment_impact}")
    
    # R:R bonus
    rr_ratio = mock_setup.get('risk_reward', {}).get('rr_ratio', 0)
    rr_bonus = min(2.0, (rr_ratio - 2.0) * 0.5) if rr_ratio > 2.0 else 0
    print(f"R:R bonus: {rr_bonus}")
    
    # Volume bonus
    volume_bonus = 0.5 if mock_setup.get('volume_data', {}).get('spike', False) else 0
    print(f"Volume bonus: {volume_bonus}")
    
    # Signal bonus
    setup_score = mock_setup.get('setup_score', 0)
    signal_bonus = min(1.0, (setup_score - 3) * 0.2) if setup_score > 3 else 0
    print(f"Signal bonus: {signal_bonus}")
    
    # Volatility bonus
    volatility_bonus = 0.3 if mock_setup.get('is_volatile_session', False) else 0
    print(f"Volatility bonus: {volatility_bonus}")
    
    expected_confidence = base_confidence + sentiment_impact + rr_bonus + volume_bonus + signal_bonus + volatility_bonus
    print(f"Expected final confidence: {expected_confidence}")
    
    recommendation = await recommender.evaluate_setup(mock_setup, mock_sentiment)
    
    if recommendation:
        print(f"✅ Recommendation successful!")
        print(f"   Confidence: {recommendation.get('confidence')}")
        print(f"   R:R Ratio: {recommendation.get('risk_reward_ratio')}")
        print(f"   Entry: {recommendation.get('entry')}")
        print(f"   Position Size: {recommendation.get('position_size')}")
        
        # Check each validation criteria
        print("\n--- Validation Check ---")
        conf = recommendation.get('confidence', 0)
        rr = recommendation.get('risk_reward_ratio', 0)
        entry = recommendation.get('entry', 0)
        pos_size = recommendation.get('position_size', {}).get('percentage', 0)
        stop = recommendation.get('stop_loss', 0)
        target = recommendation.get('take_profit', 0)
        
        print(f"Confidence {conf} >= {config.MIN_CONFIDENCE_SCORE}? {conf >= config.MIN_CONFIDENCE_SCORE}")
        print(f"R:R {rr} >= {config.RR_THRESHOLD}? {rr >= config.RR_THRESHOLD}")
        print(f"Price {entry} in range [{config.TICKER_PRICE_MIN}, {config.TICKER_PRICE_MAX}]? {config.TICKER_PRICE_MIN <= entry <= config.TICKER_PRICE_MAX}")
        print(f"Position size {pos_size} in range (0, 0.2]? {0 < pos_size <= 0.2}")
        print(f"Levels logical {stop} < {entry} < {target}? {stop < entry < target}")
        
    else:
        print("❌ Recommendation failed validation")

if __name__ == "__main__":
    asyncio.run(debug_recommender())
