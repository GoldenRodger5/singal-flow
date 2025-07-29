"""
Sentiment Agent - Analyzes market sentiment from news and social sources.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
from loguru import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from services.config import Config
from services.data_provider import PolygonDataProvider


class SentimentAgent:
    """Agent for analyzing market sentiment from various sources."""
    
    def __init__(self):
        """Initialize the sentiment agent."""
        self.config = Config()
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize AI clients
        if OPENAI_AVAILABLE and self.config.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
        
        if ANTHROPIC_AVAILABLE and self.config.CLAUDE_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=self.config.CLAUDE_API_KEY)
    
    async def analyze_ticker(self, ticker: str) -> Dict[str, Any]:
        """Analyze sentiment for a specific ticker."""
        try:
            logger.info(f"Analyzing sentiment for {ticker}")
            
            sentiment_data = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'news_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'sentiment_confidence': 0.0,
                'news_count': 0,
                'key_themes': [],
                'risk_factors': []
            }
            
            # Get recent news
            async with PolygonDataProvider() as data_provider:
                news_articles = await data_provider.get_news(ticker, limit=10)
            
            if not news_articles:
                logger.warning(f"No news found for {ticker}")
                return sentiment_data
            
            sentiment_data['news_count'] = len(news_articles)
            
            # Analyze news sentiment
            news_sentiment = await self._analyze_news_sentiment(news_articles, ticker)
            sentiment_data.update(news_sentiment)
            
            # Get market context sentiment
            market_sentiment = await self._analyze_market_context(ticker)
            sentiment_data.update(market_sentiment)
            
            logger.info(f"Sentiment analysis complete for {ticker}: {sentiment_data['news_sentiment']} ({sentiment_data['sentiment_score']:.2f})")
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {ticker}: {e}")
            return {
                'ticker': ticker,
                'news_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'sentiment_confidence': 0.0,
                'error': str(e)
            }
    
    async def _analyze_news_sentiment(self, news_articles: List[Dict], ticker: str) -> Dict[str, Any]:
        """Analyze sentiment from news articles using AI."""
        try:
            if not news_articles:
                return {
                    'news_sentiment': 'neutral',
                    'sentiment_score': 0.0,
                    'sentiment_confidence': 0.0
                }
            
            # Prepare news text for analysis
            news_text = self._prepare_news_text(news_articles)
            
            # Use AI for sentiment analysis
            if self.openai_client:
                return await self._analyze_with_openai(news_text, ticker)
            elif self.anthropic_client:
                return await self._analyze_with_claude(news_text, ticker)
            else:
                # Fallback to basic keyword analysis
                return self._basic_sentiment_analysis(news_text)
                
        except Exception as e:
            logger.error(f"Error in news sentiment analysis: {e}")
            return {
                'news_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'sentiment_confidence': 0.0
            }
    
    def _prepare_news_text(self, news_articles: List[Dict]) -> str:
        """Prepare news articles for sentiment analysis."""
        news_text = ""
        for article in news_articles[:5]:  # Limit to top 5 articles
            title = article.get('title', '')
            description = article.get('description', '')
            
            if title:
                news_text += f"Title: {title}\n"
            if description:
                news_text += f"Description: {description}\n"
            news_text += "\n"
        
        return news_text[:2000]  # Limit text length
    
    async def _analyze_with_openai(self, news_text: str, ticker: str) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI."""
        try:
            prompt = f"""
            Analyze the sentiment of this news about {ticker} for day trading purposes.
            
            News text:
            {news_text}
            
            Provide:
            1. Overall sentiment (bullish/bearish/neutral)
            2. Sentiment score (-1.0 to 1.0, where -1 is very bearish, 1 is very bullish)
            3. Confidence level (0.0 to 1.0)
            4. Key themes (up to 3)
            5. Risk factors (up to 3)
            
            Format as JSON:
            {{
                "sentiment": "bullish/bearish/neutral",
                "score": 0.0,
                "confidence": 0.0,
                "themes": ["theme1", "theme2"],
                "risks": ["risk1", "risk2"]
            }}
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                result = json.loads(content)
                return {
                    'news_sentiment': result.get('sentiment', 'neutral'),
                    'sentiment_score': float(result.get('score', 0.0)),
                    'sentiment_confidence': float(result.get('confidence', 0.0)),
                    'key_themes': result.get('themes', []),
                    'risk_factors': result.get('risks', [])
                }
            except json.JSONDecodeError:
                # Fallback parsing
                return self._parse_ai_response(content)
                
        except Exception as e:
            logger.error(f"Error with OpenAI sentiment analysis: {e}")
            return self._basic_sentiment_analysis(news_text)
    
    async def _analyze_with_claude(self, news_text: str, ticker: str) -> Dict[str, Any]:
        """Analyze sentiment using Claude."""
        try:
            prompt = f"""
            Analyze the sentiment of this news about {ticker} for day trading purposes.
            
            News text:
            {news_text}
            
            Provide a brief analysis with:
            1. Overall sentiment (bullish/bearish/neutral)
            2. Sentiment score (-1.0 to 1.0)
            3. Confidence level (0.0 to 1.0)
            4. Key themes
            5. Risk factors
            """
            
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            return self._parse_ai_response(content)
            
        except Exception as e:
            logger.error(f"Error with Claude sentiment analysis: {e}")
            return self._basic_sentiment_analysis(news_text)
    
    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """Parse AI response for sentiment data."""
        try:
            content_lower = content.lower()
            
            # Determine sentiment
            if 'bullish' in content_lower or 'positive' in content_lower:
                sentiment = 'bullish'
                base_score = 0.5
            elif 'bearish' in content_lower or 'negative' in content_lower:
                sentiment = 'bearish'
                base_score = -0.5
            else:
                sentiment = 'neutral'
                base_score = 0.0
            
            # Extract numerical values if present
            import re
            score_match = re.search(r'score[:\s]*(-?\d*\.?\d+)', content_lower)
            confidence_match = re.search(r'confidence[:\s]*(\d*\.?\d+)', content_lower)
            
            score = float(score_match.group(1)) if score_match else base_score
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            # Extract themes and risks
            themes = []
            risks = []
            
            lines = content.split('\n')
            for line in lines:
                if 'theme' in line.lower() or 'key' in line.lower():
                    themes.append(line.strip())
                elif 'risk' in line.lower():
                    risks.append(line.strip())
            
            return {
                'news_sentiment': sentiment,
                'sentiment_score': max(-1.0, min(1.0, score)),
                'sentiment_confidence': max(0.0, min(1.0, confidence)),
                'key_themes': themes[:3],
                'risk_factors': risks[:3]
            }
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {
                'news_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'sentiment_confidence': 0.0,
                'key_themes': [],
                'risk_factors': []
            }
    
    def _basic_sentiment_analysis(self, news_text: str) -> Dict[str, Any]:
        """Basic keyword-based sentiment analysis as fallback."""
        try:
            text_lower = news_text.lower()
            
            # Positive keywords
            positive_words = [
                'growth', 'profit', 'revenue', 'earnings', 'beat', 'exceed', 'strong',
                'positive', 'up', 'rise', 'gain', 'bull', 'optimistic', 'upgrade',
                'buy', 'outperform', 'breakthrough', 'success', 'expansion'
            ]
            
            # Negative keywords
            negative_words = [
                'loss', 'decline', 'fall', 'drop', 'bear', 'negative', 'weak',
                'poor', 'miss', 'below', 'concern', 'worry', 'risk', 'downgrade',
                'sell', 'underperform', 'failure', 'problem', 'issue'
            ]
            
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            # Calculate sentiment
            total_words = positive_count + negative_count
            if total_words == 0:
                sentiment = 'neutral'
                score = 0.0
            elif positive_count > negative_count:
                sentiment = 'bullish'
                score = min(0.8, (positive_count - negative_count) / total_words)
            elif negative_count > positive_count:
                sentiment = 'bearish'
                score = max(-0.8, -(negative_count - positive_count) / total_words)
            else:
                sentiment = 'neutral'
                score = 0.0
            
            confidence = min(0.7, total_words / 10.0)  # Lower confidence for basic analysis
            
            return {
                'news_sentiment': sentiment,
                'sentiment_score': score,
                'sentiment_confidence': confidence,
                'key_themes': [],
                'risk_factors': []
            }
            
        except Exception as e:
            logger.error(f"Error in basic sentiment analysis: {e}")
            return {
                'news_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'sentiment_confidence': 0.0,
                'key_themes': [],
                'risk_factors': []
            }
    
    async def _analyze_market_context(self, ticker: str) -> Dict[str, Any]:
        """Analyze broader market context for sentiment."""
        try:
            context = {}
            
            # Get market snapshot for additional context
            async with PolygonDataProvider() as data_provider:
                snapshot = await data_provider.get_market_snapshot(ticker)
                
                if snapshot and 'ticker' in snapshot:
                    ticker_data = snapshot['ticker']
                    day_data = ticker_data.get('day', {})
                    
                    # Analyze price action sentiment
                    day_change = day_data.get('c', 0)
                    if day_change > 2:
                        context['price_sentiment'] = 'bullish'
                    elif day_change < -2:
                        context['price_sentiment'] = 'bearish'
                    else:
                        context['price_sentiment'] = 'neutral'
                    
                    context['day_change'] = day_change
                    context['day_volume'] = day_data.get('v', 0)
            
            return context
            
        except Exception as e:
            logger.error(f"Error analyzing market context: {e}")
            return {}
    
    def get_sentiment_impact_on_confidence(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate how sentiment should impact trading confidence."""
        try:
            sentiment = sentiment_data.get('news_sentiment', 'neutral')
            score = sentiment_data.get('sentiment_score', 0.0)
            confidence = sentiment_data.get('sentiment_confidence', 0.0)
            
            # Bullish sentiment increases confidence for long positions
            if sentiment == 'bullish' and score > 0.3:
                return confidence * 2.0  # Up to +2 confidence points
            
            # Bearish sentiment decreases confidence for long positions
            elif sentiment == 'bearish' and score < -0.3:
                return -confidence * 1.5  # Up to -1.5 confidence points
            
            # Neutral or weak sentiment has minimal impact
            else:
                return confidence * 0.5  # Small boost for having news
                
        except Exception as e:
            logger.error(f"Error calculating sentiment impact: {e}")
            return 0.0
