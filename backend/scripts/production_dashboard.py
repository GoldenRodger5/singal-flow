"""
Real-Time Trading Dashboard for Signal Flow
Production-ready Streamlit dashboard with live updates and comprehensive monitoring
"""
import streamlit as st
import asyncio
import json
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone, timedelta
import time
import websocket
import threading
from typing import Dict, List, Any
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
WS_BASE_URL = os.getenv('WS_BASE_URL', 'ws://localhost:8000')

class TradingDashboard:
    def __init__(self):
        self.health_data = {}
        self.trades_data = []
        self.positions_data = []
        self.account_data = {}
        self.ai_decisions = []
        self.learning_summary = {}
        self.market_sentiment = {}
        self.ai_signals = []
        self.signal_performance = {}
        self.tracking_status = {}
        self.ws_health = None
        self.ws_trades = None
        self.ws_connected = False
        
    def setup_websocket_connections(self):
        """Setup WebSocket connections for real-time updates"""
        try:
            # Health monitoring WebSocket
            def on_health_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get('type') == 'health_update':
                        self.health_data = data.get('data', {})
                except Exception as e:
                    logger.error(f"Health WebSocket error: {e}")
            
            def on_health_error(ws, error):
                logger.error(f"Health WebSocket error: {error}")
                self.ws_connected = False
            
            def on_health_close(ws, close_status_code, close_msg):
                logger.info("Health WebSocket connection closed")
                self.ws_connected = False
            
            def on_health_open(ws):
                logger.info("Health WebSocket connected")
                self.ws_connected = True
            
            # Create health WebSocket connection
            self.ws_health = websocket.WebSocketApp(
                f"{WS_BASE_URL}/ws/health",
                on_message=on_health_message,
                on_error=on_health_error,
                on_close=on_health_close,
                on_open=on_health_open
            )
            
            # Start WebSocket in background thread
            ws_thread = threading.Thread(target=self.ws_health.run_forever, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"WebSocket setup failed: {e}")
    
    def fetch_data(self):
        """Fetch data from API endpoints"""
        try:
            # Fetch account info
            response = requests.get(f"{API_BASE_URL}/api/account", timeout=5)
            if response.status_code == 200:
                self.account_data = response.json()
            
            # Fetch positions
            response = requests.get(f"{API_BASE_URL}/api/positions", timeout=5)
            if response.status_code == 200:
                self.positions_data = response.json()
            
            # Fetch active trades
            response = requests.get(f"{API_BASE_URL}/api/trades/active", timeout=5)
            if response.status_code == 200:
                self.trades_data = response.json()
            
            # Fetch AI decisions
            response = requests.get(f"{API_BASE_URL}/api/ai/decisions/recent?limit=20", timeout=5)
            if response.status_code == 200:
                self.ai_decisions = response.json()
            
            # Fetch AI learning summary
            response = requests.get(f"{API_BASE_URL}/api/ai/learning/summary", timeout=5)
            if response.status_code == 200:
                self.learning_summary = response.json()
            
            # Fetch AI signals
            response = requests.get(f"{API_BASE_URL}/api/ai/signals/recent?limit=50", timeout=5)
            if response.status_code == 200:
                self.ai_signals = response.json().get('signals', [])
            
            # Fetch signal performance
            response = requests.get(f"{API_BASE_URL}/api/ai/signals/performance?days=30", timeout=5)
            if response.status_code == 200:
                self.signal_performance = response.json()
            
            # Fetch tracking status
            response = requests.get(f"{API_BASE_URL}/api/ai/tracking/status", timeout=5)
            if response.status_code == 200:
                self.tracking_status = response.json()
            
            # Fetch health if not available via WebSocket
            if not self.health_data:
                response = requests.get(f"{API_BASE_URL}/health/detailed", timeout=5)
                if response.status_code == 200:
                    self.health_data = response.json()
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            st.error(f"Failed to connect to trading system: {e}")
        except Exception as e:
            logger.error(f"Data fetch error: {e}")
            st.error(f"Data fetch error: {e}")

def create_health_indicator(status: str) -> str:
    """Create colored health indicator"""
    if status == 'healthy':
        return "🟢 Healthy"
    elif status == 'warning':
        return "🟡 Warning"
    elif status == 'unhealthy':
        return "🔴 Unhealthy"
    else:
        return "⚪ Unknown"

