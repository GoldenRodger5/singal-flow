"""
MongoDB Database Manager for Signal Flow Trading System
Handles all database operations with atomic transactions for trade safety
"""
import os
import json
import ssl
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from dataclasses import dataclass, asdict
import asyncio


@dataclass
class TradeRecord:
    """Trade record structure for database storage"""
    symbol: str
    action: str  # BUY, SELL
    quantity: float
    price: float
    timestamp: datetime
    source: str  # telegram, ai_agent, manual
    confidence: float
    execution_id: str
    status: str  # pending, executed, failed, cancelled
    profit_loss: Optional[float] = None
    fees: Optional[float] = None
    
    def to_dict(self):
        return asdict(self)


class DatabaseManager:
    """Production-ready MongoDB manager for trading data"""
    
    def __init__(self):
        try:
            # Load environment variables from .env file if running locally
            if os.path.exists('.env'):
                from dotenv import load_dotenv
                load_dotenv()
                
            # Get MongoDB URL and validate format
            self.mongo_url = os.getenv('MONGODB_URL', 'mongodb+srv://username:password@cluster.mongodb.net/')
            
            # Validate MongoDB URL format
            if not self.mongo_url or self.mongo_url == 'mongodb+srv://username:password@cluster.mongodb.net/':
                raise ValueError("MONGODB_URL environment variable not properly configured")
                
            # Remove any extra spaces or invalid characters
            self.mongo_url = self.mongo_url.strip()
            
            self.db_name = os.getenv('MONGODB_NAME', 'signal_flow_trading')
            self.connection_timeout = int(os.getenv('MONGODB_CONNECTION_TIMEOUT', 30000))  # Increased timeout for Railway
            self.server_timeout = int(os.getenv('MONGODB_SERVER_TIMEOUT', 30000))  # Increased timeout for Railway
            
            logger.info(f"Initializing MongoDB connection to: {self.mongo_url[:30]}...")
            
            # Configure MongoDB Atlas connection with Railway-friendly settings
            if 'mongodb+srv' in self.mongo_url:
                # MongoDB Atlas connection - Railway optimized
                self.client = MongoClient(
                    self.mongo_url, 
                    server_api=ServerApi('1'),
                    connectTimeoutMS=self.connection_timeout,
                    serverSelectionTimeoutMS=self.server_timeout,
                    socketTimeoutMS=60000,  # 60 second socket timeout
                    maxPoolSize=10,  # Limit connection pool for Railway
                    retryWrites=True,
                    w='majority'
                )
                self.async_client = AsyncIOMotorClient(
                    self.mongo_url, 
                    server_api=ServerApi('1'),
                    connectTimeoutMS=self.connection_timeout,
                    serverSelectionTimeoutMS=self.server_timeout,
                    socketTimeoutMS=60000,
                    maxPoolSize=10,
                    retryWrites=True,
                    w='majority'
                )
            else:
                # Local MongoDB connection
                self.client = MongoClient(
                    self.mongo_url,
                    connectTimeoutMS=self.connection_timeout,
                    serverSelectionTimeoutMS=self.server_timeout
                )
                self.async_client = AsyncIOMotorClient(
                    self.mongo_url,
                    connectTimeoutMS=self.connection_timeout,
                    serverSelectionTimeoutMS=self.server_timeout
                )
            
            self.db = self.client[self.db_name]
            self.async_db = self.async_client[self.db_name]
            
            # Setup collection references for new services
            self.ai_signals = self.async_db.ai_signals
            self.market_pulse = self.async_db.market_pulse
            self.system_config = self.async_db.system_config
            
            # Test connection with retry logic for Railway/Atlas
            self._test_connection()
            self._setup_collections()
            logger.info(f"Database configured: {self.db_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseManager: {e}")
            raise
    
    def _test_connection(self):
        """Test MongoDB connection with retry logic for Railway/Atlas"""
        max_retries = 5  # Increased retries for Railway
        for attempt in range(max_retries):
            try:
                # Test connection with timeout
                self.client.admin.command('ping', maxTimeMS=10000)
                logger.info(f"MongoDB Atlas connected successfully: {self.db_name}")
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"MongoDB Atlas connection failed after {max_retries} attempts: {e}")
                    # Don't raise in Railway - allow service to start and retry later
                    if os.getenv('RAILWAY_ENVIRONMENT'):
                        logger.warning("Running in Railway - allowing startup despite connection failure")
                        return
                    raise
                else:
                    logger.warning(f"MongoDB Atlas connection attempt {attempt + 1} failed, retrying in {2 * (attempt + 1)} seconds...")
                    import time
                    time.sleep(2 * (attempt + 1))  # Progressive backoff
    
    def _setup_collections(self):
        """Setup collections and indexes for optimal performance"""
        collections = {
            'trades': [
                ('execution_id', 1),
                ('symbol', 1),
                ('timestamp', -1),
                ('status', 1),
                ('source', 1)
            ],
            'ai_decisions': [
                ('timestamp', -1),
                ('symbol', 1),
                ('confidence', -1),
                ('decision_type', 1)
            ],
            'market_data': [
                ('symbol', 1),
                ('timestamp', -1),
                ('data_type', 1)
            ],
            'system_health': [
                ('timestamp', -1),
                ('component', 1)
            ],
            'trade_performance': [
                ('symbol', 1),
                ('date', -1),
                ('profit_loss', -1)
            ],
            'agent_logs': [
                ('agent_type', 1),
                ('timestamp', -1),
                ('action', 1)
            ],
            # AI Learning Collections
            'ai_learning_data': [
                ('timestamp', -1),
                ('feature_type', 1),
                ('symbol', 1)
            ],
            'market_sentiment': [
                ('timestamp', -1),
                ('symbol', 1),
                ('sentiment_score', -1)
            ],
            'price_patterns': [
                ('symbol', 1),
                ('pattern_type', 1),
                ('timestamp', -1),
                ('success_rate', -1)
            ],
            'strategy_outcomes': [
                ('strategy_name', 1),
                ('timestamp', -1),
                ('outcome', 1),
                ('profit_loss', -1)
            ],
            'market_regime': [
                ('timestamp', -1),
                ('regime_type', 1),
                ('confidence', -1)
            ],
            'correlation_data': [
                ('timestamp', -1),
                ('symbol_pair', 1),
                ('correlation_value', -1)
            ],
            # New collections for enhanced services
            'ai_signals': [
                ('symbol', 1),
                ('timestamp', -1),
                ('signal_type', 1),
                ('confidence', -1)
            ],
            'market_pulse': [
                ('timestamp', -1),
                ('market_trend', 1),
                ('volatility_index', -1)
            ],
            'system_config': [
                ('_id', 1),
                ('updated_at', -1)
            ],
            'volatility_data': [
                ('symbol', 1),
                ('timestamp', -1),
                ('volatility_type', 1)
            ],
            'news_sentiment': [
                ('timestamp', -1),
                ('symbol', 1),
                ('sentiment_score', -1),
                ('news_source', 1)
            ],
            # AI Signal Tracking Collections
            'ai_signals': [
                ('signal_id', 1),
                ('symbol', 1),
                ('timestamp', -1),
                ('signal_type', 1),
                ('confidence', -1),
                ('execution_decision', 1)
            ],
            'ai_signal_analysis': [
                ('signal_id', 1),
                ('analysis_timestamp', -1),
                ('symbol', 1)
            ]
        }
        
        for collection_name, indexes in collections.items():
            collection = self.db[collection_name]
            for index in indexes:
                collection.create_index([index])
        
        logger.info("Database collections and indexes configured")
    
    async def save_trade(self, trade: TradeRecord) -> bool:
        """Save trade with atomic operation"""
        try:
            result = await self.async_db.trades.insert_one(trade.to_dict())
            logger.info(f"Trade saved: {trade.execution_id} - {trade.symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to save trade {trade.execution_id}: {e}")
            return False
    
    async def update_trade_status(self, execution_id: str, status: str, 
                                profit_loss: Optional[float] = None) -> bool:
        """Update trade status atomically"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now(timezone.utc)
            }
            if profit_loss is not None:
                update_data['profit_loss'] = profit_loss
            
            result = await self.async_db.trades.update_one(
                {'execution_id': execution_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update trade {execution_id}: {e}")
            return False
    
    async def get_active_trades(self) -> List[Dict]:
        """Get all active trades"""
        try:
            cursor = self.async_db.trades.find(
                {'status': {'$in': ['pending', 'executed']}},
                sort=[('timestamp', -1)]
            )
            return await cursor.to_list(length=1000)
        except Exception as e:
            logger.error(f"Failed to get active trades: {e}")
            return []
    
    async def save_ai_decision(self, decision_data: Dict) -> bool:
        """Save AI decision with metadata"""
        try:
            decision_data['timestamp'] = datetime.now(timezone.utc)
            result = await self.async_db.ai_decisions.insert_one(decision_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save AI decision: {e}")
            return False
    
    async def get_trade_performance(self, symbol: str = None, 
                                  days: int = 30) -> Dict:
        """Get trading performance analytics"""
        try:
            match_filter = {}
            if symbol:
                match_filter['symbol'] = symbol
            
            pipeline = [
                {'$match': match_filter},
                {'$group': {
                    '_id': '$symbol',
                    'total_trades': {'$sum': 1},
                    'total_profit': {'$sum': {'$ifNull': ['$profit_loss', 0]}},
                    'winning_trades': {
                        '$sum': {
                            '$cond': [{'$gt': ['$profit_loss', 0]}, 1, 0]
                        }
                    },
                    'avg_confidence': {'$avg': '$confidence'}
                }}
            ]
            
            cursor = self.async_db.trades.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            return results
        except Exception as e:
            logger.error(f"Failed to get performance data: {e}")
            return {}
    
    async def log_system_health(self, component: str, status: str, 
                              metrics: Dict = None) -> bool:
        """Log system health metrics"""
        try:
            health_data = {
                'component': component,
                'status': status,
                'timestamp': datetime.now(timezone.utc),
                'metrics': metrics or {}
            }
            await self.async_db.system_health.insert_one(health_data)
            return True
        except Exception as e:
            logger.error(f"Failed to log system health: {e}")
            return False
    
    async def get_recent_decisions(self, limit: int = 50) -> List[Dict]:
        """Get recent AI decisions for monitoring"""
        try:
            cursor = self.async_db.ai_decisions.find(
                {},
                sort=[('timestamp', -1)],
                limit=limit
            )
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Failed to get recent decisions: {e}")
            return []
    
    def close(self):
        """Close database connections"""
        self.client.close()
        self.async_client.close()
        logger.info("Database connections closed")

    # ==================== AI LEARNING DATA COLLECTION METHODS ====================
    
    async def save_market_data(self, symbol: str, data: Dict, data_type: str = 'price') -> bool:
        """Save market data for AI learning"""
        try:
            market_data = {
                'symbol': symbol,
                'data_type': data_type,
                'timestamp': datetime.now(timezone.utc),
                'data': data,
                'metadata': {
                    'volume': data.get('volume'),
                    'high': data.get('high'),
                    'low': data.get('low'),
                    'close': data.get('close'),
                    'open': data.get('open')
                }
            }
            await self.async_db.market_data.insert_one(market_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save market data: {e}")
            return False
    
    async def save_ai_learning_features(self, symbol: str, features: Dict, feature_type: str) -> bool:
        """Save AI learning features for model training"""
        try:
            learning_data = {
                'symbol': symbol,
                'feature_type': feature_type,
                'timestamp': datetime.now(timezone.utc),
                'features': features,
                'metadata': {
                    'feature_count': len(features),
                    'data_quality': features.get('data_quality', 'unknown')
                }
            }
            await self.async_db.ai_learning_data.insert_one(learning_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save AI learning features: {e}")
            return False
    
    async def save_market_sentiment(self, symbol: str, sentiment_score: float, 
                                  source: str, metadata: Dict = None) -> bool:
        """Save market sentiment data"""
        try:
            sentiment_data = {
                'symbol': symbol,
                'sentiment_score': sentiment_score,
                'source': source,
                'timestamp': datetime.now(timezone.utc),
                'metadata': metadata or {}
            }
            await self.async_db.market_sentiment.insert_one(sentiment_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save market sentiment: {e}")
            return False
    
    async def save_price_pattern(self, symbol: str, pattern_type: str, 
                               pattern_data: Dict, success_rate: float = None) -> bool:
        """Save identified price patterns"""
        try:
            pattern_record = {
                'symbol': symbol,
                'pattern_type': pattern_type,
                'timestamp': datetime.now(timezone.utc),
                'pattern_data': pattern_data,
                'success_rate': success_rate,
                'confidence': pattern_data.get('confidence', 0.0)
            }
            await self.async_db.price_patterns.insert_one(pattern_record)
            return True
        except Exception as e:
            logger.error(f"Failed to save price pattern: {e}")
            return False
    
    async def save_strategy_outcome(self, strategy_name: str, outcome: str, 
                                  profit_loss: float, metadata: Dict = None) -> bool:
        """Save strategy execution outcomes for learning"""
        try:
            outcome_data = {
                'strategy_name': strategy_name,
                'outcome': outcome,  # 'success', 'failure', 'partial'
                'profit_loss': profit_loss,
                'timestamp': datetime.now(timezone.utc),
                'metadata': metadata or {}
            }
            await self.async_db.strategy_outcomes.insert_one(outcome_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save strategy outcome: {e}")
            return False
    
    async def save_market_regime(self, regime_type: str, confidence: float, 
                               indicators: Dict) -> bool:
        """Save market regime classification"""
        try:
            regime_data = {
                'regime_type': regime_type,  # 'bull', 'bear', 'sideways', 'volatile'
                'confidence': confidence,
                'timestamp': datetime.now(timezone.utc),
                'indicators': indicators
            }
            await self.async_db.market_regime.insert_one(regime_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save market regime: {e}")
            return False
    
    async def save_correlation_data(self, symbol1: str, symbol2: str, 
                                  correlation_value: float, timeframe: str) -> bool:
        """Save correlation analysis between symbols"""
        try:
            correlation_data = {
                'symbol_pair': f"{symbol1}_{symbol2}",
                'symbol1': symbol1,
                'symbol2': symbol2,
                'correlation_value': correlation_value,
                'timeframe': timeframe,
                'timestamp': datetime.now(timezone.utc)
            }
            await self.async_db.correlation_data.insert_one(correlation_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save correlation data: {e}")
            return False
    
    async def save_volatility_data(self, symbol: str, volatility_value: float, 
                                 volatility_type: str, timeframe: str) -> bool:
        """Save volatility measurements"""
        try:
            volatility_data = {
                'symbol': symbol,
                'volatility_value': volatility_value,
                'volatility_type': volatility_type,  # 'historical', 'implied', 'realized'
                'timeframe': timeframe,
                'timestamp': datetime.now(timezone.utc)
            }
            await self.async_db.volatility_data.insert_one(volatility_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save volatility data: {e}")
            return False
    
    async def save_news_sentiment(self, symbol: str, sentiment_score: float, 
                                news_title: str, news_source: str, 
                                article_text: str = None) -> bool:
        """Save news sentiment analysis"""
        try:
            news_data = {
                'symbol': symbol,
                'sentiment_score': sentiment_score,
                'news_title': news_title,
                'news_source': news_source,
                'article_text': article_text,
                'timestamp': datetime.now(timezone.utc)
            }
            await self.async_db.news_sentiment.insert_one(news_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save news sentiment: {e}")
            return False
    
    # ==================== AI LEARNING DATA RETRIEVAL METHODS ====================
    
    async def get_training_data(self, symbol: str = None, feature_type: str = None, 
                              days: int = 30) -> List[Dict]:
        """Get training data for AI models"""
        try:
            match_filter = {}
            if symbol:
                match_filter['symbol'] = symbol
            if feature_type:
                match_filter['feature_type'] = feature_type
            
            # Add time filter
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            match_filter['timestamp'] = {'$gte': cutoff_time}
            
            cursor = self.async_db.ai_learning_data.find(
                match_filter,
                sort=[('timestamp', -1)],
                limit=10000
            )
            return await cursor.to_list(length=10000)
        except Exception as e:
            logger.error(f"Failed to get training data: {e}")
            return []
    
    async def get_market_sentiment_history(self, symbol: str, days: int = 7) -> List[Dict]:
        """Get historical market sentiment for a symbol"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            cursor = self.async_db.market_sentiment.find(
                {'symbol': symbol, 'timestamp': {'$gte': cutoff_time}},
                sort=[('timestamp', -1)]
            )
            return await cursor.to_list(length=1000)
        except Exception as e:
            logger.error(f"Failed to get sentiment history: {e}")
            return []
    
    async def get_pattern_success_rates(self, pattern_type: str = None) -> Dict:
        """Get success rates for price patterns"""
        try:
            match_filter = {}
            if pattern_type:
                match_filter['pattern_type'] = pattern_type
            
            pipeline = [
                {'$match': match_filter},
                {'$group': {
                    '_id': '$pattern_type',
                    'avg_success_rate': {'$avg': '$success_rate'},
                    'pattern_count': {'$sum': 1},
                    'avg_confidence': {'$avg': '$confidence'}
                }}
            ]
            
            cursor = self.async_db.price_patterns.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            return {result['_id']: result for result in results}
        except Exception as e:
            logger.error(f"Failed to get pattern success rates: {e}")
            return {}
    
    async def get_strategy_performance(self, strategy_name: str = None, days: int = 30) -> Dict:
        """Get strategy performance analytics"""
        try:
            match_filter = {}
            if strategy_name:
                match_filter['strategy_name'] = strategy_name
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            match_filter['timestamp'] = {'$gte': cutoff_time}
            
            pipeline = [
                {'$match': match_filter},
                {'$group': {
                    '_id': '$strategy_name',
                    'total_trades': {'$sum': 1},
                    'successful_trades': {
                        '$sum': {'$cond': [{'$eq': ['$outcome', 'success']}, 1, 0]}
                    },
                    'total_profit': {'$sum': '$profit_loss'},
                    'avg_profit': {'$avg': '$profit_loss'},
                    'win_rate': {
                        '$avg': {'$cond': [{'$gt': ['$profit_loss', 0]}, 1, 0]}
                    }
                }}
            ]
            
            cursor = self.async_db.strategy_outcomes.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            return {result['_id']: result for result in results}
        except Exception as e:
            logger.error(f"Failed to get strategy performance: {e}")
            return {}
    
    async def get_market_regime_history(self, days: int = 30) -> List[Dict]:
        """Get market regime classification history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            cursor = self.async_db.market_regime.find(
                {'timestamp': {'$gte': cutoff_time}},
                sort=[('timestamp', -1)]
            )
            return await cursor.to_list(length=1000)
        except Exception as e:
            logger.error(f"Failed to get market regime history: {e}")
            return []
    
    async def get_comprehensive_learning_summary(self) -> Dict:
        """Get comprehensive summary of all learning data"""
        try:
            summary = {}
            
            # Count records in each collection
            collections = [
                'ai_learning_data', 'market_sentiment', 'price_patterns',
                'strategy_outcomes', 'market_regime', 'correlation_data',
                'volatility_data', 'news_sentiment'
            ]
            
            for collection in collections:
                count = await self.async_db[collection].count_documents({})
                summary[f"{collection}_count"] = count
            
            # Get recent activity (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            for collection in collections:
                recent_count = await self.async_db[collection].count_documents({
                    'timestamp': {'$gte': cutoff_time}
                })
                summary[f"{collection}_recent"] = recent_count
            
            summary['last_updated'] = datetime.now(timezone.utc).isoformat()
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get learning summary: {e}")
            return {}

    async def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent trades for performance calculations"""
        try:
            cursor = self.async_db.trades.find(
                {},
                sort=[('timestamp', -1)],
                limit=limit
            )
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []

    async def get_learning_summary(self) -> Dict:
        """Get AI learning summary with basic metrics"""
        try:
            # Get trade count and performance
            trade_count = await self.async_db.trades.count_documents({})
            decision_count = await self.async_db.ai_decisions.count_documents({})
            
            # Calculate basic metrics
            pipeline = [
                {'$group': {
                    '_id': None,
                    'total_pnl': {'$sum': {'$ifNull': ['$profit_loss', 0]}},
                    'winning_trades': {
                        '$sum': {'$cond': [{'$gt': ['$profit_loss', 0]}, 1, 0]}
                    },
                    'avg_confidence': {'$avg': '$confidence'}
                }}
            ]
            
            trade_stats = await self.async_db.trades.aggregate(pipeline).to_list(length=1)
            stats = trade_stats[0] if trade_stats else {}
            
            return {
                'total_trades': trade_count,
                'total_decisions': decision_count,
                'total_pnl': stats.get('total_pnl', 0),
                'winning_trades': stats.get('winning_trades', 0),
                'win_rate': (stats.get('winning_trades', 0) / max(trade_count, 1)) * 100,
                'avg_confidence': stats.get('avg_confidence', 0),
                'models_trained': 0,  # Real ML model count from database - will implement when ML models added
                'total_predictions': decision_count,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get learning summary: {e}")
            return {
                'total_trades': 0,
                'total_decisions': 0,
                'total_pnl': 0,
                'winning_trades': 0,
                'win_rate': 0,
                'avg_confidence': 0,
                'models_trained': 0,
                'total_predictions': 0,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    # ==================== AI SIGNALS MANAGEMENT ====================
    
    async def store_ai_signals(self, signals_data: List[Dict[str, Any]]):
        """Store AI signals to database for tracking."""
        try:
            if not signals_data:
                return
            
            # Add metadata to each signal
            for signal in signals_data:
                signal['_id'] = f"{signal['symbol']}_{signal['timestamp'].strftime('%Y%m%d_%H%M%S')}"
                signal['created_at'] = datetime.now(timezone.utc)
            
            result = await self.ai_signals.insert_many(signals_data)
            logger.debug(f"Stored {len(result.inserted_ids)} AI signals")
            
        except Exception as e:
            logger.error(f"Error storing AI signals: {e}")
    
    async def get_recent_signals(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent AI signals from database."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            cursor = self.ai_signals.find({
                'timestamp': {'$gte': cutoff_date}
            }).sort('timestamp', -1)
            
            signals = await cursor.to_list(length=None)
            
            # Convert datetime objects to ISO format strings for JSON serialization
            for signal in signals:
                if 'timestamp' in signal and hasattr(signal['timestamp'], 'isoformat'):
                    signal['timestamp'] = signal['timestamp'].isoformat()
                if 'created_at' in signal and hasattr(signal['created_at'], 'isoformat'):
                    signal['created_at'] = signal['created_at'].isoformat()
                if 'last_updated' in signal and hasattr(signal['last_updated'], 'isoformat'):
                    signal['last_updated'] = signal['last_updated'].isoformat()
                    
            logger.debug(f"Retrieved {len(signals)} recent signals")
            return signals
            
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    async def update_signal_outcomes(self, updates: List[Dict[str, Any]]):
        """Update signal outcomes with actual returns."""
        try:
            for update in updates:
                signal_id = f"{update['symbol']}_{update['timestamp'].strftime('%Y%m%d_%H%M%S')}"
                
                await self.ai_signals.update_one(
                    {'_id': signal_id},
                    {'$set': {
                        'actual_return': update['actual_return'],
                        'current_price': update['current_price'],
                        'last_updated': datetime.now(timezone.utc)
                    }}
                )
            
            logger.debug(f"Updated {len(updates)} signal outcomes")
            
        except Exception as e:
            logger.error(f"Error updating signal outcomes: {e}")
    
    # ==================== MARKET PULSE DATA ====================
    
    async def store_market_pulse(self, pulse_data: Dict[str, Any]):
        """Store market pulse data for historical tracking."""
        try:
            pulse_data['_id'] = pulse_data['timestamp'].strftime('%Y%m%d_%H%M')
            pulse_data['created_at'] = datetime.now(timezone.utc)
            
            await self.market_pulse.replace_one(
                {'_id': pulse_data['_id']},
                pulse_data,
                upsert=True
            )
            
            logger.debug("Stored market pulse data")
            
        except Exception as e:
            logger.error(f"Error storing market pulse: {e}")
    
    async def get_historical_market_pulse(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical market pulse data."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            cursor = self.market_pulse.find({
                'timestamp': {'$gte': cutoff_date}
            }).sort('timestamp', -1)
            
            pulse_history = await cursor.to_list(length=None)
            logger.debug(f"Retrieved {len(pulse_history)} market pulse records")
            return pulse_history
            
        except Exception as e:
            logger.error(f"Error getting historical market pulse: {e}")
            return []
    
    # ==================== PERFORMANCE DATA ====================
    
    async def get_balance_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get account balance history for performance analysis."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get balance snapshots from trades and portfolio updates
            cursor = self.trades.aggregate([
                {'$match': {'timestamp': {'$gte': cutoff_date}}},
                {'$group': {
                    '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                    'total_value': {'$last': '$portfolio_value'},
                    'trades_count': {'$sum': 1},
                    'date': {'$last': '$timestamp'}
                }},
                {'$sort': {'date': 1}}
            ])
            
            balance_history = await cursor.to_list(length=None)
            
            # Fill in missing days with interpolated values
            if balance_history:
                filled_history = []
                current_date = cutoff_date.date()
                end_date = datetime.now(timezone.utc).date()
                
                i = 0
                last_value = 10000.0  # Starting balance
                
                while current_date <= end_date:
                    date_str = current_date.isoformat()
                    
                    # Check if we have data for this date
                    if i < len(balance_history) and balance_history[i]['_id'] == date_str:
                        last_value = balance_history[i]['total_value']
                        filled_history.append({
                            'date': date_str,
                            'total_value': last_value,
                            'trades_count': balance_history[i]['trades_count']
                        })
                        i += 1
                    else:
                        # Use last known value
                        filled_history.append({
                            'date': date_str,
                            'total_value': last_value,
                            'trades_count': 0
                        })
                    
                    current_date += timedelta(days=1)
                
                return filled_history
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting balance history: {e}")
            return []
    
    async def get_trading_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get trading history for performance analysis."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            cursor = self.trades.find({
                'timestamp': {'$gte': cutoff_date},
                'status': 'executed'
            }).sort('timestamp', -1)
            
            trades = await cursor.to_list(length=None)
            logger.debug(f"Retrieved {len(trades)} trades from history")
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trading history: {e}")
            return []
    
    async def get_symbol_trading_history(self, symbol: str) -> List[Dict[str, Any]]:
        """Get trading history for a specific symbol."""
        try:
            cursor = self.trades.find({
                'symbol': symbol,
                'status': 'executed'
            }).sort('timestamp', -1)
            
            trades = await cursor.to_list(length=None)
            logger.debug(f"Retrieved {len(trades)} trades for {symbol}")
            return trades
            
        except Exception as e:
            logger.error(f"Error getting symbol trading history: {e}")
            return []
    
    # ==================== SYSTEM CONFIGURATION ====================
    
    async def update_system_config(self, config_section: str, config_data: Dict[str, Any]):
        """Update system configuration in database."""
        try:
            config_doc = {
                '_id': config_section,
                'config': config_data,
                'updated_at': datetime.now(timezone.utc)
            }
            
            await self.system_config.replace_one(
                {'_id': config_section},
                config_doc,
                upsert=True
            )
            
            logger.debug(f"Updated system config section: {config_section}")
            
        except Exception as e:
            logger.error(f"Error updating system config: {e}")
    
    async def get_system_config(self, config_section: str) -> Dict[str, Any]:
        """Get system configuration from database."""
        try:
            config_doc = await self.system_config.find_one({'_id': config_section})
            
            if config_doc:
                return config_doc.get('config', {})
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting system config: {e}")
            return {}


# Global database instance - lazy initialization
_db_manager = None

def get_db_manager():
    """Get database manager instance with lazy initialization."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        logger.info("✅ Connected to MongoDB Atlas - PRODUCTION MODE")
    return _db_manager

# Lazy initialization - only create when first accessed
_db_manager = None

# For backward compatibility, create a lazy property that only initializes when accessed
class LazyDBManager:
    def __getattr__(self, name):
        db_mgr = get_db_manager()
        return getattr(db_mgr, name)
    
    def __call__(self, *args, **kwargs):
        db_mgr = get_db_manager()
        return db_mgr(*args, **kwargs)

# Backward compatibility - lazy initialization
db_manager = LazyDBManager()
