#!/usr/bin/env python3
"""
Full MongoDB Migration Script
Migrates all JSON file operations to MongoDB collections for consistency and scalability.
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger


class MongoDBMigrator:
    """Migrates existing JSON data to MongoDB and updates data persistence patterns."""
    
    def __init__(self):
        # Import here to avoid connection issues on module load
        from services.database_manager import DatabaseManager
        self.db_manager = DatabaseManager()
        self.data_dir = Path("data")
        self.migration_log = []
        
    async def migrate_ai_decisions(self) -> bool:
        """Migrate AI decisions from JSON files to MongoDB."""
        try:
            logger.info("🔄 Migrating AI decisions to MongoDB...")
            
            # Check for existing JSON files
            decisions_file = self.data_dir / "ai_decisions.json"
            outcomes_file = self.data_dir / "decision_outcomes.json"
            
            migrated_count = 0
            
            # Migrate decisions
            if decisions_file.exists():
                with open(decisions_file, 'r') as f:
                    decisions = json.load(f)
                
                for decision in decisions:
                    # Convert datetime strings back to datetime objects if needed
                    if isinstance(decision.get('timestamp'), str):
                        decision['timestamp'] = datetime.fromisoformat(decision['timestamp'].replace('Z', '+00:00'))
                    
                    # Add migration metadata
                    decision['_migrated_from'] = 'json_file'
                    decision['_migration_date'] = datetime.now()
                    
                    success = await self.db_manager.save_ai_decision(decision)
                    if success:
                        migrated_count += 1
                
                logger.info(f"✅ Migrated {migrated_count} AI decisions")
                
                # Backup and remove old file
                backup_path = decisions_file.with_suffix('.json.backup')
                decisions_file.rename(backup_path)
                logger.info(f"📦 Backed up original file to {backup_path}")
            
            # Migrate outcomes (similar process)
            if outcomes_file.exists():
                with open(outcomes_file, 'r') as f:
                    outcomes = json.load(f)
                
                # Store outcomes as part of ai_decisions with outcome data
                for outcome in outcomes:
                    # Find matching decision and update it
                    decision_id = outcome.get('decision_id')
                    if decision_id:
                        # Update the decision with outcome data
                        await self.db_manager.async_db.ai_decisions.update_one(
                            {'decision_id': decision_id},
                            {'$set': {
                                'actual_outcome': outcome.get('actual_outcome'),
                                'outcome_timestamp': datetime.now(),
                                'accuracy_metrics': outcome.get('accuracy_metrics'),
                                'lessons_learned': outcome.get('lessons_learned')
                            }}
                        )
                
                backup_path = outcomes_file.with_suffix('.json.backup')
                outcomes_file.rename(backup_path)
                logger.info(f"📦 Backed up outcomes file to {backup_path}")
            
            self.migration_log.append(f"AI Decisions: {migrated_count} records migrated")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI decisions migration failed: {e}")
            return False
    
    async def migrate_agent_logs(self) -> bool:
        """Migrate agent JSON logs to MongoDB agent_logs collection."""
        try:
            logger.info("🔄 Migrating agent logs to MongoDB...")
            
            migrated_count = 0
            
            # Migrate active trades
            active_trades_file = self.data_dir / "active_trades.json"
            if active_trades_file.exists():
                with open(active_trades_file, 'r') as f:
                    active_trades = json.load(f)
                
                for trade_id, trade_data in active_trades.items():
                    log_entry = {
                        'agent_name': 'execution_monitor',
                        'action': 'trade_tracking',
                        'timestamp': datetime.now(),
                        'data': {
                            'trade_id': trade_id,
                            'trade_data': trade_data,
                            'status': 'active'
                        },
                        '_migrated_from': 'active_trades.json'
                    }
                    
                    success = await self.db_manager.log_agent_action(
                        'execution_monitor', 'trade_tracking', log_entry['data']
                    )
                    if success:
                        migrated_count += 1
                
                # Backup original
                backup_path = active_trades_file.with_suffix('.json.backup')
                active_trades_file.rename(backup_path)
            
            # Migrate trade log
            trade_log_file = self.data_dir / "trade_log.json"
            if trade_log_file.exists():
                with open(trade_log_file, 'r') as f:
                    trade_log = json.load(f)
                
                for log_entry in trade_log:
                    agent_log = {
                        'agent_name': 'execution_monitor',
                        'action': 'trade_execution',
                        'timestamp': datetime.fromisoformat(log_entry.get('timestamp', datetime.now().isoformat())),
                        'data': log_entry,
                        '_migrated_from': 'trade_log.json'
                    }
                    
                    success = await self.db_manager.log_agent_action(
                        'execution_monitor', 'trade_execution', agent_log['data']
                    )
                    if success:
                        migrated_count += 1
                
                backup_path = trade_log_file.with_suffix('.json.backup')
                trade_log_file.rename(backup_path)
            
            logger.info(f"✅ Migrated {migrated_count} agent log entries")
            self.migration_log.append(f"Agent Logs: {migrated_count} records migrated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Agent logs migration failed: {e}")
            return False
    
    async def migrate_summary_data(self) -> bool:
        """Migrate summary JSON files to appropriate MongoDB collections."""
        try:
            logger.info("🔄 Migrating summary data to MongoDB...")
            
            migrated_count = 0
            
            # Migrate daily summaries - could go to a new collection or system_health
            daily_summaries_file = self.data_dir / "daily_summaries.json"
            if daily_summaries_file.exists():
                with open(daily_summaries_file, 'r') as f:
                    summaries = json.load(f)
                
                for date_str, summary in summaries.items():
                    # Store as system health metric
                    await self.db_manager.log_system_health(
                        'daily_summary',
                        'info',
                        {
                            'date': date_str,
                            'summary': summary,
                            '_migrated_from': 'daily_summaries.json'
                        }
                    )
                    migrated_count += 1
                
                backup_path = daily_summaries_file.with_suffix('.json.backup')
                daily_summaries_file.rename(backup_path)
            
            # Migrate strategy stats
            strategy_stats_file = self.data_dir / "strategy_stats.json"
            if strategy_stats_file.exists():
                with open(strategy_stats_file, 'r') as f:
                    stats = json.load(f)
                
                for strategy_name, strategy_data in stats.items():
                    # Use strategy_outcomes collection
                    await self.db_manager.save_strategy_outcome(
                        strategy_name,
                        'performance_summary',
                        strategy_data,
                        {
                            '_migrated_from': 'strategy_stats.json',
                            'migration_date': datetime.now()
                        }
                    )
                    migrated_count += 1
                
                backup_path = strategy_stats_file.with_suffix('.json.backup')
                strategy_stats_file.rename(backup_path)
            
            logger.info(f"✅ Migrated {migrated_count} summary records")
            self.migration_log.append(f"Summary Data: {migrated_count} records migrated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Summary data migration failed: {e}")
            return False
    
    async def update_enhanced_decision_logger(self) -> bool:
        """Update enhanced_decision_logger.py to use MongoDB instead of JSON files."""
        try:
            logger.info("🔄 Updating enhanced_decision_logger to use MongoDB...")
            
            # Read current file
            logger_file = Path("services/enhanced_decision_logger.py")
            
            # Create MongoDB version
            mongodb_logger_content = '''"""
