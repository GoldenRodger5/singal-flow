"""
MongoDB Database Manager for Signal Flow Trading System
Handles all database operations with atomic transactions for trade safety
"""
import os
import json
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
        self.mongo_url = os.getenv('MONGODB_URL', 'mongodb+srv://username:password@cluster.mongodb.net/')
        self.db_name = os.getenv('MONGODB_NAME', 'signal_flow_trading')
        self.connection_timeout = int(os.getenv('MONGODB_CONNECTION_TIMEOUT', 10000))
        self.server_timeout = int(os.getenv('MONGODB_SERVER_TIMEOUT', 10000))
        
        # Configure MongoDB Atlas connection with proper settings
        if 'mongodb+srv' in self.mongo_url:
            # MongoDB Atlas connection with enhanced settings
            self.client = MongoClient(
                self.mongo_url, 
                server_api=ServerApi('1'),
                connectTimeoutMS=self.connection_timeout,
                serverSelectionTimeoutMS=self.server_timeout,
                maxPoolSize=50,
                retryWrites=True
            )
            self.async_client = AsyncIOMotorClient(
                self.mongo_url, 
                server_api=ServerApi('1'),
                connectTimeoutMS=self.connection_timeout,
                serverSelectionTimeoutMS=self.server_timeout,
                maxPoolSize=50,
                retryWrites=True
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
        
        # Test connection with retry logic for Atlas
        self._test_connection()
        self._setup_collections()
        logger.info(f"Database configured: {self.db_name}")
    
    def _test_connection(self):
        """Test MongoDB connection with retry logic for Atlas"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.client.admin.command('ping')
                logger.info(f"MongoDB Atlas connected successfully: {self.db_name}")
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"MongoDB Atlas connection failed after {max_retries} attempts: {e}")
                    raise
                else:
                    logger.warning(f"MongoDB Atlas connection attempt {attempt + 1} failed, retrying...")
                    import time
                    time.sleep(2)  # Wait 2 seconds before retry
    
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


# Global database instance - lazy initialization
_db_manager = None

def get_db_manager():
    """Get database manager instance with lazy initialization."""
    global _db_manager
    if _db_manager is None:
        try:
            _db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            # Return a mock database manager for development/testing
            _db_manager = MockDatabaseManager()
    return _db_manager

class MockDatabaseManager:
    """Mock database manager for when MongoDB is unavailable."""
    
    def log_trade(self, *args, **kwargs):
        logger.info("Mock DB: Trade logged")
        return {"status": "mock"}
    
    def get_trades(self, *args, **kwargs):
        return []
    
    def log_ai_decision(self, *args, **kwargs):
        logger.info("Mock DB: AI decision logged")
        return {"status": "mock"}
    
    def get_recent_decisions(self, *args, **kwargs):
        return []
    
    def __getattr__(self, name):
        """Handle any other method calls."""
        def mock_method(*args, **kwargs):
            logger.info(f"Mock DB: {name} called")
            return {"status": "mock"}
        return mock_method

# Backward compatibility
db_manager = get_db_manager()
