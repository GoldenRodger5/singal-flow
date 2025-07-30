"""
Enhanced Trading UI with comprehensive controls and real-time features
"""

import streamlit as st
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service imports for enhanced features
try:
    from services.enhanced_ui_controls import render_enhanced_controls, show_current_settings
    from services.current_holdings_dashboard import show_current_holdings
    from services.ai_predictions_dashboard import show_ai_predictions
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    ENHANCED_FEATURES_AVAILABLE = False
    logger.warning(f"Enhanced features not available: {e}")

# Set page configuration
st.set_page_config(
    page_title="SignalFlow Enhanced Trading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main trading UI application."""
    st.title("📈 SignalFlow Enhanced Trading System")
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar navigation
    page = render_sidebar()
    
    # Main content area
    if page == "Enhanced Dashboard":
        render_enhanced_dashboard()
    elif page == "Current Holdings":
        render_holdings_page()
    elif page == "AI Predictions":
        render_ai_predictions_page()
    elif page == "Quick Controls":
        render_controls_page()
    elif page == "Configuration":
        render_configuration_page()
    else:
        render_main_dashboard()

def initialize_session_state():
    """Initialize session state variables."""
    if 'confidence_threshold' not in st.session_state:
        st.session_state.confidence_threshold = 6.0
    if 'position_multiplier' not in st.session_state:
        st.session_state.position_multiplier = 1.0
    if 'auto_execute_threshold' not in st.session_state:
        st.session_state.auto_execute_threshold = 9.5
    if 'paper_trading' not in st.session_state:
        st.session_state.paper_trading = True
    if 'williams_r_oversold' not in st.session_state:
        st.session_state.williams_r_oversold = -80
    if 'volume_multiplier' not in st.session_state:
        st.session_state.volume_multiplier = 3.0
    if 'momentum_min' not in st.session_state:
        st.session_state.momentum_min = 5
    if 'max_daily_risk' not in st.session_state:
        st.session_state.max_daily_risk = 15

def render_sidebar():
    """Render sidebar navigation."""
    st.sidebar.title("🎯 Navigation")
    
    pages = [
        "Enhanced Dashboard",
        "Current Holdings", 
        "AI Predictions",
        "Quick Controls",
        "Configuration"
    ]
    
    selected_page = st.sidebar.selectbox("Select Page", pages)
    
    # Quick status indicators
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 System Status")
    
    # Mock status indicators
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.sidebar.markdown("🟢 **Trading:** Active")
        st.sidebar.markdown("🟢 **AI Engine:** Running")
    with col2:
        st.sidebar.markdown("🟡 **Signals:** 3 Active")
        st.sidebar.markdown("🟢 **Data Feed:** Live")
    
    # Quick stats
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Quick Stats")
    st.sidebar.metric("Portfolio Value", "$94,250", "↗️ +2.1%")
    st.sidebar.metric("Active Positions", "5", "→ No change")
    st.sidebar.metric("Today's P&L", "+$1,247", "↗️ +1.3%")
    
    return selected_page

def render_enhanced_dashboard():
    """Render the enhanced main dashboard."""
    st.markdown("## 🚀 Enhanced Trading Dashboard")
    
    # Top metrics row
    render_top_metrics()
    
    # Two-column layout
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        # Main chart area
        render_main_chart()
        
        # Recent signals
        render_recent_signals()
        
    with right_col:
        # Enhanced controls
        if ENHANCED_FEATURES_AVAILABLE:
            render_enhanced_controls()
        else:
            st.warning("Enhanced controls not available")
        
        # Quick actions
        render_quick_actions()

def render_holdings_page():
    """Render the current holdings page."""
    if ENHANCED_FEATURES_AVAILABLE:
        show_current_holdings()
    else:
        st.error("Holdings dashboard not available")
        render_basic_holdings()

def render_ai_predictions_page():
    """Render the AI predictions page."""
    if ENHANCED_FEATURES_AVAILABLE:
        show_ai_predictions()
    else:
        st.error("AI predictions not available")
        render_basic_predictions()

def render_controls_page():
    """Render the quick controls page."""
    if ENHANCED_FEATURES_AVAILABLE:
        render_enhanced_controls()
        st.markdown("---")
        show_current_settings()
    else:
        st.error("Enhanced controls not available")
        render_basic_controls()

def render_configuration_page():
    """Render the configuration page."""
    st.markdown("## ⚙️ System Configuration")
    
    if ENHANCED_FEATURES_AVAILABLE:
        show_current_settings()
    else:
        st.warning("Dynamic configuration not available")
    
    # Basic configuration options
    st.markdown("### 🔧 Basic Settings")
    
    paper_mode = st.toggle("Paper Trading Mode", value=True)
    debug_mode = st.toggle("Debug Mode", value=False)
    notifications = st.toggle("Enable Notifications", value=True)
    
    if st.button("Save Configuration"):
        st.success("Configuration saved!")

def render_main_dashboard():
    """Render the basic main dashboard."""
    st.markdown("## 📊 Trading Dashboard")
    
    # Basic metrics
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("Portfolio Value", "$94,250", "2.1%")
    with metric_col2:
        st.metric("Active Trades", "5", "0")
    with metric_col3:
        st.metric("Today's P&L", "+$1,247", "1.3%")
    with metric_col4:
        st.metric("Win Rate", "76%", "3%")
    
    # Basic chart
    render_basic_chart()

def render_top_metrics():
    """Render top performance metrics."""
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    
    with metric_col1:
        st.metric(
            "💰 Portfolio Value", 
            "$94,250", 
            "↗️ +$1,950 (2.1%)",
            help="Total portfolio value including cash"
        )
    
    with metric_col2:
        st.metric(
            "📊 Active Positions", 
            "5", 
            "→ No change",
            help="Number of current open positions"
        )
    
    with metric_col3:
        st.metric(
            "📈 Today's P&L", 
            "+$1,247", 
            "↗️ +1.3%",
            help="Profit/loss for current trading session"
        )
    
    with metric_col4:
        st.metric(
            "🎯 Win Rate", 
            "76%", 
            "↗️ +3%",
            help="Percentage of profitable trades (last 30 days)"
        )
    
    with metric_col5:
        st.metric(
            "⚡ AI Confidence", 
            "8.2/10", 
            "↗️ +0.5",
            help="Average AI confidence in current signals"
        )

def render_main_chart():
    """Render the main trading chart."""
    st.markdown("### 📈 Market Overview")
    
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    sample_data = pd.DataFrame({
        'date': dates,
        'price': 150 + (pd.Series(range(len(dates))) * 0.5) + (pd.Series(range(len(dates))) * 0.1).apply(lambda x: x % 10 - 5),
        'volume': 1000000 + (pd.Series(range(len(dates))) * 10000)
    })
    
    # Create subplot
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price Chart", "Volume")
    )
    
    # Price chart
    fig.add_trace(
        go.Scatter(
            x=sample_data['date'],
            y=sample_data['price'],
            mode='lines',
            name='Price',
            line=dict(color='#00D4AA', width=2)
        ),
        row=1, col=1
    )
    
    # Volume chart
    fig.add_trace(
        go.Bar(
            x=sample_data['date'],
            y=sample_data['volume'],
            name='Volume',
            marker_color='rgba(0, 212, 170, 0.5)'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="Market Data",
        xaxis_title="Date",
        height=500,
        showlegend=False,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_recent_signals():
    """Render recent trading signals."""
    st.markdown("### 🚨 Recent Signals")
    
    # Sample signals data
    signals_data = {
        'Time': ['14:32:15', '14:28:42', '14:25:11', '14:21:33', '14:18:07'],
        'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
        'Action': ['BUY', 'SELL', 'BUY', 'BUY', 'SELL'],
        'Confidence': [8.5, 7.2, 9.1, 6.8, 8.9],
        'Price': ['$155.23', '$297.45', '$2,548.17', '$248.92', '$421.56'],
        'Status': ['Executed', 'Pending', 'Executed', 'Rejected', 'Executed']
    }
    
    signals_df = pd.DataFrame(signals_data)
    
    # Style the dataframe
    def style_signals(row):
        if row['Action'] == 'BUY':
            return ['background-color: rgba(0, 255, 0, 0.1)'] * len(row)
        elif row['Action'] == 'SELL':
            return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
        else:
            return [''] * len(row)
    
    styled_df = signals_df.style.apply(style_signals, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

def render_quick_actions():
    """Render quick action buttons."""
    st.markdown("### ⚡ Quick Actions")
    
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("🛑 Pause Trading", type="secondary", use_container_width=True):
            st.warning("Trading paused!")
        
        if st.button("📊 Generate Report", type="secondary", use_container_width=True):
            st.info("Report generated!")
    
    with action_col2:
        if st.button("🔄 Force Refresh", type="secondary", use_container_width=True):
            st.experimental_rerun()
        
        if st.button("⚙️ Emergency Stop", type="primary", use_container_width=True):
            st.error("Emergency stop activated!")

def render_basic_holdings():
    """Render basic holdings when enhanced features not available."""
    st.markdown("## 📊 Basic Holdings")
    st.info("Enhanced holdings dashboard not available. Showing basic view.")
    
    # Sample holdings
    holdings_data = {
        'Symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'Quantity': [100, 50, 25],
        'Avg Price': ['$150.00', '$300.00', '$2500.00'],
        'Current Price': ['$155.00', '$295.00', '$2550.00'],
        'P&L': ['+$500', '-$250', '+$1250']
    }
    
    st.dataframe(pd.DataFrame(holdings_data), use_container_width=True, hide_index=True)

def render_basic_predictions():
    """Render basic predictions when AI features not available."""
    st.markdown("## 🤖 Basic Predictions")
    st.info("AI predictions dashboard not available. Showing basic view.")
    
    # Sample predictions
    predictions_data = {
        'Symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'Direction': ['↗️ Bullish', '↘️ Bearish', '↗️ Bullish'],
        'Confidence': ['8.5/10', '7.2/10', '9.1/10'],
        'Target': ['$160.00', '$290.00', '$2600.00']
    }
    
    st.dataframe(pd.DataFrame(predictions_data), use_container_width=True, hide_index=True)

def render_basic_controls():
    """Render basic controls when enhanced features not available."""
    st.markdown("## ⚙️ Basic Controls")
    st.info("Enhanced controls not available. Showing basic view.")
    
    # Basic sliders
    confidence = st.slider("Confidence Threshold", 1.0, 10.0, 6.0, 0.5)
    position_size = st.slider("Position Size", 0.1, 1.0, 0.25, 0.05)
    
    if st.button("Update Settings"):
        st.success("Settings updated!")

def render_basic_chart():
    """Render basic chart when enhanced features not available."""
    # Simple line chart
    chart_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30),
        'value': range(30)
    })
    
    st.line_chart(chart_data.set_index('date'))


def render_basic_holdings():
    """Render basic holdings when full dashboard not available."""
    st.markdown("## 📊 Portfolio Overview")
    st.info("📈 **No current positions**\n\nYour portfolio is empty. Holdings will appear here after trades are executed.")


def render_basic_predictions():
    """Render basic predictions when AI features not available."""
    st.markdown("## 🤖 AI Predictions")
    st.info("🧠 **No AI predictions available**\n\nThe AI is still learning and collecting data. Predictions will appear here after the system has processed enough market data.")


if __name__ == "__main__":
    main()