Enhanced Decision Logger - MongoDB Version
Captures detailed AI reasoning for learning using MongoDB persistence.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger

from services.config import Config
from services.database_manager import DatabaseManager


@dataclass
class DecisionContext:
    """Context information for a trading decision."""
    ticker: str
    market_data: Dict[str, Any]
    technical_indicators: Dict[str, Any]
    sentiment_data: Dict[str, Any]
    market_conditions: Dict[str, Any]
    time_context: Dict[str, Any]
    portfolio_context: Dict[str, Any]


@dataclass
class AIReasoning:
    """Detailed AI reasoning process."""
    decision_id: str
    timestamp: datetime
    context: DecisionContext
    reasoning_steps: List[Dict[str, Any]]
    confidence_breakdown: Dict[str, float]
    risk_assessment: Dict[str, Any]
    final_decision: str  # 'buy', 'sell', 'hold', 'exit'
    confidence_score: float
    expected_outcome: Dict[str, Any]
    alternatives_considered: List[Dict[str, Any]]
    key_factors: List[str]
    risk_factors: List[str]


@dataclass
class DecisionOutcome:
    """Actual outcome vs AI expectations."""
    decision_id: str
    actual_outcome: Dict[str, Any]
    expectation_vs_reality: Dict[str, Any]
    accuracy_metrics: Dict[str, float]
    lessons_learned: List[str]


