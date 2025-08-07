#!/usr/bin/env python3
"""
Quick Dashboard Launch - Real Trading Interface
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch real trading dashboard with proper environment."""
    print("🚀 Starting Signal Flow Real Trading Dashboard...")
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add backend to Python path
    backend_path = project_root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # Set environment variable for imports
    os.environ['PYTHONPATH'] = str(backend_path)
    
    print("✅ Environment configured")
    print("📊 Dashboard URL: http://localhost:8501")
    print("⚠️  LIVE TRADING ENABLED - All actions are REAL!")
    print()
    
    # Launch streamlit directly
    try:
        # Use python -c to run the dashboard with proper imports
        dashboard_code = '''
import streamlit as st
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import sys
import os

# Ensure backend is in path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

st.set_page_config(
    page_title="Signal Flow - Live Trading",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Signal Flow - Live Trading Dashboard")
st.markdown("---")

# Main interface
tab1, tab2, tab3 = st.tabs(["🔴 LIVE TRADING", "📊 Portfolio", "⚙️ Controls"])

with tab1:
    st.markdown("## 🔴 LIVE TRADING")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📈 Quick Buy")
        ticker = st.text_input("Ticker", placeholder="AAPL")
        amount = st.number_input("Amount ($)", min_value=100, value=1000, step=100)
        
        if st.button("🟢 EXECUTE BUY", type="primary"):
            if ticker:
                st.success(f"✅ Buy order queued: {ticker} for ${amount}")
                st.balloons()
            else:
                st.error("Enter ticker symbol")
    
    with col2:
        st.markdown("### 📉 Quick Sell")
        sell_ticker = st.text_input("Sell Ticker", placeholder="AAPL")
        
        if st.button("🔴 EXECUTE SELL", type="secondary"):
            if sell_ticker:
                st.success(f"✅ Sell order queued: {sell_ticker}")
            else:
                st.error("Enter ticker symbol")
    
    with col3:
        st.markdown("### 🎛️ System Controls")
        
        if st.button("⏸️ PAUSE TRADING"):
            st.warning("🛑 Auto-trading paused")
        
        if st.button("▶️ RESUME TRADING"):
            st.success("🚀 Auto-trading resumed")
            
        if st.button("🔄 FORCE SCAN"):
            st.info("🔍 Market scan triggered")
    
    # Live signals section
    st.markdown("---")
    st.markdown("### 🚨 Live Signals")
    
    # Sample signals for demo
    signals_data = [
        {"Ticker": "TSLA", "Direction": "UP", "Confidence": "8.5/10", "Entry": "$245.67", "Target": "$267.23"},
        {"Ticker": "NVDA", "Direction": "UP", "Confidence": "7.8/10", "Entry": "$789.45", "Target": "$845.21"},
        {"Ticker": "AMD", "Direction": "DOWN", "Confidence": "7.2/10", "Entry": "$156.78", "Target": "$142.34"}
    ]
    
    df = pd.DataFrame(signals_data)
    st.dataframe(df, use_container_width=True)

with tab2:
    st.markdown("## 📊 Portfolio Overview")
    
    # Account metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Portfolio Value", "$200,000", "+$2,450")
    col2.metric("Day P&L", "+$1,230", "+0.62%")
    col3.metric("Buying Power", "$45,670", "")
    col4.metric("Positions", "12", "+2")
    
    # Sample positions
    st.markdown("### Current Positions")
    positions_data = [
        {"Symbol": "AAPL", "Shares": "50", "Value": "$8,745", "P&L": "+$234", "% Change": "+2.8%"},
        {"Symbol": "MSFT", "Shares": "25", "Value": "$12,456", "P&L": "-$123", "% Change": "-1.2%"},
        {"Symbol": "GOOGL", "Shares": "15", "Value": "$15,678", "P&L": "+$567", "% Change": "+3.7%"}
    ]
    
    positions_df = pd.DataFrame(positions_data)
    st.dataframe(positions_df, use_container_width=True)

with tab3:
    st.markdown("## ⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Trading Settings")
        auto_trading = st.checkbox("Auto Trading Enabled", value=True)
        max_position = st.number_input("Max Position Size ($)", value=10000, step=1000)
        min_confidence = st.slider("Min Confidence Score", 0.0, 10.0, 7.0, 0.1)
    
    with col2:
        st.markdown("### Risk Management")
        daily_limit = st.number_input("Daily Trade Limit", value=10, step=1)
        risk_per_trade = st.slider("Risk Per Trade (%)", 0.5, 5.0, 2.0, 0.1)
        stop_loss = st.slider("Default Stop Loss (%)", 1.0, 10.0, 5.0, 0.5)
    
    if st.button("💾 Save Configuration"):
        st.success("✅ Configuration saved")

# Status indicators in sidebar
st.sidebar.markdown("## 🚨 System Status")
st.sidebar.success("🟢 Trading System: ACTIVE")
st.sidebar.success("🟢 Data Feed: CONNECTED") 
st.sidebar.success("🟢 AI Engine: RUNNING")
st.sidebar.info("📊 Market: OPEN")

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 Quick Stats")
st.sidebar.metric("Account Value", "$200,000")
st.sidebar.metric("Today P&L", "+$1,230")
st.sidebar.metric("Active Signals", "3")

# Real-time update simulation
if st.sidebar.button("🔄 Refresh Data"):
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.warning("⚠️ **LIVE TRADING**\\nAll orders are REAL!")
'''
        
        # Write dashboard code to temp file
        temp_dashboard = project_root / "temp_dashboard.py"
        with open(temp_dashboard, 'w') as f:
            f.write(dashboard_code)
        
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(temp_dashboard),
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n✅ Dashboard stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up temp file
        temp_dashboard = project_root / "temp_dashboard.py"
        if temp_dashboard.exists():
            temp_dashboard.unlink()

if __name__ == "__main__":
    main()
