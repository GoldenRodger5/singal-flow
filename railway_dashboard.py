#!/usr/bin/env python3
"""
Railway Cloud Dashboard
Streamlit dashboard optimized for Railway deployment
"""
import os
import sys
import streamlit as st
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging for cloud
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="SignalFlow Live Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_trading_system_url():
    """Get the trading system URL from Railway environment."""
    # If running on Railway, use the internal service URL
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway_url:
        return f"https://{railway_url}"
    else:
        # Fallback to your specific Railway URL
        return "https://web-production-3e19d.up.railway.app"

def fetch_system_status():
    """Fetch system status from the trading API."""
    try:
        base_url = get_trading_system_url()
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_health_status():
    """Fetch health status from the trading API."""
    try:
        base_url = get_trading_system_url()
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def render_system_overview():
    """Render system overview section."""
    st.header("🎯 System Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Trading System Status")
        status = fetch_system_status()
        
        if "error" not in status:
            st.success("✅ System Online")
            st.write(f"**Mode**: {status.get('mode', 'Unknown')}")
            st.write(f"**Environment**: {status.get('environment', 'Unknown')}")
            st.write(f"**Active**: {status.get('trading_active', False)}")
            st.write(f"**Last Update**: {status.get('timestamp', 'Unknown')}")
        else:
            st.error(f"❌ System Error: {status['error']}")
    
    with col2:
        st.subheader("💚 Health Status")
        health = fetch_health_status()
        
        if "error" not in health:
            st.success("✅ System Healthy")
            st.write(f"**Status**: {health.get('status', 'Unknown')}")
            uptime_seconds = health.get('uptime', 0)
            uptime_hours = uptime_seconds / 3600
            st.write(f"**Uptime**: {uptime_hours:.1f} hours")
            st.write(f"**Mode**: {health.get('mode', 'Unknown')}")
        else:
            st.error(f"❌ Health Check Failed: {health['error']}")

def render_trading_metrics():
    """Render trading metrics and performance."""
    st.header("📈 Trading Performance")
    
    # Mock data for now - you'll connect this to your actual database
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", "42", "+5")
    
    with col2:
        st.metric("Win Rate", "65%", "+3%")
    
    with col3:
        st.metric("Profit/Loss", "$1,247", "+$156")
    
    with col4:
        st.metric("AI Confidence", "7.2/10", "+0.3")

def render_live_positions():
    """Render current positions and watchlist."""
    st.header("💼 Current Positions")
    
    # Mock position data - connect to your actual data
    positions_data = {
        "Symbol": ["AAPL", "TSLA", "NVDA"],
        "Shares": [10, 5, 8],
        "Entry Price": [150.25, 245.80, 420.15],
        "Current Price": [152.30, 248.90, 425.60],
        "P&L": ["+$20.50", "+$15.50", "+$43.60"],
        "Status": ["Open", "Open", "Open"]
    }
    
    df = pd.DataFrame(positions_data)
    st.dataframe(df, use_container_width=True)

def render_ai_insights():
    """Render AI insights and recommendations."""
    st.header("🤖 AI Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Recommendations")
        st.write("🎯 **Strong Buy Signal**: AAPL")
        st.write("📊 **Confidence**: 8.5/10")
        st.write("📈 **Expected Move**: +7.2%")
        st.write("⏰ **Time Frame**: 3-5 days")
        
    with col2:
        st.subheader("Market Sentiment")
        st.write("🐂 **Overall**: Bullish")
        st.write("📊 **Volatility**: Moderate")
        st.write("🎯 **Best Sectors**: Technology, Energy")
        st.write("⚠️ **Risk Level**: Medium")

def render_system_logs():
    """Render recent system activity."""
    st.header("📋 Recent Activity")
    
    # Mock log data - connect to your actual logs
    logs = [
        {"Time": "10:45 AM", "Action": "AI Signal Generated", "Symbol": "AAPL", "Type": "BUY"},
        {"Time": "10:30 AM", "Action": "Position Closed", "Symbol": "MSFT", "Type": "SELL"},
        {"Time": "10:15 AM", "Action": "Market Scan Complete", "Symbol": "-", "Type": "INFO"},
        {"Time": "10:00 AM", "Action": "System Health Check", "Symbol": "-", "Type": "OK"},
    ]
    
    df = pd.DataFrame(logs)
    st.dataframe(df, use_container_width=True)

def render_controls():
    """Render system control panel."""
    st.header("🎛️ System Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Trading Parameters")
        
        # Mock controls - you'll connect these to your actual system
        confidence_threshold = st.slider("AI Confidence Threshold", 1.0, 10.0, 7.0, 0.1)
        position_size = st.slider("Position Size ($)", 50, 1000, 200, 50)
        risk_level = st.selectbox("Risk Level", ["Conservative", "Moderate", "Aggressive"])
        
        if st.button("Update Settings"):
            st.success("✅ Settings updated successfully!")
    
    with col2:
        st.subheader("Emergency Controls")
        
        if st.button("🛑 Stop All Trading", type="primary"):
            st.warning("⚠️ This will halt all trading activities")
        
        if st.button("📊 Force Market Scan"):
            st.info("🔄 Triggering immediate market scan...")
        
        if st.button("🧠 Trigger AI Learning"):
            st.info("🤖 Starting AI learning cycle...")

def main():
    """Main dashboard application."""
    st.title("📈 SignalFlow Live Trading Dashboard")
    st.markdown("**Real-time monitoring and control for your AI trading system**")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh (30s)", value=True)
    
    if auto_refresh:
        # Auto-refresh every 30 seconds
        time.sleep(0.1)  # Small delay to prevent too frequent updates
        st.rerun()
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["📊 Overview", "📈 Performance", "💼 Positions", "🤖 AI Insights", "📋 Activity", "🎛️ Controls"]
    )
    
    # Render selected page
    if page == "📊 Overview":
        render_system_overview()
        render_trading_metrics()
    elif page == "📈 Performance":
        render_trading_metrics()
        # Add performance charts here
    elif page == "💼 Positions":
        render_live_positions()
    elif page == "🤖 AI Insights":
        render_ai_insights()
    elif page == "📋 Activity":
        render_system_logs()
    elif page == "🎛️ Controls":
        render_controls()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("🚀 **SignalFlow AI Trading**")
    st.sidebar.markdown(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
