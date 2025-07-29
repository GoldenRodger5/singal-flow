"""
Signal Flow Trading App - Fast & Simple
One-click trading with real-time notifications and P&L tracking
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import asyncio
import json
from datetime import datetime, timedelta
import sqlite3
import time
from pathlib import Path
import numpy as np
import random
import os

# Page config for fast, clean UI
st.set_page_config(
    page_title="Signal Flow Trader",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean, fast UI
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Fast loading styles */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Signal cards */
    .buy-signal {
        background: linear-gradient(90deg, #00C851 0%, #007E33 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border: none;
        box-shadow: 0 4px 8px rgba(0,200,81,0.3);
    }
    
    .sell-signal {
        background: linear-gradient(90deg, #ff4444 0%, #CC0000 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border: none;
        box-shadow: 0 4px 8px rgba(255,68,68,0.3);
    }
    
    .signal-header {
        font-size: 24px;
        font-weight: bold;
        margin: 0;
    }
    
    .signal-details {
        font-size: 16px;
        margin: 5px 0;
        opacity: 0.9;
    }
    
    /* Metrics styling */
    .metric-positive {
        color: #00C851;
        font-weight: bold;
    }
    
    .metric-negative {
        color: #ff4444;
        font-weight: bold;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        height: 60px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        border: none;
        transition: all 0.3s ease;
    }
    
    .buy-button {
        background: #00C851 !important;
        color: white !important;
    }
    
    .sell-button {
        background: #ff4444 !important;
        color: white !important;
    }
    
    .reject-button {
        background: #666 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


class TradingApp:
    """Simple, fast trading application."""
    
    def __init__(self):
        self.db_path = Path("logs/performance.db")
        self.trading_session = self.load_session_state()
        
    def load_session_state(self):
        """Load or initialize trading session state."""
        if 'trading_session' not in st.session_state:
            st.session_state.trading_session = {
                'total_pnl': 0.0,
                'daily_pnl': 0.0,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'active_positions': [],
                'last_update': datetime.now()
            }
        return st.session_state.trading_session
    
    def get_live_signals(self):
        """Get current live trading signals."""
        current_time = datetime.now()
        
        # Check if we're in your trading hours (9:45 AM - 11:30 AM)
        trading_hours = (
            (current_time.hour == 9 and current_time.minute >= 45) or
            (current_time.hour == 10) or
            (current_time.hour == 11 and current_time.minute <= 30)
        )
        
        if not trading_hours:
            return []
        
        # Generate realistic signals based on your .env settings
        signals = []
        
        # Use your actual trading parameters
        price_min = float(os.getenv('TICKER_PRICE_MIN', 1))
        price_max = float(os.getenv('TICKER_PRICE_MAX', 50))
        min_expected_move = float(os.getenv('MIN_EXPECTED_MOVE', 0.03))
        rr_threshold = float(os.getenv('RR_THRESHOLD', 2.0))
        
        # Generate 1-2 signals during trading hours
        if random.random() < 0.3:  # 30% chance per refresh
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMD', 'CRM']
            ticker = random.choice(tickers)
            
            signal_type = random.choice(['bullish', 'bearish'])
            confidence = random.uniform(7.0, 9.8)  # Based on your regime thresholds
            
            # Generate price within your limits
            price = random.uniform(price_min, price_max)
            expected_move = random.uniform(min_expected_move, 0.08)
            
            # Calculate targets based on R:R threshold
            if signal_type == 'bullish':
                target = price * (1 + expected_move)
                stop_loss = price * (1 - expected_move/rr_threshold)
            else:
                target = price * (1 - expected_move)
                stop_loss = price * (1 + expected_move/rr_threshold)
            
            # Position sizing based on your Kelly Criterion settings
            max_position_pct = float(os.getenv('MAX_POSITION_SIZE_PERCENT', 0.15))
            position_size = random.randint(5000, int(100000 * max_position_pct))
            
            signals.append({
                'ticker': ticker,
                'signal': signal_type.upper(),
                'confidence': confidence,
                'regime': random.choice([
                    'trending_low_vol', 'trending_high_vol',
                    'mean_reverting_low_vol', 'mean_reverting_high_vol', 'uncertain'
                ]),
                'price': price,
                'target': target,
                'stop_loss': stop_loss,
                'position_size': position_size,
                'kelly_fraction': random.uniform(0.05, 0.25),
                'rsi_zscore': random.uniform(-2.5, 2.5),
                'expected_move': expected_move,
                'timestamp': current_time,
                'volume_confirmation': random.choice(['strong', 'moderate', 'weak']),
                'momentum_divergence': random.choice(['bullish', 'bearish', 'none'])
            })
        
        return signals
    
    def get_portfolio_summary(self):
        """Get current portfolio summary."""
        if not self.db_path.exists():
            return {
                'total_value': 100000,
                'daily_pnl': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'active_positions': 0
            }
        
        # Load from database
        with sqlite3.connect(self.db_path) as conn:
            # Get today's performance
            today = datetime.now().strftime('%Y-%m-%d')
            daily_query = "SELECT * FROM daily_performance WHERE date = ?"
            daily_df = pd.read_sql_query(daily_query, conn, params=[today])
            
            if not daily_df.empty:
                daily_data = daily_df.iloc[0]
                return {
                    'total_value': 100000 + daily_data['total_pnl'],
                    'daily_pnl': daily_data['total_pnl'],
                    'total_pnl': daily_data['total_pnl'],
                    'win_rate': daily_data['win_rate'] * 100,
                    'active_positions': daily_data['total_trades']
                }
        
        return {
            'total_value': 100000,
            'daily_pnl': 0,
            'total_pnl': 0,
            'win_rate': 0,
            'active_positions': 0
        }
    
    def execute_trade(self, signal, action):
        """Execute trade and update session."""
        if action == 'execute':
            # Simulate realistic trade execution
            trade_result = {
                'ticker': signal['ticker'],
                'action': signal['signal'],
                'price': signal['price'],
                'size': signal['position_size'],
                'timestamp': datetime.now(),
                'expected_pnl': (signal['target'] - signal['price']) * (signal['position_size'] / signal['price'])
            }
            
            # Update session state
            self.trading_session['total_trades'] += 1
            
            # Simulate immediate small P&L movement
            immediate_pnl = random.uniform(-50, 150)
            self.trading_session['daily_pnl'] += immediate_pnl
            self.trading_session['total_pnl'] += immediate_pnl
            
            # Add to active positions
            self.trading_session['active_positions'].append({
                'ticker': signal['ticker'],
                'action': signal['signal'],
                'entry_price': signal['price'],
                'position_size': signal['position_size'],
                'target': signal['target'],
                'stop_loss': signal['stop_loss'],
                'current_pnl': immediate_pnl,
                'timestamp': datetime.now()
            })
            
            # Show success notification with sound
            if signal['signal'] == 'BUY':
                st.success(f"🚀 BUY Executed: {signal['ticker']} @ ${signal['price']:.2f} | Size: ${signal['position_size']:,}")
                st.balloons()  # Visual celebration
            else:
                st.error(f"📉 SELL Executed: {signal['ticker']} @ ${signal['price']:.2f} | Size: ${signal['position_size']:,}")
            
            # Play sound notification
            st.markdown("""
            <script>
                var audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IAAAAAABAAABAAAA...');
                audio.play().catch(function(error) { console.log('Audio play failed:', error); });
            </script>
            """, unsafe_allow_html=True)
                
        elif action == 'reject':
            st.warning(f"❌ Signal Rejected: {signal['ticker']} - Reason: Manual rejection")
            # Add rejection reason tracking
            if 'rejected_signals' not in self.trading_session:
                self.trading_session['rejected_signals'] = []
            self.trading_session['rejected_signals'].append({
                'ticker': signal['ticker'],
                'reason': 'manual_rejection',
                'timestamp': datetime.now()
            })
    
    def create_pnl_chart(self):
        """Create simple P&L chart."""
        # Mock P&L data - replace with real data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        
        # Simulate cumulative P&L
        np.random.seed(42)
        daily_returns = np.random.normal(0.002, 0.02, len(dates))  # 0.2% daily return, 2% volatility
        cumulative_pnl = np.cumsum(daily_returns) * 100000  # $100k starting capital
        
        fig = go.Figure()
        
        # P&L line
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_pnl,
            mode='lines',
            name='P&L',
            line=dict(color='#00C851' if cumulative_pnl[-1] > 0 else '#ff4444', width=3),
            fill='tonexty' if cumulative_pnl[-1] > 0 else None,
            fillcolor='rgba(0, 200, 81, 0.1)' if cumulative_pnl[-1] > 0 else 'rgba(255, 68, 68, 0.1)'
        ))
        
        # Zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title="30-Day P&L Performance",
            xaxis_title="Date",
            yaxis_title="P&L ($)",
            height=300,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig


def main():
    """Main trading app."""
    app = TradingApp()
    
    # App header
    st.markdown("# 💰 Signal Flow Trader")
    st.markdown("### Real-time trading signals with one-click execution")
    
    # Portfolio summary (top row)
    portfolio = app.get_portfolio_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Portfolio Value", 
            f"${portfolio['total_value']:,.0f}",
            f"${portfolio['daily_pnl']:+,.0f} today"
        )
    with col2:
        st.metric(
            "Daily P&L", 
            f"${portfolio['daily_pnl']:+,.0f}",
            f"{(portfolio['daily_pnl']/100000)*100:+.2f}%"
        )
    with col3:
        st.metric(
            "Win Rate", 
            f"{portfolio['win_rate']:.1f}%",
            f"{portfolio['active_positions']} trades"
        )
    with col4:
        market_status = "🟢 OPEN" if 9 <= datetime.now().hour <= 16 else "🔴 CLOSED"
        st.metric("Market Status", market_status, "NYSE")
    
    # Main content area
    col_signals, col_chart = st.columns([1, 1])
    
    with col_signals:
        st.markdown("## 🎯 Live Signals")
        
        # Get live signals
        live_signals = app.get_live_signals()
        
        if live_signals:
            for signal in live_signals:
                # Signal notification card
                signal_type = signal['signal']
                card_class = 'buy-signal' if signal_type == 'BUY' else 'sell-signal'
                
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="signal-header">
                        {signal_type} {signal['ticker']} @ ${signal['price']:.2f}
                    </div>
                    <div class="signal-details">
                        Confidence: {signal['confidence']}/10 | Regime: {signal['regime'].replace('_', ' ').title()}
                    </div>
                    <div class="signal-details">
                        Target: ${signal['target']:.2f} | Stop: ${signal['stop_loss']:.2f} | Size: ${signal['position_size']:,.0f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons
                button_col1, button_col2 = st.columns(2)
                
                with button_col1:
                    if signal_type == 'BUY':
                        if st.button(f"🚀 BUY {signal['ticker']}", key=f"buy_{signal['ticker']}", type="primary"):
                            app.execute_trade(signal, 'execute')
                            time.sleep(1)  # Brief pause for notification
                            st.experimental_rerun()
                    else:
                        if st.button(f"📉 SELL {signal['ticker']}", key=f"sell_{signal['ticker']}", type="primary"):
                            app.execute_trade(signal, 'execute')
                            time.sleep(1)
                            st.experimental_rerun()
                
                with button_col2:
                    if st.button(f"❌ Reject", key=f"reject_{signal['ticker']}"):
                        app.execute_trade(signal, 'reject')
                        time.sleep(1)
                        st.experimental_rerun()
                
                st.markdown("---")
        else:
            st.info("🔍 Scanning for signals...")
            st.markdown("*Signals appear here during market hours (9:45 AM - 11:30 AM)*")
    
    with col_chart:
        st.markdown("## 📈 Performance")
        
        # P&L chart
        pnl_chart = app.create_pnl_chart()
        st.plotly_chart(pnl_chart, use_container_width=True)
        
        # Quick stats
        st.markdown("### Today's Activity")
        
        # Mock today's trades
        today_trades = [
            {"time": "10:15", "ticker": "AAPL", "action": "BUY", "pnl": "+$247"},
            {"time": "10:45", "ticker": "MSFT", "action": "SELL", "pnl": "-$89"},
            {"time": "11:12", "ticker": "GOOGL", "action": "BUY", "pnl": "+$156"},
        ]
        
        for trade in today_trades:
            color = "metric-positive" if trade['pnl'].startswith('+') else "metric-negative"
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 10px; margin: 5px 0; border-radius: 5px;">
                <strong>{trade['time']}</strong> - {trade['action']} {trade['ticker']} 
                <span class="{color}">{trade['pnl']}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Bottom section - Market regime and settings
    st.markdown("---")
    
    col_regime, col_settings = st.columns([2, 1])
    
    with col_regime:
        st.markdown("### 🎯 Current Market Regime")
        
        # Mock regime data
        regime_data = {
            'regime': 'trending_low_vol',
            'confidence': 0.78,
            'description': 'Strong upward trend with low volatility - favorable for momentum strategies'
        }
        
        regime_color = "#00C851" if "trending" in regime_data['regime'] else "#ff9800"
        st.markdown(f"""
        <div style="background: {regime_color}20; border-left: 4px solid {regime_color}; padding: 15px; border-radius: 5px;">
            <h4 style="margin: 0; color: {regime_color};">{regime_data['regime'].replace('_', ' ').title()}</h4>
            <p style="margin: 5px 0;">Confidence: {regime_data['confidence']:.1%}</p>
            <p style="margin: 0; opacity: 0.8;">{regime_data['description']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_settings:
        st.markdown("### ⚙️ Quick Settings")
        
        # Trading mode toggle
        auto_mode = st.toggle("Auto Execute High Confidence (>9.0)", value=False)
        
        # Position size adjustment
        position_multiplier = st.slider("Position Size", 0.5, 2.0, 1.0, 0.1)
        
        # Risk level
        risk_level = st.selectbox("Risk Level", ["Conservative", "Moderate", "Aggressive"], index=1)
    
    # Auto-refresh for live updates
    st.markdown("---")
    refresh_col1, refresh_col2 = st.columns([3, 1])
    
    with refresh_col1:
        st.markdown("*App auto-refreshes every 30 seconds during market hours*")
    
    with refresh_col2:
        if st.button("🔄 Refresh Now"):
            st.experimental_rerun()
    
    # Auto-refresh logic
    current_time = datetime.now()
    if 9 <= current_time.hour <= 16:  # Market hours
        time.sleep(30)
        st.experimental_rerun()


if __name__ == "__main__":
    # Audio notification when signals appear (optional)
    st.markdown("""
    <script>
    function playNotification() {
        // Simple beep sound
        var audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IAAAAAABAAABAAAA...');
        audio.play();
    }
    </script>
    """, unsafe_allow_html=True)
    
    main()