class EnhancedDecisionLogger:
    """Enhanced decision logger with MongoDB persistence for AI learning."""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.current_reasoning = None
        
        logger.info("Enhanced Decision Logger initialized with MongoDB persistence")
    
    async def start_reasoning_session(self, context: DecisionContext) -> str:
        """Start a new reasoning session."""
        decision_id = f"decision_{int(datetime.now().timestamp() * 1000)}"
        
        self.current_reasoning = AIReasoning(
            decision_id=decision_id,
            timestamp=datetime.now(),
            context=context,
            reasoning_steps=[],
            confidence_breakdown={},
            risk_assessment={},
            final_decision="",
            confidence_score=0.0,
            expected_outcome={},
            alternatives_considered=[],
            key_factors=[],
            risk_factors=[]
        )
        
        logger.info(f"Started reasoning session: {decision_id}")
        return decision_id
    
    async def log_reasoning_step(self, step_name: str, analysis: Dict[str, Any], 
                               confidence: float, reasoning: str) -> None:
        """Log a step in the reasoning process."""
        if not self.current_reasoning:
            logger.warning("No active reasoning session")
            return
        
        step = {
            'step_name': step_name,
            'timestamp': datetime.now(),
            'analysis': analysis,
            'confidence': confidence,
            'reasoning': reasoning,
            'step_order': len(self.current_reasoning.reasoning_steps)
        }
        
        self.current_reasoning.reasoning_steps.append(step)
        self.current_reasoning.confidence_breakdown[step_name] = confidence
        
        logger.debug(f"Logged reasoning step: {step_name} (confidence: {confidence:.2f})")
    
    async def add_risk_factor(self, factor: str, severity: str, impact: float) -> None:
        """Add a risk factor to current reasoning."""
        if not self.current_reasoning:
            return
        
        risk_item = {
            'factor': factor,
            'severity': severity,
            'impact': impact,
            'timestamp': datetime.now()
        }
        
        self.current_reasoning.risk_assessment[factor] = risk_item
        self.current_reasoning.risk_factors.append(factor)
    
    async def add_key_factor(self, factor: str, weight: float) -> None:
        """Add a key decision factor."""
        if not self.current_reasoning:
            return
        
        self.current_reasoning.key_factors.append({
            'factor': factor,
            'weight': weight,
            'timestamp': datetime.now()
        })
    
    async def consider_alternative(self, alternative: str, pros: List[str], 
                                 cons: List[str], confidence: float) -> None:
        """Log an alternative that was considered."""
        if not self.current_reasoning:
            return
        
        alt = {
            'alternative': alternative,
            'pros': pros,
            'cons': cons,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
        
        self.current_reasoning.alternatives_considered.append(alt)
    
    async def finalize_decision(self, decision: str, confidence: float, 
                              expected_outcome: Dict[str, Any]) -> bool:
        """Finalize the reasoning and save to MongoDB."""
        if not self.current_reasoning:
            logger.error("No active reasoning session to finalize")
            return False
        
        self.current_reasoning.final_decision = decision
        self.current_reasoning.confidence_score = confidence
        self.current_reasoning.expected_outcome = expected_outcome
        
        # Convert to dict for MongoDB storage
        decision_data = asdict(self.current_reasoning)
        
        # Ensure datetime objects are properly handled
        decision_data['timestamp'] = self.current_reasoning.timestamp
        
        # Save to MongoDB
        success = await self.db_manager.save_ai_decision(decision_data)
        
        if success:
            logger.info(f"✅ Decision reasoning saved to MongoDB: {self.current_reasoning.decision_id}")
            self.current_reasoning = None
            return True
        else:
            logger.error(f"❌ Failed to save decision reasoning to MongoDB")
            return False
    
    async def log_decision_outcome(self, decision_id: str, actual_outcome: Dict[str, Any], 
                                 outcome_timestamp: Optional[datetime] = None) -> bool:
        """Log the actual outcome of a decision for learning."""
        if not outcome_timestamp:
            outcome_timestamp = datetime.now()
        
        try:
            # Update the existing decision with outcome data
            result = await self.db_manager.async_db.ai_decisions.update_one(
                {'decision_id': decision_id},
                {
                    '$set': {
                        'actual_outcome': actual_outcome,
                        'outcome_timestamp': outcome_timestamp,
                        'outcome_logged': True
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Decision outcome logged for {decision_id}")
                return True
            else:
                logger.warning(f"⚠️ No decision found with ID {decision_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to log decision outcome: {e}")
            return False
    
    async def get_learning_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze decision patterns for AI learning using MongoDB aggregation."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # MongoDB aggregation pipeline for pattern analysis
            pipeline = [
                {'$match': {'timestamp': {'$gte': cutoff_date}}},
                {'$group': {
                    '_id': '$final_decision',
                    'count': {'$sum': 1},
                    'avg_confidence': {'$avg': '$confidence_score'},
                    'outcomes': {'$push': '$actual_outcome'}
                }},
                {'$sort': {'count': -1}}
            ]
            
            cursor = self.db_manager.async_db.ai_decisions.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            patterns = {
                'decision_distribution': results,
                'total_decisions': sum(r['count'] for r in results),
                'analysis_period_days': days,
                'generated_at': datetime.now()
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze learning patterns: {e}")
            return {}
    
    async def get_accuracy_metrics(self, days: int = 30) -> Dict[str, float]:
        """Calculate decision accuracy metrics from MongoDB data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get decisions with outcomes
            cursor = self.db_manager.async_db.ai_decisions.find({
                'timestamp': {'$gte': cutoff_date},
                'outcome_logged': True,
                'actual_outcome': {'$exists': True}
            })
            
            decisions_with_outcomes = await cursor.to_list(length=None)
            
            if not decisions_with_outcomes:
                return {'accuracy': 0.0, 'sample_size': 0}
            
            # Calculate accuracy metrics
            correct_predictions = 0
            total_predictions = len(decisions_with_outcomes)
            
            for decision in decisions_with_outcomes:
                expected = decision.get('expected_outcome', {})
                actual = decision.get('actual_outcome', {})
                
                # Simple accuracy calculation - can be enhanced
                if expected.get('direction') == actual.get('direction'):
                    correct_predictions += 1
            
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
            
            return {
                'accuracy': accuracy,
                'correct_predictions': correct_predictions,
                'total_predictions': total_predictions,
                'sample_size': total_predictions
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate accuracy metrics: {e}")
            return {'accuracy': 0.0, 'sample_size': 0}
'''
            
            # Backup original file
            backup_path = logger_file.with_suffix('.py.backup')
            if logger_file.exists():
                logger_file.rename(backup_path)
                logger.info(f"📦 Backed up original logger to {backup_path}")
            
            # Write new MongoDB version
            with open(logger_file, 'w') as f:
                f.write(mongodb_logger_content)
            
            logger.info("✅ Enhanced decision logger updated to use MongoDB")
            self.migration_log.append("Enhanced Decision Logger: Updated to MongoDB")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update enhanced decision logger: {e}")
            return False
    
    async def verify_mongodb_connections(self) -> bool:
        """Verify all MongoDB collections are accessible and properly indexed."""
        try:
            logger.info("🔍 Verifying MongoDB connections and indexes...")
            
            # Test database connection
            await self.db_manager.ensure_connection()
            
            # Verify all collections exist and have proper indexes
            collections_to_verify = [
                'trades', 'ai_decisions', 'ai_learning_data', 'market_data',
                'market_sentiment', 'news_sentiment', 'price_patterns',
                'strategy_outcomes', 'market_regime', 'correlation_data',
                'volatility_data', 'system_health', 'agent_logs', 'ai_signals',
                'ai_signal_analysis'
            ]
            
            verified_collections = []
            
            for collection_name in collections_to_verify:
                try:
                    collection = getattr(self.db_manager.async_db, collection_name)
                    
                    # Test write operation
                    test_doc = {
                        '_test': True,
                        'timestamp': datetime.now(),
                        'verification_run': True
                    }
                    result = await collection.insert_one(test_doc)
                    
                    # Clean up test document
                    await collection.delete_one({'_id': result.inserted_id})
                    
                    verified_collections.append(collection_name)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Collection {collection_name} verification failed: {e}")
            
            logger.info(f"✅ Verified {len(verified_collections)}/{len(collections_to_verify)} collections")
            
            # Ensure indexes are created
            await self.db_manager.ensure_indexes()
            logger.info("✅ MongoDB indexes verified")
            
            return len(verified_collections) >= len(collections_to_verify) * 0.8  # 80% success rate
            
        except Exception as e:
            logger.error(f"❌ MongoDB verification failed: {e}")
            return False
    
    async def run_full_migration(self) -> Dict[str, bool]:
        """Run complete migration to MongoDB."""
        logger.info("🚀 Starting full MongoDB migration...")
        logger.info("=" * 60)
        
        results = {}
        
        # Step 1: Verify MongoDB connectivity
        results['mongodb_verification'] = await self.verify_mongodb_connections()
        if not results['mongodb_verification']:
            logger.error("❌ MongoDB verification failed - aborting migration")
            return results
        
        # Step 2: Migrate existing data
        results['ai_decisions_migration'] = await self.migrate_ai_decisions()
        results['agent_logs_migration'] = await self.migrate_agent_logs()
        results['summary_data_migration'] = await self.migrate_summary_data()
        
        # Step 3: Update code to use MongoDB
        results['decision_logger_update'] = await self.update_enhanced_decision_logger()
        
        # Step 4: Final verification
        results['final_verification'] = await self.verify_mongodb_connections()
        
        # Calculate success rate
        successful_migrations = sum(results.values())
        total_migrations = len(results)
        success_rate = successful_migrations / total_migrations * 100
        
        # Print results
        logger.info("\n📊 MONGODB MIGRATION RESULTS")
        logger.info("=" * 60)
        
        for migration_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            formatted_name = migration_name.replace('_', ' ').title()
            logger.info(f"{formatted_name}: {status}")
        
        # Print migration log
        logger.info("\n📋 Migration Summary:")
        for log_entry in self.migration_log:
            logger.info(f"  • {log_entry}")
        
        logger.info(f"\n🎯 Overall Success Rate: {success_rate:.0f}% ({successful_migrations}/{total_migrations})")
        
        if success_rate >= 80:
            logger.info("🎉 MIGRATION SUCCESSFUL! Your system now uses MongoDB consistently.")
            logger.info("🔧 Next steps:")
            logger.info("  1. Update agents to use db_manager instead of JSON files")
            logger.info("  2. Test all trading operations")
            logger.info("  3. Monitor MongoDB performance")
        else:
            logger.error("⚠️ MIGRATION INCOMPLETE - Review failed steps above")
        
        return results


async def main():
    """Main migration function."""
    try:
        migrator = MongoDBMigrator()
        results = await migrator.run_full_migration()
        
        # Return appropriate exit code
        successful_migrations = sum(results.values())
        total_migrations = len(results)
        
        if successful_migrations >= total_migrations * 0.8:
            print("\n✅ MongoDB migration completed successfully!")
            return 0
        else:
            print(f"\n⚠️ MongoDB migration completed with issues ({successful_migrations}/{total_migrations} successful)")
            return 1
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
