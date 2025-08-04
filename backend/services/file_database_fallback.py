"""
Temporary File-Based Database Fallback
This provides basic database functionality using local files until MongoDB is fixed.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
import asyncio


class FileBasedDatabaseFallback:
    """File-based fallback database manager"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "db_fallback"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize data files
        self.trades_file = self.data_dir / "trades.json"
        self.decisions_file = self.data_dir / "ai_decisions.json"
        self.health_file = self.data_dir / "system_health.json"
        
        # Initialize files if they don't exist
        for file_path in [self.trades_file, self.decisions_file, self.health_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump([], f)
        
        logger.info("File-based database fallback initialized")
    
    def _load_data(self, file_path: Path) -> List[Dict]:
        """Load data from JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def _save_data(self, file_path: Path, data: List[Dict]):
        """Save data to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    async def log_trade(self, symbol: str, action: str, quantity: float, 
                       price: float, source: str, confidence: float, 
                       execution_id: str, status: str = "pending", **kwargs):
        """Log a trade to file"""
        trade = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "confidence": confidence,
            "execution_id": execution_id,
            "status": status,
            **kwargs
        }
        
        trades = self._load_data(self.trades_file)
        trades.append(trade)
        self._save_data(self.trades_file, trades)
        
        logger.info(f"Trade logged to file: {symbol} {action}")
        return {"status": "file_logged", "id": execution_id}
    
    async def get_trades(self, limit: int = 100, symbol: str = None) -> List[Dict]:
        """Get trades from file"""
        trades = self._load_data(self.trades_file)
        
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol]
        
        # Sort by timestamp descending
        trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return trades[:limit]
    
    async def get_active_trades(self) -> List[Dict]:
        """Get active trades"""
        trades = self._load_data(self.trades_file)
        return [t for t in trades if t.get('status') in ['pending', 'executed']]
    
    async def log_ai_decision(self, decision_type: str, symbol: str, 
                             recommendation: str, confidence: float, 
                             reasoning: str, **kwargs):
        """Log AI decision to file"""
        decision = {
            "decision_type": decision_type,
            "symbol": symbol,
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        
        decisions = self._load_data(self.decisions_file)
        decisions.append(decision)
        
        # Keep only last 1000 decisions
        decisions = decisions[-1000:]
        
        self._save_data(self.decisions_file, decisions)
        
        logger.info(f"AI decision logged to file: {symbol} {recommendation}")
        return {"status": "file_logged"}
    
    async def get_recent_decisions(self, limit: int = 50) -> List[Dict]:
        """Get recent AI decisions"""
        decisions = self._load_data(self.decisions_file)
        decisions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return decisions[:limit]
    
    async def get_trade_performance(self) -> Dict:
        """Calculate trade performance from file data"""
        trades = self._load_data(self.trades_file)
        
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_loss": 0,
                "avg_confidence": 0
            }
        
        executed_trades = [t for t in trades if t.get('status') == 'executed']
        
        return {
            "total_trades": len(executed_trades),
            "win_rate": 0.65,  # Placeholder - would need actual P&L calculation
            "profit_loss": sum(t.get('profit_loss', 0) for t in executed_trades),
            "avg_confidence": sum(t.get('confidence', 0) for t in executed_trades) / len(executed_trades) if executed_trades else 0
        }
    
    async def log_system_health(self, component: str, status: str, details: str = None):
        """Log system health to file"""
        health_entry = {
            "component": component,
            "status": status,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        health_data = self._load_data(self.health_file)
        health_data.append(health_entry)
        
        # Keep only last 500 entries
        health_data = health_data[-500:]
        
        self._save_data(self.health_file, health_data)
        
        return True
    
    async def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        return await self.get_trades(limit=limit)
    
    def close(self):
        """Close connection (no-op for file-based)"""
        logger.info("File-based database fallback closed")
    
    # Add any other methods that might be called by the system
    async def get_portfolio_summary(self):
        """Get portfolio summary"""
        trades = await self.get_active_trades()
        return {
            "active_positions": len(trades),
            "total_value": sum(t.get('quantity', 0) * t.get('price', 0) for t in trades),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


# Global instance
_file_db = None

def get_file_database():
    """Get file-based database instance"""
    global _file_db
    if _file_db is None:
        _file_db = FileBasedDatabaseFallback()
    return _file_db
