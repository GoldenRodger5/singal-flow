"""
Real-time Trading System Dashboard
Live monitoring of the Enhanced Trading System with MongoDB Atlas integration
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime, timedelta
import time
import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import asyncio
import motor.motor_asyncio


class LiveTradingDashboard:
    """Real-time dashboard for the Enhanced Trading System."""
    
    def __init__(self):
        self.api_base_url = f"http://localhost:{os.getenv('LOCAL_SERVER_PORT', 8000)}"
        self.mongo_url = os.getenv('MONGODB_URL')
        self.db_name = os.getenv('MONGODB_NAME', 'signal_flow_trading')
        
        # Initialize MongoDB connection
        self.client = None
        self.db = None
        
        if self.mongo_url:
            try:
                self.client = MongoClient(
                    self.mongo_url,
                    server_api=ServerApi('1'),
                    connectTimeoutMS=10000,
                    serverSelectionTimeoutMS=10000
                )
                self.db = self.client[self.db_name]
                # Test connection
                self.client.admin.command('ping')
            except Exception as e:
                st.error(f"MongoDB connection failed: {e}")
                self.client = None
                self.db = None
    
    def get_system_status(self):
        """Get current system status from FastAPI server."""
        try:
            response = requests.get(f"{self.api_base_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            return {"error": str(e)}
    
    def get_system_health(self):
        """Get system health from FastAPI server."""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            return {"error": str(e)}
    
    def get_trades_data(self, limit=50):
        """Get trades from API or MongoDB as fallback."""
        # Try API first
        try:
            response = requests.get(f"{self.api_base_url}/api/trades", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'trades' in data and data['trades']:
                    return pd.DataFrame(data['trades'])
        except Exception as e:
            pass  # Fall back to MongoDB
        
        # Fallback to MongoDB
        try:
            if not self.db:
                return pd.DataFrame()
            
            trades = list(self.db.trades.find().sort("timestamp", -1).limit(limit))
            return pd.DataFrame(trades) if trades else pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
    
    def get_ai_decisions_from_db(self, limit=20):
    
    def get_trades_from_mongodb(self, limit=50):
    def get_trades_from_mongodb(self, limit=50):
        """Get recent trades from MongoDB Atlas."""
        try:
            if not self.db:
                return pd.DataFrame()
            
            trades = list(self.db.trades.find().sort("timestamp", -1).limit(limit))
            return pd.DataFrame(trades) if trades else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching trades: {e}")
            return pd.DataFrame()
    
    def get_ai_decisions_from_db(self, limit=20):
        """Get recent AI decisions from MongoDB Atlas."""
        try:
            if not self.db:
                return pd.DataFrame()
            
            decisions = list(self.db.ai_decisions.find().sort("timestamp", -1).limit(limit))
            return pd.DataFrame(decisions) if decisions else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching AI decisions: {e}")
            return pd.DataFrame()
    
    def get_performance_metrics(self):
        """Get performance metrics from MongoDB."""
        try:
            if not self.db:
                return {}
                
            # Get trade performance
            pipeline = [
                {"$group": {
                    "_id": None,
                    "total_trades": {"$sum": 1},
                    "total_pnl": {"$sum": "$profit_loss"},
                    "winning_trades": {"$sum": {"$cond": [{"$gt": ["$profit_loss", 0]}, 1, 0]}},
                    "losing_trades": {"$sum": {"$cond": [{"$lt": ["$profit_loss", 0]}, 1, 0]}}
                }}
            ]
            
            result = list(self.db.trades.aggregate(pipeline))
            if result:
                metrics = result[0]
                metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades'] * 100) if metrics['total_trades'] > 0 else 0
                return metrics
            return {}
        except Exception as e:
            st.error(f"Error calculating performance: {e}")
            return {}


def main():
    st.set_page_config(
        page_title="Live Trading Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize dashboard
    dashboard = LiveTradingDashboard()
    
    # Header
    st.title("🚀 Enhanced Trading System - Live Dashboard")
    st.markdown("---")
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 10, 120, 30)
    
    if auto_refresh:
        # Auto-refresh every N seconds
        placeholder = st.empty()
        while True:
            with placeholder.container():
                render_dashboard(dashboard)
            time.sleep(refresh_rate)
    else:
        # Manual refresh
        if st.sidebar.button("🔄 Refresh Data"):
            st.rerun()
        render_dashboard(dashboard)


def render_dashboard(dashboard):
    """Render the main dashboard content."""
    
    # System Status Section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🖥️ System Status")
        status = dashboard.get_system_status()
        if status and "error" not in status:
            st.success("✅ System Running")
            
            # Display key metrics
            if "trading_system" in status:
                trading_status = status["trading_system"]
                st.metric("Uptime", f"{trading_status.get('session_stats', {}).get('uptime_minutes', 0):.1f} min")
                st.metric("Trades Today", trading_status.get('session_stats', {}).get('trades_executed', 0))
                st.metric("Signals Generated", trading_status.get('session_stats', {}).get('signals_generated', 0))
        else:
            st.error("❌ System Offline")
            st.write(status.get("error", "Unknown error"))
    
    with col2:
        st.subheader("💾 Database Status")
        health = dashboard.get_system_health()
        if health and "components" in health:
            components = health["components"]
            
            if components.get("database", False):
                st.success("✅ MongoDB Atlas Connected")
            else:
                st.error("❌ Database Disconnected")
            
            if components.get("trading_system", False):
                st.success("✅ Trading System Active")
            else:
                st.error("❌ Trading System Inactive")
            
            if components.get("telegram", False):
                st.success("✅ Telegram Bot Active")
            else:
                st.warning("⚠️ Telegram Offline")
    
    with col3:
        st.subheader("📊 Performance Summary")
        metrics = dashboard.get_performance_metrics()
        if metrics:
            st.metric("Total Trades", metrics.get('total_trades', 0))
            st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
            
            total_pnl = metrics.get('total_pnl', 0) or 0
            pnl_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("Total P&L", f"${total_pnl:.2f}", delta_color=pnl_color)
        else:
            st.info("No performance data available yet")
    
    st.markdown("---")
    
    # Recent Trades Section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Recent Trades")
        trades_df = dashboard.get_trades_data(20)
        
        if not trades_df.empty:
            # Clean up the dataframe for display
            display_trades = trades_df[['symbol', 'action', 'quantity', 'price', 'timestamp', 'status']].copy()
            display_trades['timestamp'] = pd.to_datetime(display_trades['timestamp']).dt.strftime('%H:%M:%S')
            display_trades = display_trades.sort_values('timestamp', ascending=False)
            
            st.dataframe(
                display_trades,
                use_container_width=True,
                hide_index=True
            )
            
            # P&L Chart if profit_loss data exists
            if 'profit_loss' in trades_df.columns:
                pnl_data = trades_df[trades_df['profit_loss'].notna()]
                if not pnl_data.empty:
                    fig = px.bar(
                        pnl_data.head(10),
                        x='symbol',
                        y='profit_loss',
                        title="Recent Trade P&L",
                        color='profit_loss',
                        color_continuous_scale=['red', 'green']
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades executed yet")
    
    with col2:
        st.subheader("🧠 AI Decisions")
        ai_decisions_df = dashboard.get_ai_decisions_from_db(10)
        
        if not ai_decisions_df.empty:
            for _, decision in ai_decisions_df.iterrows():
                with st.expander(f"{decision.get('symbol', 'Unknown')} - {decision.get('action', 'N/A')} (Confidence: {decision.get('confidence', 0):.2f})"):
                    st.write(f"**Reasoning:** {decision.get('reasoning', 'No reasoning provided')}")
                    st.write(f"**Timestamp:** {decision.get('timestamp', 'Unknown')}")
                    if 'market_conditions' in decision:
                        st.write(f"**Market Conditions:** {decision['market_conditions']}")
        else:
            st.info("No AI decisions recorded yet")
    
    st.markdown("---")
    
    # System Configuration
    with st.expander("⚙️ System Configuration"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Trading Mode**")
            st.write("Paper Trading: ✅")
            st.write("Auto Execute: ✅")
            st.write("AI Explanations: ✅")
        
        with col2:
            st.write("**Risk Management**")
            st.write(f"Max Daily Trades: {os.getenv('MAX_DAILY_TRADES', 50)}")
            st.write(f"Max Daily Loss: {float(os.getenv('MAX_DAILY_LOSS_PCT', 0.025)) * 100}%")
            st.write(f"Min Confidence: {float(os.getenv('MIN_CONFIDENCE_THRESHOLD', 0.65)) * 100}%")
        
        with col3:
            st.write("**API Endpoints**")
            api_base = f"http://localhost:{os.getenv('LOCAL_SERVER_PORT', 8000)}"
            st.write(f"Health: {api_base}/health")
            st.write(f"Status: {api_base}/status")
            st.write(f"Trades: {api_base}/api/trades")
    
    # Live System Logs (if available)
    with st.expander("📋 Recent System Activity"):
        try:
            # Get recent system health logs
            if dashboard.db:
                health_logs = list(dashboard.db.system_health.find().sort("timestamp", -1).limit(10))
                if health_logs:
                    for log in health_logs:
                        timestamp = log.get('timestamp', 'Unknown')
                        component = log.get('component', 'Unknown')
                        status = log.get('status', 'Unknown')
                        st.write(f"**{timestamp}** - {component}: {status}")
                else:
                    st.info("No system logs available")
            else:
                st.warning("Database connection not available for logs")
        except Exception as e:
            st.warning(f"Could not fetch system logs: {e}")


if __name__ == "__main__":
    main()