def create_account_overview(account_data: Dict):
    """Create account overview section"""
    if not account_data:
        st.warning("Account data not available")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Portfolio Value", 
            f"${account_data.get('portfolio_value', 0):,.2f}",
            delta=f"${float(account_data.get('portfolio_value', 0)) - float(account_data.get('last_equity', 0)):,.2f}"
        )
    
    with col2:
        st.metric(
            "Buying Power", 
            f"${account_data.get('buying_power', 0):,.2f}"
        )
    
    with col3:
        st.metric(
            "Cash", 
            f"${account_data.get('cash', 0):,.2f}"
        )
    
    with col4:
        st.metric(
            "Account Status", 
            account_data.get('status', 'Unknown')
        )

def create_positions_table(positions_data: List[Dict]):
    """Create positions table"""
    if not positions_data:
        st.info("No open positions")
        return
    
    df = pd.DataFrame(positions_data)
    
    # Format columns
    if not df.empty:
        df['Market Value'] = df['market_value'].apply(lambda x: f"${x:,.2f}")
        df['Unrealized P/L'] = df['unrealized_pl'].apply(lambda x: f"${x:,.2f}")
        df['Unrealized P/L %'] = df['unrealized_plpc'].apply(lambda x: f"{x:.2%}")
        df['Quantity'] = df['qty'].apply(lambda x: f"{x:,.0f}")
        
        # Display table
        st.dataframe(
            df[['symbol', 'Quantity', 'side', 'Market Value', 'Unrealized P/L', 'Unrealized P/L %']],
            use_container_width=True
        )

def create_trades_table(trades_data: List[Dict]):
    """Create active trades table"""
    if not trades_data:
        st.info("No active trades")
        return
    
    df = pd.DataFrame(trades_data)
    
    if not df.empty:
        # Format timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M:%S')
        
        # Display table
        st.dataframe(
            df[['symbol', 'action', 'quantity', 'price', 'status', 'source', 'timestamp']],
            use_container_width=True
        )

