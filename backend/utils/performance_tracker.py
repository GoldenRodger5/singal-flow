"""
Enhanced Performance Tracking & Analytics
Comprehensive logging for regime-aware trading analysis
"""
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import sqlite3


class PerformanceTracker:
    """
    Comprehensive performance tracking for regime-aware trading.
    Logs every signal, execution, exit, and regime classification.
    """
    
    def __init__(self, db_path: str = "logs/performance.db"):
        """Initialize performance tracker with SQLite database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._setup_database()
        logger.info("Performance tracker initialized")
    
    def _setup_database(self):
        """Create performance tracking tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Trading signals table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    ticker TEXT,
                    signal_type TEXT,
                    confidence REAL,
                    market_regime TEXT,
                    regime_confidence REAL,
                    rsi_zscore REAL,
                    momentum_divergence TEXT,
                    volume_trend TEXT,
                    order_flow_signal TEXT,
                    sector_strength REAL,
                    volatility_percentile REAL,
                    trend_strength REAL,
                    expected_move REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    kelly_fraction REAL,
                    risk_reward_ratio REAL,
                    executed BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Trade executions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    timestamp DATETIME,
                    ticker TEXT,
                    action TEXT,
                    price REAL,
                    quantity INTEGER,
                    position_size_usd REAL,
                    market_regime TEXT,
                    commission REAL,
                    slippage REAL,
                    FOREIGN KEY (signal_id) REFERENCES signals (id)
                )
            """)
            
            # Trade exits table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    timestamp DATETIME,
                    ticker TEXT,
                    exit_price REAL,
                    exit_reason TEXT,
                    pnl_usd REAL,
                    pnl_percent REAL,
                    hold_duration_minutes INTEGER,
                    market_regime_entry TEXT,
                    market_regime_exit TEXT,
                    win BOOLEAN,
                    FOREIGN KEY (execution_id) REFERENCES executions (id)
                )
            """)
            
            # Daily performance summary table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_pnl REAL,
                    avg_win REAL,
                    avg_loss REAL,
                    largest_win REAL,
                    largest_loss REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    profit_factor REAL,
                    regime_trending_high_vol INTEGER DEFAULT 0,
                    regime_trending_low_vol INTEGER DEFAULT 0,
                    regime_mean_reverting_high_vol INTEGER DEFAULT 0,
                    regime_mean_reverting_low_vol INTEGER DEFAULT 0,
                    regime_uncertain INTEGER DEFAULT 0
                )
            """)
            
            # Regime performance table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS regime_performance (
                    date TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    regime_confidence REAL,
                    total_signals INTEGER DEFAULT 0,
                    successful_signals INTEGER DEFAULT 0,
                    avg_return REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    PRIMARY KEY (date, regime)
            """)
            
            conn.commit()
    
    def log_signal(self, signal_data: Dict[str, Any]) -> int:
        """
        Log trading signal with all indicator details.
        Returns signal_id for linking executions.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO signals (
                    timestamp, ticker, signal_type, confidence, market_regime, 
                    regime_confidence, rsi_zscore, momentum_divergence, volume_trend,
                    order_flow_signal, sector_strength, volatility_percentile,
                    trend_strength, expected_move, stop_loss, take_profit,
                    position_size, kelly_fraction, risk_reward_ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                signal_data.get('ticker'),
                signal_data.get('signal_type'),
                signal_data.get('confidence'),
                signal_data.get('market_regime'),
                signal_data.get('regime_confidence'),
                signal_data.get('rsi_zscore'),
                signal_data.get('momentum_divergence'),
                signal_data.get('volume_trend'),
                signal_data.get('order_flow_signal'),
                signal_data.get('sector_strength'),
                signal_data.get('volatility_percentile'),
                signal_data.get('trend_strength'),
                signal_data.get('expected_move'),
                signal_data.get('stop_loss'),
                signal_data.get('take_profit'),
                signal_data.get('position_size'),
                signal_data.get('kelly_fraction'),
                signal_data.get('risk_reward_ratio')
            ))
            signal_id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"📊 Signal logged: {signal_data.get('ticker')} - {signal_data.get('signal_type')} (Regime: {signal_data.get('market_regime')})")
        return signal_id
    
    def log_execution(self, signal_id: int, execution_data: Dict[str, Any]) -> int:
        """Log trade execution details."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO executions (
                    signal_id, timestamp, ticker, action, price, quantity,
                    position_size_usd, market_regime, commission, slippage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                datetime.now(),
                execution_data.get('ticker'),
                execution_data.get('action'),
                execution_data.get('price'),
                execution_data.get('quantity'),
                execution_data.get('position_size_usd'),
                execution_data.get('market_regime'),
                execution_data.get('commission', 0),
                execution_data.get('slippage', 0)
            ))
            execution_id = cursor.lastrowid
            
            # Mark signal as executed
            conn.execute("UPDATE signals SET executed = TRUE WHERE id = ?", (signal_id,))
            conn.commit()
        
        logger.info(f"✅ Execution logged: {execution_data.get('ticker')} - ${execution_data.get('position_size_usd')}")
        return execution_id
    
    def log_exit(self, execution_id: int, exit_data: Dict[str, Any]):
        """Log trade exit with P&L calculation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO exits (
                    execution_id, timestamp, ticker, exit_price, exit_reason,
                    pnl_usd, pnl_percent, hold_duration_minutes,
                    market_regime_entry, market_regime_exit, win
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                datetime.now(),
                exit_data.get('ticker'),
                exit_data.get('exit_price'),
                exit_data.get('exit_reason'),
                exit_data.get('pnl_usd'),
                exit_data.get('pnl_percent'),
                exit_data.get('hold_duration_minutes'),
                exit_data.get('market_regime_entry'),
                exit_data.get('market_regime_exit'),
                exit_data.get('pnl_usd', 0) > 0
            ))
            conn.commit()
        
        win_loss = "WIN" if exit_data.get('pnl_usd', 0) > 0 else "LOSS"
        logger.info(f"🎯 Exit logged: {exit_data.get('ticker')} - {win_loss} ${exit_data.get('pnl_usd'):.2f}")
    
    def update_daily_performance(self, date: str = None):
        """Calculate and update daily performance metrics."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            # Get daily trade statistics
            trades_query = """
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN e.pnl_usd > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN e.pnl_usd <= 0 THEN 1 ELSE 0 END) as losing_trades,
                    AVG(CASE WHEN e.pnl_usd > 0 THEN e.pnl_usd ELSE NULL END) as avg_win,
                    AVG(CASE WHEN e.pnl_usd <= 0 THEN e.pnl_usd ELSE NULL END) as avg_loss,
                    MAX(e.pnl_usd) as largest_win,
                    MIN(e.pnl_usd) as largest_loss,
                    SUM(e.pnl_usd) as total_pnl,
                    s.market_regime
                FROM exits e
                JOIN executions ex ON e.execution_id = ex.id
                JOIN signals s ON ex.signal_id = s.id
                WHERE DATE(e.timestamp) = ?
                GROUP BY s.market_regime
            """
            
            regime_stats = pd.read_sql_query(trades_query, conn, params=[date])
            
            if not regime_stats.empty:
                # Calculate overall daily metrics
                total_trades = regime_stats['total_trades'].sum()
                winning_trades = regime_stats['winning_trades'].sum()
                losing_trades = regime_stats['losing_trades'].sum()
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                total_pnl = regime_stats['total_pnl'].sum()
                avg_win = regime_stats['avg_win'].mean()
                avg_loss = regime_stats['avg_loss'].mean()
                largest_win = regime_stats['largest_win'].max()
                largest_loss = regime_stats['largest_loss'].min()
                
                # Calculate profit factor
                total_wins = regime_stats['winning_trades'].sum() * avg_win if avg_win else 0
                total_losses = abs(regime_stats['losing_trades'].sum() * avg_loss) if avg_loss else 1
                profit_factor = total_wins / total_losses if total_losses > 0 else 0
                
                # Count trades by regime
                regime_counts = regime_stats.groupby('market_regime')['total_trades'].sum()
                
                # Insert or update daily performance
                conn.execute("""
                    INSERT OR REPLACE INTO daily_performance (
                        date, total_trades, winning_trades, losing_trades, win_rate,
                        total_pnl, avg_win, avg_loss, largest_win, largest_loss,
                        profit_factor, regime_trending_high_vol, regime_trending_low_vol,
                        regime_mean_reverting_high_vol, regime_mean_reverting_low_vol,
                        regime_uncertain
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date, total_trades, winning_trades, losing_trades, win_rate,
                    total_pnl, avg_win, avg_loss, largest_win, largest_loss,
                    profit_factor, 
                    regime_counts.get('trending_high_vol', 0),
                    regime_counts.get('trending_low_vol', 0),
                    regime_counts.get('mean_reverting_high_vol', 0),
                    regime_counts.get('mean_reverting_low_vol', 0),
                    regime_counts.get('uncertain', 0)
                ))
                
                # Update regime-specific performance
                for _, row in regime_stats.iterrows():
                    regime_win_rate = row['winning_trades'] / row['total_trades'] if row['total_trades'] > 0 else 0
                    avg_pnl = row['total_pnl'] / row['total_trades'] if row['total_trades'] > 0 else 0
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO regime_performance (
                            date, regime, trades, wins, losses, win_rate, total_pnl, avg_pnl
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        date, row['market_regime'], row['total_trades'],
                        row['winning_trades'], row['losing_trades'],
                        regime_win_rate, row['total_pnl'], avg_pnl
                    ))
                
                conn.commit()
                logger.info(f"📈 Daily performance updated: {total_trades} trades, {win_rate:.1%} win rate, ${total_pnl:.2f} P&L")
    
    def get_regime_performance_summary(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance summary by market regime over specified days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    regime,
                    SUM(trades) as total_trades,
                    SUM(wins) as total_wins,
                    AVG(win_rate) as avg_win_rate,
                    SUM(total_pnl) as total_pnl,
                    AVG(avg_pnl) as avg_pnl_per_trade
                FROM regime_performance 
                WHERE date >= ? AND date <= ?
                GROUP BY regime
            """
            
            df = pd.read_sql_query(query, conn, params=[
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            ])
            
            return df.set_index('regime').to_dict('index')
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Get comprehensive daily trading summary."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            # Get daily performance
            daily_perf = pd.read_sql_query(
                "SELECT * FROM daily_performance WHERE date = ?",
                conn, params=[date]
            )
            
            # Get regime breakdown
            regime_perf = pd.read_sql_query(
                "SELECT * FROM regime_performance WHERE date = ?",
                conn, params=[date]
            )
            
            if daily_perf.empty:
                return {"date": date, "message": "No trading activity recorded"}
            
            summary = daily_perf.iloc[0].to_dict()
            summary['regime_breakdown'] = regime_perf.to_dict('records')
            
            return summary
    
    def export_performance_report(self, days: int = 30) -> str:
        """Export comprehensive performance report to JSON."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        report = {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "generated": datetime.now().isoformat(),
            "regime_performance": self.get_regime_performance_summary(days),
            "daily_summaries": []
        }
        
        # Add daily summaries
        current_date = start_date
        while current_date <= end_date:
            daily = self.get_daily_summary(current_date.strftime('%Y-%m-%d'))
            if daily.get('total_trades', 0) > 0:
                report['daily_summaries'].append(daily)
            current_date += timedelta(days=1)
        
        # Save report
        report_path = f"logs/performance_report_{end_date.strftime('%Y%m%d')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📊 Performance report exported: {report_path}")
        return report_path


# Global performance tracker instance
performance_tracker = PerformanceTracker()
