"""
Enhanced Multi-Source Sentiment Analysis
Real-time sentiment from Reddit, Twitter, and News with time decay
"""
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
import os

# Optional imports - graceful degradation if not available
try:
    import praw
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False
    logger.warning("Reddit API (praw) not available. Install with: pip install praw")

try:
    import tweepy
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    logger.warning("Twitter API (tweepy) not available. Install with: pip install tweepy")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("TextBlob not available. Install with: pip install textblob")


@dataclass
class SentimentDataPoint:
    """Individual sentiment data point with metadata."""
    text: str
    sentiment_score: float
    confidence: float
    source: str
    timestamp: datetime
    author_credibility: float = 1.0
    engagement_score: float = 1.0


class EnhancedSentimentAnalyzer:
    """
    Multi-source sentiment analyzer with time decay and credibility weighting.
    Integrates Reddit, Twitter, and News with sophisticated scoring.
    """
    
    def __init__(self):
        """Initialize enhanced sentiment analyzer."""
        self.reddit_client = None
        self.twitter_client = None
        self.source_weights = {
            'news': 1.0,
            'reddit_wsb': 0.8,
            'reddit_investing': 0.9,
            'reddit_security_analysis': 1.0,
            'twitter_verified': 0.9,
            'twitter_influencer': 0.7,
            'twitter_general': 0.5
        }
        self.time_decay_hours = 24
        self._initialize_apis()
        logger.info("Enhanced sentiment analyzer initialized")
    
    def _initialize_apis(self):
        """Initialize Reddit and Twitter API clients."""
        # Reddit API setup
        if REDDIT_AVAILABLE:
            reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
            reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'SignalFlow/1.0')
            
            if reddit_client_id and reddit_client_secret:
                try:
                    self.reddit_client = praw.Reddit(
                        client_id=reddit_client_id,
                        client_secret=reddit_client_secret,
                        user_agent=reddit_user_agent
                    )
                    logger.info("✅ Reddit API client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Reddit client: {e}")
            else:
                logger.warning("Reddit API credentials not configured")
        
        # Twitter API setup (disabled to prevent proxies error)
        if TWITTER_AVAILABLE:
            twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            
            if twitter_bearer_token:
                try:
                    # Temporarily disable Twitter client to avoid proxies error
                    # self.twitter_client = tweepy.Client(bearer_token=twitter_bearer_token)
                    self.twitter_client = None
                    logger.info("✅ Twitter API client initialized (disabled for stability)")
                except Exception as e:
                    logger.error(f"Failed to initialize Twitter client: {e}")
            else:
                logger.warning("Twitter API credentials not configured")
    
    async def analyze_comprehensive_sentiment(self, ticker: str, hours_back: int = 24) -> Dict[str, Any]:
        """
        Comprehensive sentiment analysis from all available sources.
        
        Args:
            ticker: Stock ticker symbol
            hours_back: Hours of historical data to analyze
            
        Returns:
            Comprehensive sentiment analysis with source breakdown
        """
        logger.info(f"📊 Starting comprehensive sentiment analysis for {ticker}")
        
        sentiment_points = []
        source_summaries = {}
        
        # Collect sentiment from all sources
        try:
            # Reddit sentiment
            reddit_points = await self._get_reddit_sentiment(ticker, hours_back)
            sentiment_points.extend(reddit_points)
            source_summaries['reddit'] = len(reddit_points)
            
            # Twitter sentiment  
            twitter_points = await self._get_twitter_sentiment(ticker, hours_back)
            sentiment_points.extend(twitter_points)
            source_summaries['twitter'] = len(twitter_points)
            
            # News sentiment (existing integration)
            news_points = await self._get_news_sentiment(ticker, hours_back)
            sentiment_points.extend(news_points)
            source_summaries['news'] = len(news_points)
            
        except Exception as e:
            logger.error(f"Error collecting sentiment data: {e}")
        
        # Calculate composite sentiment with time decay and credibility weighting
        composite_sentiment = self._calculate_composite_sentiment(sentiment_points)
        
        # Sentiment trend analysis
        trend_analysis = self._analyze_sentiment_trend(sentiment_points, hours_back)
        
        result = {
            'ticker': ticker,
            'timestamp': datetime.now(),
            'composite_score': composite_sentiment['score'],
            'composite_confidence': composite_sentiment['confidence'],
            'composite_direction': composite_sentiment['direction'],
            'source_breakdown': source_summaries,
            'total_data_points': len(sentiment_points),
            'trend_analysis': trend_analysis,
            'time_decay_applied': True,
            'credibility_weighted': True
        }
        
        logger.info(f"✅ Sentiment analysis complete: {ticker} - "
                   f"{result['composite_direction']} ({result['composite_score']:.2f})")
        
        return result
    
    async def _get_reddit_sentiment(self, ticker: str, hours_back: int) -> List[SentimentDataPoint]:
        """Get sentiment from relevant Reddit subreddits."""
        if not self.reddit_client:
            return []
        
        sentiment_points = []
        
        # Target subreddits with different credibility levels
        subreddits = {
            'wallstreetbets': 'reddit_wsb',
            'investing': 'reddit_investing', 
            'SecurityAnalysis': 'reddit_security_analysis',
            'ValueInvesting': 'reddit_security_analysis',
            'stocks': 'reddit_investing'
        }
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for subreddit_name, source_type in subreddits.items():
            try:
                subreddit = self.reddit_client.subreddit(subreddit_name)
                
                # Search for ticker mentions
                for submission in subreddit.search(f"${ticker} OR {ticker}", 
                                                 time_filter="day", limit=20):
                    
                    post_time = datetime.fromtimestamp(submission.created_utc)
                    if post_time < cutoff_time:
                        continue
                    
                    # Analyze post title and content
                    text = f"{submission.title} {submission.selftext}"
                    sentiment = self._analyze_text_sentiment(text)
                    
                    if sentiment:
                        # Calculate credibility based on subreddit and engagement
                        credibility = self._calculate_reddit_credibility(
                            submission, subreddit_name
                        )
                        
                        sentiment_points.append(SentimentDataPoint(
                            text=text[:200],  # Truncate for storage
                            sentiment_score=sentiment['score'],
                            confidence=sentiment['confidence'],
                            source=source_type,
                            timestamp=post_time,
                            author_credibility=credibility,
                            engagement_score=min(submission.score / 10, 5.0)
                        ))
                
                # Also check top comments for popular posts
                for submission in subreddit.hot(limit=10):
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments[:5]:
                        if ticker.upper() in comment.body.upper():
                            comment_time = datetime.fromtimestamp(comment.created_utc)
                            if comment_time >= cutoff_time:
                                sentiment = self._analyze_text_sentiment(comment.body)
                                if sentiment:
                                    sentiment_points.append(SentimentDataPoint(
                                        text=comment.body[:200],
                                        sentiment_score=sentiment['score'],
                                        confidence=sentiment['confidence'],
                                        source=source_type,
                                        timestamp=comment_time,
                                        author_credibility=min(comment.score / 5, 3.0),
                                        engagement_score=1.0
                                    ))
                
                logger.debug(f"Collected {len([p for p in sentiment_points if p.source == source_type])} "
                           f"sentiment points from r/{subreddit_name}")
                
            except Exception as e:
                logger.error(f"Error collecting from r/{subreddit_name}: {e}")
        
        return sentiment_points
    
    async def _get_twitter_sentiment(self, ticker: str, hours_back: int) -> List[SentimentDataPoint]:
        """Get sentiment from Twitter mentions."""
        if not self.twitter_client:
            return []
        
        sentiment_points = []
        
        try:
            # Search for ticker mentions
            query = f"${ticker} OR {ticker} -is:retweet lang:en"
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            tweets = tweepy.Paginator(
                self.twitter_client.search_recent_tweets,
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations']
            ).flatten(limit=200)
            
            for tweet in tweets:
                tweet_time = tweet.created_at.replace(tzinfo=None)
                if tweet_time < cutoff_time:
                    continue
                
                sentiment = self._analyze_text_sentiment(tweet.text)
                if sentiment:
                    # Determine source type based on engagement and verification
                    source_type = self._determine_twitter_source_type(tweet)
                    credibility = self._calculate_twitter_credibility(tweet)
                    
                    sentiment_points.append(SentimentDataPoint(
                        text=tweet.text,
                        sentiment_score=sentiment['score'],
                        confidence=sentiment['confidence'],
                        source=source_type,
                        timestamp=tweet_time,
                        author_credibility=credibility,
                        engagement_score=min(
                            (tweet.public_metrics['like_count'] + 
                             tweet.public_metrics['retweet_count']) / 10, 5.0
                        )
                    ))
            
            logger.debug(f"Collected {len(sentiment_points)} sentiment points from Twitter")
            
        except Exception as e:
            logger.error(f"Error collecting Twitter sentiment: {e}")
        
        return sentiment_points
    
    async def _get_news_sentiment(self, ticker: str, hours_back: int) -> List[SentimentDataPoint]:
        """Get sentiment from news articles (using existing data provider)."""
        sentiment_points = []
        
        try:
            from services.data_provider import data_provider
            
            # Get recent news
            news_articles = await data_provider.get_news(ticker, limit=20)
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for article in news_articles:
                # Parse article timestamp
                article_time = datetime.fromisoformat(
                    article.get('published_utc', '').replace('Z', '+00:00')
                ).replace(tzinfo=None)
                
                if article_time < cutoff_time:
                    continue
                
                # Analyze article title and description
                text = f"{article.get('title', '')} {article.get('description', '')}"
                sentiment = self._analyze_text_sentiment(text)
                
                if sentiment:
                    sentiment_points.append(SentimentDataPoint(
                        text=text[:200],
                        sentiment_score=sentiment['score'],
                        confidence=sentiment['confidence'],
                        source='news',
                        timestamp=article_time,
                        author_credibility=self._calculate_news_credibility(article),
                        engagement_score=1.0
                    ))
            
            logger.debug(f"Collected {len(sentiment_points)} sentiment points from news")
            
        except Exception as e:
            logger.error(f"Error collecting news sentiment: {e}")
        
        return sentiment_points
    
    def _analyze_text_sentiment(self, text: str) -> Optional[Dict[str, float]]:
        """Analyze sentiment of text using TextBlob and keyword analysis."""
        if not TEXTBLOB_AVAILABLE or not text.strip():
            return None
        
        try:
            # Clean text
            text = re.sub(r'http\S+', '', text)  # Remove URLs
            text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)  # Keep only alphanumeric
            
            # TextBlob sentiment
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Keyword-based sentiment adjustment
            bullish_keywords = [
                'buy', 'bull', 'bullish', 'long', 'calls', 'moon', 'rocket',
                'breakout', 'rally', 'surge', 'pump', 'gap up', 'squeeze'
            ]
            
            bearish_keywords = [
                'sell', 'bear', 'bearish', 'short', 'puts', 'crash', 'dump',
                'breakdown', 'decline', 'drop', 'gap down', 'correction'
            ]
            
            text_lower = text.lower()
            bullish_count = sum(1 for word in bullish_keywords if word in text_lower)
            bearish_count = sum(1 for word in bearish_keywords if word in text_lower)
            
            # Combine TextBlob and keyword analysis
            keyword_sentiment = (bullish_count - bearish_count) * 0.1
            combined_score = (polarity + keyword_sentiment) / 2
            
            # Confidence based on subjectivity and keyword presence
            confidence = min(subjectivity + (bullish_count + bearish_count) * 0.1, 1.0)
            
            return {
                'score': max(-1, min(1, combined_score)),
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text sentiment: {e}")
            return None
    
    def _calculate_composite_sentiment(self, sentiment_points: List[SentimentDataPoint]) -> Dict[str, float]:
        """Calculate time-decayed, credibility-weighted composite sentiment."""
        if not sentiment_points:
            return {'score': 0.0, 'confidence': 0.0, 'direction': 'neutral'}
        
        total_weighted_score = 0.0
        total_weight = 0.0
        now = datetime.now()
        
        for point in sentiment_points:
            # Time decay factor (exponential decay)
            hours_old = (now - point.timestamp).total_seconds() / 3600
            time_decay = max(0.1, 1.0 - (hours_old / self.time_decay_hours))
            
            # Source credibility weight
            source_weight = self.source_weights.get(point.source, 0.5)
            
            # Combined weight
            weight = (
                point.confidence * 
                point.author_credibility * 
                point.engagement_score * 
                time_decay * 
                source_weight
            )
            
            total_weighted_score += point.sentiment_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return {'score': 0.0, 'confidence': 0.0, 'direction': 'neutral'}
        
        composite_score = total_weighted_score / total_weight
        composite_confidence = min(total_weight / len(sentiment_points), 1.0)
        
        # Determine direction
        if composite_score > 0.1:
            direction = 'bullish'
        elif composite_score < -0.1:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        return {
            'score': composite_score,
            'confidence': composite_confidence,
            'direction': direction
        }
    
    def _analyze_sentiment_trend(self, sentiment_points: List[SentimentDataPoint], hours_back: int) -> Dict[str, Any]:
        """Analyze sentiment trend over time."""
        if len(sentiment_points) < 2:
            return {'trend': 'insufficient_data', 'momentum': 0.0}
        
        # Sort by timestamp
        sorted_points = sorted(sentiment_points, key=lambda x: x.timestamp)
        
        # Calculate moving average sentiment
        window_hours = max(1, hours_back // 4)
        now = datetime.now()
        
        recent_scores = []
        older_scores = []
        
        for point in sorted_points:
            hours_old = (now - point.timestamp).total_seconds() / 3600
            if hours_old <= window_hours:
                recent_scores.append(point.sentiment_score)
            elif hours_old <= hours_back / 2:
                older_scores.append(point.sentiment_score)
        
        if not recent_scores or not older_scores:
            return {'trend': 'insufficient_data', 'momentum': 0.0}
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)
        
        momentum = recent_avg - older_avg
        
        if momentum > 0.1:
            trend = 'improving'
        elif momentum < -0.1:
            trend = 'deteriorating'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'momentum': momentum,
            'recent_avg': recent_avg,
            'older_avg': older_avg,
            'data_points_recent': len(recent_scores),
            'data_points_older': len(older_scores)
        }
    
    def _calculate_reddit_credibility(self, submission, subreddit_name: str) -> float:
        """Calculate credibility score for Reddit post."""
        base_credibility = {
            'SecurityAnalysis': 1.0,
            'ValueInvesting': 1.0,
            'investing': 0.8,
            'stocks': 0.7,
            'wallstreetbets': 0.5
        }.get(subreddit_name, 0.5)
        
        # Adjust based on engagement
        score_factor = min(submission.score / 100, 2.0)
        return min(base_credibility * (1 + score_factor), 3.0)
    
    def _determine_twitter_source_type(self, tweet) -> str:
        """Determine Twitter source type based on metrics."""
        metrics = tweet.public_metrics
        total_engagement = metrics['like_count'] + metrics['retweet_count']
        
        if total_engagement > 100:
            return 'twitter_influencer'
        elif total_engagement > 20:
            return 'twitter_verified'
        else:
            return 'twitter_general'
    
    def _calculate_twitter_credibility(self, tweet) -> float:
        """Calculate credibility score for Twitter post."""
        metrics = tweet.public_metrics
        total_engagement = metrics['like_count'] + metrics['retweet_count']
        
        # Base credibility on engagement
        engagement_factor = min(total_engagement / 50, 2.0)
        return min(1.0 + engagement_factor, 3.0)
    
    def _calculate_news_credibility(self, article: Dict) -> float:
        """Calculate credibility score for news article."""
        # Trusted news sources get higher credibility
        trusted_sources = [
            'reuters', 'bloomberg', 'wsj', 'marketwatch', 
            'cnbc', 'yahoo', 'benzinga', 'seeking alpha'
        ]
        
        publisher = article.get('publisher', {}).get('name', '').lower()
        
        for source in trusted_sources:
            if source in publisher:
                return 2.0
        
        return 1.0  # Default credibility


# Global instance
enhanced_sentiment = EnhancedSentimentAnalyzer()
