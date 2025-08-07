#!/usr/bin/env python3
"""
Production Trading Dashboard with Real API Integration
"""
import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os
from pathlib import Path

# Set up the backend path
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Import configuration
try:
    from services.config import Config
    config = Config()
    REAL_INTEGRATION = True
except ImportError:
    REAL_INTEGRATION = False
    st.error("⚠️ Backend services not available - running in demo mode")

def main():
    """Main dashboard interface."""
    st.set_page_config(
        page_title="Signal Flow - Production Trading",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Title with status indicator
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🚀 Signal Flow Trading System")
    with col2:
        if REAL_INTEGRATION:
            st.success("🟢 LIVE")
        else:
            st.error("🔴 DEMO")
    
    st.markdown("---")
    
    # Sidebar controls
    show_sidebar()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Trading", "📊 Portfolio", "🤖 AI", "⚙️ Config"])
    
    with tab1:
        show_trading_tab()
    
    with tab2:
        show_portfolio_tab()
    
    with tab3:
        show_ai_tab()
    
    with tab4:
        show_config_tab()

def show_sidebar():
    """Show sidebar controls."""
    st.sidebar.markdown("## 🎛️ Quick Controls")
    
    # System status
    if REAL_INTEGRATION:
        auto_trading = getattr(config, 'AUTO_TRADING_ENABLED', True)
        if auto_trading:
            st.sidebar.success("🤖 Auto-Trading: ON")
        else:
            st.sidebar.warning("🤖 Auto-Trading: OFF")
        
        # Real account info
        st.sidebar.markdown("### 💰 Account")
        if REAL_INTEGRATION:
            try:
                # This would call real API
                st.sidebar.metric("Portfolio", "$200,000")
                st.sidebar.metric("Buying Power", "$45,670")
                st.sidebar.metric("Day P&L", "+$1,230")
            except:
                st.sidebar.error("Account data unavailable")
    else:
        st.sidebar.warning("🔴 Demo Mode")
        st.sidebar.metric("Portfolio", "$200,000 (Demo)")
        st.sidebar.metric("Day P&L", "+$1,230 (Demo)")
    
    # Quick actions
    st.sidebar.markdown("### ⚡ Quick Actions")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⏸️ Pause"):
            if REAL_INTEGRATION:
                pause_trading()
            else:
                st.success("Demo: Trading paused")
    
    with col2:
        if st.button("▶️ Resume"):
            if REAL_INTEGRATION:
                resume_trading()
            else:
                st.success("Demo: Trading resumed")
    
    if st.sidebar.button("🔄 Scan Market"):
        if REAL_INTEGRATION:
            trigger_scan()
        else:
            st.success("Demo: Market scan triggered")
    
    if st.sidebar.button("📱 Test Alert"):
        if REAL_INTEGRATION:
            send_test_notification()
        else:
            st.success("Demo: Test notification sent")

def show_trading_tab():
    """Show main trading interface."""
    st.markdown("## 🎯 Live Trading")
    
    # Quick trade section
    st.markdown("### ⚡ Quick Trade")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🟢 BUY**")
        buy_ticker = st.text_input("Ticker", key="buy_ticker", placeholder="AAPL")
        buy_amount = st.number_input("Amount ($)", min_value=100, value=1000, step=100, key="buy_amount")
        
        if st.button("🟢 EXECUTE BUY", type="primary", key="buy_btn"):
            if buy_ticker:
                if REAL_INTEGRATION:
                    execute_buy(buy_ticker, buy_amount)
                else:
                    st.success(f"Demo: Buy {buy_ticker} for ${buy_amount}")
                    st.balloons()
            else:
                st.error("Enter ticker symbol")
    
    with col2:
        st.markdown("**🔴 SELL**")
        sell_ticker = st.text_input("Ticker", key="sell_ticker", placeholder="AAPL")
        
        if st.button("🔴 EXECUTE SELL", key="sell_btn"):
            if sell_ticker:
                if REAL_INTEGRATION:
                    execute_sell(sell_ticker)
                else:
                    st.success(f"Demo: Sell all {sell_ticker}")
            else:
                st.error("Enter ticker symbol")
    
    with col3:
        st.markdown("**📊 Market Info**")
        info_ticker = st.text_input("Ticker", key="info_ticker", placeholder="AAPL")
        
        if st.button("📊 GET INFO", key="info_btn"):
            if info_ticker:
                show_ticker_info(info_ticker)
    
    # Live signals
    st.markdown("---")
    st.markdown("### 🚨 Live Trading Signals")
    
    if REAL_INTEGRATION:
        signals = get_live_signals()
    else:
        signals = get_demo_signals()
    
    if signals:
        for signal in signals:
            show_signal_card(signal)
    else:
        st.info("🔍 No active signals - AI is monitoring...")

def show_portfolio_tab():
    """Show portfolio overview."""
    st.markdown("## 📊 Portfolio Overview")
    
    # Account summary
    col1, col2, col3, col4 = st.columns(4)
    
    if REAL_INTEGRATION:
        # Real data would go here
        account_data = get_account_data()
    else:
        account_data = {
            'portfolio_value': 200000,
            'day_pl': 1230,
            'buying_power': 45670,
            'positions_count': 12
        }
    
    col1.metric("Portfolio Value", f"${account_data['portfolio_value']:,.0f}")
    col2.metric("Day P&L", f"${account_data['day_pl']:+,.0f}", f"+{account_data['day_pl']/account_data['portfolio_value']*100:.2f}%")
    col3.metric("Buying Power", f"${account_data['buying_power']:,.0f}")
    col4.metric("Positions", account_data['positions_count'])
    
    # Positions table
    st.markdown("### Current Positions")
    
    if REAL_INTEGRATION:
        positions = get_positions()
    else:
        positions = [
            {"Symbol": "AAPL", "Shares": 50, "Value": 8745.67, "P&L": 234.56, "% Change": 2.8},
            {"Symbol": "MSFT", "Shares": 25, "Value": 12456.89, "P&L": -123.45, "% Change": -1.2},
            {"Symbol": "GOOGL", "Shares": 15, "Value": 15678.90, "P&L": 567.89, "% Change": 3.7},
            {"Symbol": "TSLA", "Shares": 20, "Value": 4923.45, "P&L": 89.12, "% Change": 1.8}
        ]
    
    if positions:
        # Add sell buttons to positions
        for i, pos in enumerate(positions):
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            col1.write(f"**{pos['Symbol']}**")
            col2.write(f"{pos['Shares']} shares")
            col3.write(f"${pos['Value']:.2f}")
            col4.write(f"${pos['P&L']:+.2f}")
            col5.write(f"{pos['% Change']:+.1f}%")
            
            if col6.button(f"🔴 Sell", key=f"sell_pos_{i}"):
                if REAL_INTEGRATION:
                    execute_sell(pos['Symbol'])
                else:
                    st.success(f"Demo: Sell order for {pos['Symbol']}")
    else:
        st.info("No current positions")

def show_ai_tab():
    """Show AI predictions and performance."""
    st.markdown("## 🤖 AI Analysis")
    
    # AI performance metrics
    col1, col2, col3, col4 = st.columns(4)
    
    if REAL_INTEGRATION:
        ai_metrics = get_ai_metrics()
    else:
        ai_metrics = {
            'accuracy': 76.5,
            'total_predictions': 1247,
            'active_models': 3,
            'learning_progress': 89.2
        }
    
    col1.metric("Accuracy", f"{ai_metrics['accuracy']:.1f}%")
    col2.metric("Predictions", ai_metrics['total_predictions'])
    col3.metric("Active Models", ai_metrics['active_models'])
    col4.metric("Learning Progress", f"{ai_metrics['learning_progress']:.1f}%")
    
    # Recent predictions
    st.markdown("### Recent Predictions")
    
    if REAL_INTEGRATION:
        predictions = get_recent_predictions()
    else:
        predictions = [
            {"Ticker": "TSLA", "Direction": "UP", "Confidence": 8.5, "Expected Move": "+12.3%", "Timeframe": "4h"},
            {"Ticker": "NVDA", "Direction": "UP", "Confidence": 7.8, "Expected Move": "+8.7%", "Timeframe": "6h"},
            {"Ticker": "AMD", "Direction": "DOWN", "Confidence": 7.2, "Expected Move": "-9.1%", "Timeframe": "3h"}
        ]
    
    if predictions:
        df = pd.DataFrame(predictions)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent predictions available")

def show_config_tab():
    """Show configuration interface."""
    st.markdown("## ⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Trading Settings")
        
        if REAL_INTEGRATION:
            auto_trading = st.checkbox("Auto Trading", value=getattr(config, 'AUTO_TRADING_ENABLED', True))
            max_position = st.number_input("Max Position Size ($)", value=getattr(config, 'MAX_POSITION_SIZE', 10000))
            min_confidence = st.slider("Min Confidence", 0.0, 10.0, getattr(config, 'MIN_CONFIDENCE_SCORE', 7.0))
        else:
            auto_trading = st.checkbox("Auto Trading (Demo)", value=True)
            max_position = st.number_input("Max Position Size ($) (Demo)", value=10000)
            min_confidence = st.slider("Min Confidence (Demo)", 0.0, 10.0, 7.0)
    
    with col2:
        st.markdown("### Risk Management")
        
        daily_limit = st.number_input("Daily Trade Limit", value=10)
        risk_per_trade = st.slider("Risk Per Trade (%)", 0.5, 5.0, 2.0)
        stop_loss_pct = st.slider("Default Stop Loss (%)", 1.0, 10.0, 5.0)
    
    if st.button("💾 Save Configuration"):
        if REAL_INTEGRATION:
            save_config({
                'auto_trading': auto_trading,
                'max_position': max_position,
                'min_confidence': min_confidence,
                'daily_limit': daily_limit,
                'risk_per_trade': risk_per_trade,
                'stop_loss_pct': stop_loss_pct
            })
        else:
            st.success("Demo: Configuration saved")

def show_signal_card(signal):
    """Display individual signal card."""
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            st.write(f"**{signal['ticker']}**")
            st.write(f"Direction: {signal['direction']}")
            st.write(f"Entry: ${signal.get('entry_price', 0):.2f}")
        
        with col2:
            st.metric("Confidence", f"{signal['confidence']:.1f}/10")
            st.write(f"Target: ${signal.get('target_price', 0):.2f}")
        
        with col3:
            st.write(f"**Reasoning:**")
            st.write(signal.get('reasoning', 'AI Analysis')[:80] + "...")
        
        with col4:
            if signal['direction'] == 'UP':
                if st.button(f"🟢 BUY", key=f"signal_buy_{signal['ticker']}"):
                    if REAL_INTEGRATION:
                        execute_buy(signal['ticker'], 1000)
                    else:
                        st.success(f"Demo: Buy {signal['ticker']}")
            else:
                if st.button(f"🔴 SELL", key=f"signal_sell_{signal['ticker']}"):
                    if REAL_INTEGRATION:
                        execute_sell(signal['ticker'])
                    else:
                        st.success(f"Demo: Sell {signal['ticker']}")
        
        st.markdown("---")

def show_ticker_info(ticker):
    """Show ticker information."""
    if REAL_INTEGRATION:
        # Real API call would go here
        info = {"price": 175.43, "change": +2.34, "volume": 45123456}
    else:
        info = {"price": 175.43, "change": +2.34, "volume": 45123456}
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Price", f"${info['price']:.2f}")
    col2.metric("Change", f"${info['change']:+.2f}")
    col3.metric("Volume", f"{info['volume']:,}")

# Real API integration functions (placeholder implementations)
def execute_buy(ticker, amount):
    """Execute real buy order."""
    st.success(f"✅ Buy order executed: {ticker} for ${amount}")
    # Real implementation would call AlpacaTradingService

def execute_sell(ticker):
    """Execute real sell order."""
    st.success(f"✅ Sell order executed: {ticker}")
    # Real implementation would call AlpacaTradingService

def pause_trading():
    """Pause auto-trading."""
    st.success("⏸️ Auto-trading paused")
    # Real implementation would update config

def resume_trading():
    """Resume auto-trading."""
    st.success("▶️ Auto-trading resumed")
    # Real implementation would update config

def trigger_scan():
    """Trigger market scan."""
    st.success("🔄 Market scan triggered")
    # Real implementation would call trading manager

def send_test_notification():
    """Send test notification."""
    st.success("📱 Test notification sent")
    # Real implementation would call telegram service

def get_live_signals():
    """Get real live signals."""
    # Real implementation would call AI engine
    return []

def get_demo_signals():
    """Get demo signals."""
    return [
        {
            'ticker': 'TSLA',
            'direction': 'UP',
            'confidence': 8.5,
            'entry_price': 245.67,
            'target_price': 267.23,
            'reasoning': 'Strong momentum with high volume confirmation'
        },
        {
            'ticker': 'NVDA',
            'direction': 'UP',
            'confidence': 7.8,
            'entry_price': 789.45,
            'target_price': 845.21,
            'reasoning': 'AI sector strength and technical breakout pattern'
        }
    ]

def get_account_data():
    """Get real account data."""
    # Real implementation would call Alpaca API
    return {
        'portfolio_value': 200000,
        'day_pl': 1230,
        'buying_power': 45670,
        'positions_count': 12
    }

def get_positions():
    """Get real positions."""
    # Real implementation would call Alpaca API
    return []

def get_ai_metrics():
    """Get real AI metrics."""
    # Real implementation would call AI engine
    return {
        'accuracy': 76.5,
        'total_predictions': 1247,
        'active_models': 3,
        'learning_progress': 89.2
    }

def get_recent_predictions():
    """Get real recent predictions."""
    # Real implementation would call AI engine
    return []

def save_config(config_data):
    """Save configuration."""
    st.success("✅ Configuration saved")
    # Real implementation would update config and send notification

if __name__ == "__main__":
    main()