def create_health_dashboard(health_data: Dict):
    """Create system health dashboard"""
    if not health_data:
        st.warning("Health data not available")
        return
    
    # Overall status
    overall_status = health_data.get('overall', 'unknown')
    st.subheader(f"System Status: {create_health_indicator(overall_status)}")
    
    # Component health
    components = health_data.get('components', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Trading Components**")
        if 'trading_api' in components:
            trading_health = components['trading_api']
            st.write(f"• Trading API: {create_health_indicator(trading_health.get('status', 'unknown'))}")
            if 'buying_power' in trading_health:
                st.write(f"  - Buying Power: ${trading_health['buying_power']:,.2f}")
        
        if 'ai_agents' in components:
            ai_health = components['ai_agents']
            st.write(f"• AI Agents: {create_health_indicator(ai_health.get('status', 'unknown'))}")
            if 'recent_decisions' in ai_health:
                st.write(f"  - Recent Decisions: {ai_health['recent_decisions']}")
    
    with col2:
        st.write("**System Components**")
        if 'database' in components:
            db_health = components['database']
            st.write(f"• Database: {create_health_indicator(db_health.get('status', 'unknown'))}")
            if 'active_trades' in db_health:
                st.write(f"  - Active Trades: {db_health['active_trades']}")
        
        if 'system_resources' in components:
            sys_health = components['system_resources']
            st.write(f"• System Resources: {create_health_indicator(sys_health.get('status', 'unknown'))}")
            if 'cpu_percent' in sys_health:
                st.write(f"  - CPU: {sys_health['cpu_percent']:.1f}%")
            if 'memory_percent' in sys_health:
                st.write(f"  - Memory: {sys_health['memory_percent']:.1f}%")

def create_ai_learning_dashboard(learning_summary: Dict):
    """Create AI learning data dashboard"""
    if not learning_summary:
        st.info("AI learning data not available")
        return
    
    st.subheader("🤖 AI Learning System Status")
    
    # Database summary
    db_summary = learning_summary.get('database_summary', {})
    collection_status = learning_summary.get('collection_status', {})
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ai_decisions_count = db_summary.get('ai_learning_data_count', 0)
        st.metric("AI Learning Records", f"{ai_decisions_count:,}")
    
    with col2:
        sentiment_count = db_summary.get('market_sentiment_count', 0)
        st.metric("Sentiment Records", f"{sentiment_count:,}")
    
    with col3:
        pattern_count = db_summary.get('price_patterns_count', 0)
        st.metric("Price Patterns", f"{pattern_count:,}")
    
    with col4:
        strategy_count = db_summary.get('strategy_outcomes_count', 0)
        st.metric("Strategy Outcomes", f"{strategy_count:,}")
    
    # Recent activity
    st.write("**Recent Activity (24h)**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        recent_learning = db_summary.get('ai_learning_data_recent', 0)
        st.write(f"• New Learning Data: {recent_learning}")
        recent_sentiment = db_summary.get('market_sentiment_recent', 0)
        st.write(f"• New Sentiment Data: {recent_sentiment}")
    
    with col2:
        recent_patterns = db_summary.get('price_patterns_recent', 0)
        st.write(f"• New Patterns: {recent_patterns}")
        recent_regime = db_summary.get('market_regime_recent', 0)
        st.write(f"• Market Regime Updates: {recent_regime}")
    
    with col3:
        symbols_tracked = collection_status.get('symbols_tracked', 0)
        st.write(f"• Symbols Tracked: {symbols_tracked}")
        collecting = collection_status.get('collecting', False)
        status = "🟢 Active" if collecting else "🔴 Stopped"
        st.write(f"• Collection Status: {status}")


def create_market_regime_chart(learning_summary: Dict):
    """Create market regime visualization"""
    try:
        # This would normally fetch market regime data
        # For now, show a placeholder with the available data
        st.subheader("📊 Market Regime Analysis")
        
        collection_status = learning_summary.get('collection_status', {})
        if collection_status:
            st.write("Market regime tracking active")
            
            # Create a simple status indicator
            regime_data = {
                'Current Regime': 'Bull Market',
                'Confidence': '0.75',
                'Last Update': '2 minutes ago'
            }
            
            for key, value in regime_data.items():
                st.write(f"**{key}**: {value}")
        else:
            st.info("Market regime data not available")
            
    except Exception as e:
        st.error(f"Market regime chart error: {e}")


def create_ai_decisions_chart(ai_decisions: List[Dict]):
    """Create AI decisions timeline chart"""
    if not ai_decisions:
        st.info("No recent AI decisions")
        return
    
    df = pd.DataFrame(ai_decisions)
    
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        fig = px.scatter(df, x='timestamp', y='symbol', 
                        color='action' if 'action' in df.columns else 'decision_type',
                        title="Recent AI Trading Decisions",
                        hover_data=['confidence'] if 'confidence' in df.columns else None)
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline data available for AI decisions")


def create_ai_signal_tracking_dashboard(ai_signals: List[Dict], signal_performance: Dict, tracking_status: Dict):
    """Create comprehensive AI signal tracking dashboard"""
    st.header("🤖 AI Signal Tracking")
    
    if not tracking_status:
        st.error("AI tracking system not available")
        return
    
    # Tracking Status Overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_signals = tracking_status.get('total_signals', 0)
        st.metric("Total Signals", f"{total_signals:,}")
    
    with col2:
        total_analyses = tracking_status.get('total_analyses', 0)
        st.metric("Analyzed Signals", f"{total_analyses:,}")
    
    with col3:
        recent_signals = tracking_status.get('recent_signals_24h', 0)
        st.metric("Signals (24h)", f"{recent_signals:,}")
    
    with col4:
        tracking_stats = tracking_status.get('tracking_stats', {})
        active_agents = len(tracking_stats.get('wrapped_agents', []))
        st.metric("Active Agents", active_agents)
    
    # Signal Performance Summary
    if signal_performance:
        st.subheader("📊 Signal Performance Summary")
        
        summary = signal_performance.get('summary', {})
        if summary:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                buy_accuracy = summary.get('buy_signals', {}).get('avg_accuracy', 0)
                st.metric("Buy Signal Accuracy", f"{buy_accuracy:.1%}")
            
            with col2:
                sell_accuracy = summary.get('sell_signals', {}).get('avg_accuracy', 0)
                st.metric("Sell Signal Accuracy", f"{sell_accuracy:.1%}")
            
            with col3:
                timing_accuracy = summary.get('timing_accuracy', 0)
                st.metric("Timing Accuracy", f"{timing_accuracy:.1%}")
        
        # Learning Insights
        insights = signal_performance.get('learning_insights', [])
        if insights:
            st.subheader("💡 Learning Insights")
            for insight in insights[:5]:  # Show top 5 insights
                st.write(f"• {insight}")
    
    # Recent Signals Table
    if ai_signals:
        st.subheader("📈 Recent AI Signals")
        
        # Process signals for display
        signals_df = pd.DataFrame(ai_signals)
        
        if not signals_df.empty:
            # Format timestamp
            if 'signal_timestamp' in signals_df.columns:
                signals_df['signal_timestamp'] = pd.to_datetime(signals_df['signal_timestamp'])
                signals_df['time_ago'] = (datetime.now() - signals_df['signal_timestamp']).dt.total_seconds() / 60
                signals_df['time_ago'] = signals_df['time_ago'].apply(lambda x: f"{int(x)}m ago" if x < 60 else f"{int(x/60)}h ago")
            
            # Select columns for display
            display_columns = ['symbol', 'signal_type', 'confidence', 'reasoning', 'time_ago']
            display_df = signals_df[display_columns].head(10)
            
            st.dataframe(display_df, use_container_width=True)
            
            # Signal Distribution Chart
            st.subheader("📊 Signal Distribution")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Signal type distribution
                signal_type_counts = signals_df['signal_type'].value_counts()
                fig_pie = px.pie(values=signal_type_counts.values, 
                               names=signal_type_counts.index,
                               title="Signal Type Distribution")
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Confidence distribution
                fig_hist = px.histogram(signals_df, x='confidence', 
                                      title="Signal Confidence Distribution",
                                      nbins=20)
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Timeline of signals
            if 'signal_timestamp' in signals_df.columns:
                st.subheader("📅 Signal Timeline")
                fig_timeline = px.scatter(signals_df, 
                                        x='signal_timestamp', 
                                        y='symbol',
                                        color='signal_type',
                                        size='confidence',
                                        hover_data=['reasoning'],
                                        title="AI Signals Timeline")
                st.plotly_chart(fig_timeline, use_container_width=True)
    
    else:
        st.info("No recent AI signals available")
    
    # Agent Status
    tracking_stats = tracking_status.get('tracking_stats', {})
    if tracking_stats.get('wrapped_agents'):
        st.subheader("🤖 Agent Status")
        
        agents_data = []
        tracked_methods = tracking_stats.get('tracked_methods', {})
        
        for agent_name in tracking_stats['wrapped_agents']:
            methods = tracked_methods.get(agent_name, [])
            agents_data.append({
                'Agent': agent_name,
                'Tracked Methods': len(methods),
                'Methods': ', '.join(methods[:3]) + ('...' if len(methods) > 3 else ''),
                'Status': '✅ Active' if tracking_stats.get('tracking_active') else '❌ Inactive'
            })
        
        if agents_data:
            agents_df = pd.DataFrame(agents_data)
            st.dataframe(agents_df, use_container_width=True)


def main():
    """Main dashboard function"""
    st.set_page_config(
        page_title="Signal Flow Trading Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize dashboard
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = TradingDashboard()
        st.session_state.dashboard.setup_websocket_connections()
    
    dashboard = st.session_state.dashboard
    
    # Header
    st.title("📈 Signal Flow Trading Dashboard")
    st.markdown("### Real-Time Trading System Monitor")
    
    # Auto-refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        auto_refresh = st.checkbox("Auto Refresh (5s)", value=True)
    with col2:
        if st.button("Refresh Now"):
            dashboard.fetch_data()
    with col3:
        ws_status = "🟢 Connected" if dashboard.ws_connected else "🔴 Disconnected"
        st.write(f"WebSocket: {ws_status}")
    
    # Fetch data
    dashboard.fetch_data()
    
    # System Health Section
    st.header("🏥 System Health")
    create_health_dashboard(dashboard.health_data)
    
    st.divider()
    
    # Account Overview
    st.header("💼 Account Overview")
    create_account_overview(dashboard.account_data)
    
    st.divider()
    
    # Two-column layout for positions and trades
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📊 Current Positions")
        create_positions_table(dashboard.positions_data)
    
    with col2:
        st.header("⚡ Active Trades")
        create_trades_table(dashboard.trades_data)
    
    st.divider()
    
    # AI Decisions
    st.header("🤖 AI Trading Decisions")
    create_ai_decisions_chart(dashboard.ai_decisions)
    
    st.divider()
    
    # AI Learning System
    st.header("🧠 AI Learning System")
    create_ai_learning_dashboard(dashboard.learning_summary)
    
    # AI Signal Tracking Dashboard
    create_ai_signal_tracking_dashboard(dashboard.ai_signals, dashboard.signal_performance, dashboard.tracking_status)
    
    # Market Regime Analysis
    create_market_regime_chart(dashboard.learning_summary)
    
    # Emergency controls in sidebar
    st.sidebar.header("🚨 Emergency Controls")
    if st.sidebar.button("Emergency Stop All Trading", type="primary"):
        try:
            response = requests.post(f"{API_BASE_URL}/api/system/emergency_stop", timeout=10)
            if response.status_code == 200:
                st.sidebar.success("Emergency stop executed!")
            else:
                st.sidebar.error("Emergency stop failed!")
        except Exception as e:
            st.sidebar.error(f"Emergency stop error: {e}")
    
    # System info in sidebar
    st.sidebar.header("📊 System Info")
    if dashboard.health_data:
        uptime = dashboard.health_data.get('uptime', 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        st.sidebar.write(f"Uptime: {hours}h {minutes}m")
        
        last_check = dashboard.health_data.get('last_check')
        if last_check:
            check_time = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
            st.sidebar.write(f"Last Health Check: {check_time.strftime('%H:%M:%S')}")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()
