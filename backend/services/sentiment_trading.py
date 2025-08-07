"""
AI Sentiment-Driven Trading Engine
Leverages Polygon.io News API with sentiment analysis for profitable trades
Based on Polygon.io sentiment analysis research
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
import os

@dataclass
class SentimentSignal:
    """Trading signal based on sentiment analysis."""
    symbol: str
    sentiment_score: float     # -1 to 1 (negative to positive)
    sentiment_strength: float  # 0-1 (weak to strong)
    news_volume: int          # Number of articles
    signal_type: str          # 'BUY', 'SELL', 'HOLD'
    confidence: float         # 0-100%
    key_headlines: List[str]
    price_impact_estimate: float  # Expected % price movement
    timeframe: str            # 'immediate', 'short_term', 'medium_term'
    timestamp: datetime

@dataclass
class NewsInsight:
    """Individual news insight."""
    ticker: str
    sentiment: str
    sentiment_reasoning: str
    headline: str
    published_time: datetime
    relevance_score: float

class SentimentTradingEngine:
    """
    AI-powered sentiment analysis trading engine.
    Uses Polygon.io's enhanced Ticker News API with sentiment insights.
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        self.session = None
        
        # Sentiment trading thresholds
        self.strong_sentiment_threshold = 0.7
        self.minimum_news_volume = 3
        self.recency_hours = 4  # Only consider news from last 4 hours
        
        # Impact estimation coefficients (based on backtesting)
        self.sentiment_impact_multiplier = 2.5
        self.news_volume_multiplier = 0.3
        
        logger.info("📰 AI Sentiment Trading Engine initialized")
        logger.info("🤖 Using Polygon.io enhanced sentiment analysis")
    
    async def __aenter__(self):
        """Async context manager."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager cleanup."""
        if self.session:
            await self.session.close()
    
    async def analyze_sentiment_signals(self, watchlist: List[str]) -> List[SentimentSignal]:
        """Analyze sentiment signals for watchlist."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        sentiment_signals = []
        
        for symbol in watchlist:
            try:
                signal = await self._generate_sentiment_signal(symbol)
                if signal and signal.confidence > 70:
                    sentiment_signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error analyzing sentiment for {symbol}: {e}")
        
        # Sort by confidence
        sentiment_signals.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"📊 Generated {len(sentiment_signals)} high-confidence sentiment signals")
        return sentiment_signals
    
    async def _generate_sentiment_signal(self, symbol: str) -> Optional[SentimentSignal]:
        """Generate sentiment signal for individual stock."""
        try:
            # Get recent news with sentiment insights
            news_insights = await self._get_sentiment_insights(symbol)
            if not news_insights or len(news_insights) < self.minimum_news_volume:
                return None
            
            # Calculate aggregate sentiment metrics
            sentiment_metrics = self._calculate_sentiment_metrics(news_insights)
            
            # Determine trading signal
            signal_type, confidence = self._determine_trading_signal(sentiment_metrics)
            
            if confidence < 70:
                return None
            
            # Estimate price impact
            price_impact = self._estimate_price_impact(sentiment_metrics, news_insights)
            
            # Determine timeframe
            timeframe = self._determine_timeframe(sentiment_metrics, news_insights)
            
            # Get key headlines
            key_headlines = [insight.headline for insight in news_insights[:3]]
            
            return SentimentSignal(
                symbol=symbol,
                sentiment_score=sentiment_metrics['avg_sentiment'],
                sentiment_strength=sentiment_metrics['sentiment_strength'],
                news_volume=len(news_insights),
                signal_type=signal_type,
                confidence=confidence,
                key_headlines=key_headlines,
                price_impact_estimate=price_impact,
                timeframe=timeframe,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating sentiment signal for {symbol}: {e}")
            return None
    
    async def _get_sentiment_insights(self, symbol: str) -> List[NewsInsight]:
        """Get recent news with sentiment insights."""
        try:
            # Get recent news (last 4 hours for maximum relevance)
            cutoff_time = datetime.now() - timedelta(hours=self.recency_hours)
            
            url = f"{self.base_url}/v2/reference/news"
            params = {
                'apikey': self.api_key,
                'ticker': symbol,
                'published_utc.gte': cutoff_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'order': 'desc',
                'limit': 50
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                news_insights = []
                
                if 'results' in data:
                    for article in data['results']:
                        insights = article.get('insights', [])
                        
                        for insight in insights:
                            if insight.get('ticker') == symbol:
                                news_insight = NewsInsight(
                                    ticker=symbol,
                                    sentiment=insight.get('sentiment', 'neutral'),
                                    sentiment_reasoning=insight.get('sentiment_reasoning', ''),
                                    headline=article.get('title', ''),
                                    published_time=datetime.fromisoformat(
                                        article.get('published_utc', '').replace('Z', '+00:00')
                                    ),
                                    relevance_score=self._calculate_relevance_score(insight, article)
                                )
                                news_insights.append(news_insight)
                
                # Filter and sort by relevance
                relevant_insights = [
                    insight for insight in news_insights 
                    if insight.relevance_score > 0.3
                ]
                
                relevant_insights.sort(key=lambda x: x.relevance_score, reverse=True)
                return relevant_insights[:20]  # Top 20 most relevant
                
        except Exception as e:
            logger.error(f"Error getting sentiment insights for {symbol}: {e}")
            return []
    
    def _calculate_relevance_score(self, insight: Dict, article: Dict) -> float:
        """Calculate relevance score for news insight."""
        score = 0.5  # Base score
        
        # Boost score based on sentiment strength
        sentiment_reasoning = insight.get('sentiment_reasoning', '').lower()
        
        # Strong positive/negative indicators
        strong_positive = ['major', 'significant', 'breakthrough', 'partnership', 'acquisition', 'beat', 'upgrade']
        strong_negative = ['lawsuit', 'investigation', 'downgrade', 'loss', 'bankruptcy', 'scandal', 'recall']
        
        for word in strong_positive:
            if word in sentiment_reasoning:
                score += 0.2
        
        for word in strong_negative:
            if word in sentiment_reasoning:
                score += 0.2
        
        # Boost for recent articles
        published_time = datetime.fromisoformat(article.get('published_utc', '').replace('Z', '+00:00'))
        hours_ago = (datetime.now(published_time.tzinfo) - published_time).total_seconds() / 3600
        
        if hours_ago < 1:
            score += 0.3  # Very recent
        elif hours_ago < 2:
            score += 0.2  # Recent
        elif hours_ago < 4:
            score += 0.1  # Somewhat recent
        
        return min(1.0, score)
    
    def _calculate_sentiment_metrics(self, insights: List[NewsInsight]) -> Dict:
        """Calculate aggregate sentiment metrics."""
        if not insights:
            return {}
        
        # Convert sentiment to numeric values
        sentiment_values = []
        for insight in insights:
            if insight.sentiment == 'positive':
                sentiment_values.append(1.0 * insight.relevance_score)
            elif insight.sentiment == 'negative':
                sentiment_values.append(-1.0 * insight.relevance_score)
            else:  # neutral
                sentiment_values.append(0.0)
        
        # Calculate weighted average
        total_weight = sum(insight.relevance_score for insight in insights)
        weighted_sentiment = sum(sentiment_values) / total_weight if total_weight > 0 else 0
        
        # Calculate sentiment strength (how strong the sentiment is)
        abs_sentiments = [abs(val) for val in sentiment_values]
        sentiment_strength = sum(abs_sentiments) / len(abs_sentiments) if abs_sentiments else 0
        
        # Calculate sentiment consistency (all positive/negative vs mixed)
        positive_count = sum(1 for val in sentiment_values if val > 0)
        negative_count = sum(1 for val in sentiment_values if val < 0)
        total_count = len(sentiment_values)
        
        if total_count > 0:
            consistency = max(positive_count, negative_count) / total_count
        else:
            consistency = 0
        
        return {
            'avg_sentiment': weighted_sentiment,
            'sentiment_strength': sentiment_strength,
            'consistency': consistency,
            'positive_ratio': positive_count / total_count if total_count > 0 else 0,
            'negative_ratio': negative_count / total_count if total_count > 0 else 0
        }
    
    def _determine_trading_signal(self, metrics: Dict) -> Tuple[str, float]:
        """Determine trading signal and confidence."""
        if not metrics:
            return 'HOLD', 0
        
        sentiment = metrics['avg_sentiment']
        strength = metrics['sentiment_strength']
        consistency = metrics['consistency']
        
        # Base confidence on sentiment strength and consistency
        confidence = (strength * 50) + (consistency * 30) + 20
        
        # Determine signal type
        if sentiment > 0.3 and strength > 0.5:
            signal_type = 'BUY'
            confidence += 10  # Boost for positive sentiment
        elif sentiment < -0.3 and strength > 0.5:
            signal_type = 'SELL'  
            confidence += 10  # Boost for negative sentiment
        else:
            signal_type = 'HOLD'
            confidence *= 0.7  # Reduce confidence for hold signals
        
        # Cap confidence at 100%
        confidence = min(100, confidence)
        
        return signal_type, confidence
    
    def _estimate_price_impact(self, metrics: Dict, insights: List[NewsInsight]) -> float:
        """Estimate potential price impact."""
        if not metrics or not insights:
            return 0
        
        # Base impact on sentiment score and strength
        base_impact = abs(metrics['avg_sentiment']) * metrics['sentiment_strength'] * self.sentiment_impact_multiplier
        
        # Adjust for news volume
        volume_adjustment = min(len(insights) * self.news_volume_multiplier, 2.0)
        
        # Adjust for recency (more recent = higher impact)
        recency_adjustment = 1.0
        recent_insights = [i for i in insights if (datetime.now() - i.published_time).total_seconds() < 3600]
        if recent_insights:
            recency_adjustment = 1 + (len(recent_insights) / len(insights)) * 0.5
        
        total_impact = base_impact * volume_adjustment * recency_adjustment
        
        # Cap at reasonable maximum
        return min(total_impact, 15.0)  # Max 15% price impact estimate
    
    def _determine_timeframe(self, metrics: Dict, insights: List[NewsInsight]) -> str:
        """Determine expected timeframe for price impact."""
        if not insights:
            return 'medium_term'
        
        # Count very recent insights (last hour)
        very_recent = sum(1 for i in insights if (datetime.now() - i.published_time).total_seconds() < 3600)
        recent = sum(1 for i in insights if (datetime.now() - i.published_time).total_seconds() < 7200)  # 2 hours
        
        if very_recent >= 2:
            return 'immediate'  # Multiple very recent articles
        elif recent >= 3:
            return 'short_term'  # Several recent articles
        else:
            return 'medium_term'  # General sentiment shift
    
    async def monitor_sentiment_changes(self, active_symbols: List[str]) -> Dict[str, Dict]:
        """Monitor sentiment changes for active positions."""
        changes = {}
        
        for symbol in active_symbols:
            try:
                current_signal = await self._generate_sentiment_signal(symbol)
                if current_signal:
                    changes[symbol] = {
                        'sentiment_score': current_signal.sentiment_score,
                        'sentiment_strength': current_signal.sentiment_strength,
                        'signal_type': current_signal.signal_type,
                        'confidence': current_signal.confidence,
                        'news_volume': current_signal.news_volume,
                        'timestamp': current_signal.timestamp
                    }
                    
            except Exception as e:
                logger.error(f"Error monitoring sentiment for {symbol}: {e}")
        
        return changes

# Global instance - will be created when needed
sentiment_engine = None

def get_sentiment_engine():
    """Get or create the sentiment engine instance."""
    global sentiment_engine
    if sentiment_engine is None:
        sentiment_engine = SentimentTradingEngine()
    return sentiment_engine

# Export
__all__ = ['get_sentiment_engine', 'sentiment_engine', 'SentimentTradingEngine', 'SentimentSignal', 'NewsInsight']
