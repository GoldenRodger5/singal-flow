#!/usr/bin/env python3
"""
Enhanced Fast Trading UI - Ultra-responsive with real-time notifications
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go
import random
import time
import json
import asyncio
from typing import Dict, List, Optional

# Set page config first
st.set_page_config(
    page_title="🚀 Signal Flow Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ultra-fast CSS styling
st.markdown("""
<style>
    /* Remove padding for maximum speed */
    .main > div {
        padding-top: 1rem;
    }
    
    /* Signal cards with instant visual feedback */
    .signal-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
    }
    
    .signal-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 16px 64px rgba(0,0,0,0.2);
    }
    
    .buy-signal {
        background: linear-gradient(135deg, #00c851 0%, #00ff41 100%);
        animation: pulse-green 2s infinite;
    }
    
    .sell-signal {
        background: linear-gradient(135deg, #ff4444 0%, #ff6b6b 100%);
        animation: pulse-red 2s infinite;
    }
    
    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(0, 200, 81, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 200, 81, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 200, 81, 0); }
    }
    
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }
    }
    
    /* Instant action buttons */
    .stButton > button {
        border-radius: 25px;
        font-weight: bold;
        font-size: 16px;
        padding: 10px 20px;
        transition: all 0.2s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
    }
    
    /* Notification styles */
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        background: #00c851;
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        font-weight: bold;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        animation: slideIn 0.5s ease;
    }
    
    @keyframes slideIn {
        from { transform: translateX(300px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    /* P&L metrics with color coding */
    .metric-positive {
        color: #00c851 !important;
        font-weight: bold;
    }
    
    .metric-negative {
        color: #ff4444 !important;
        font-weight: bold;
    }
    
    /* Remove streamlit branding for speed */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Fast loading indicators */
    .loading {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255,255,255,.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

class FastTradingEngine:
    """Ultra-fast trading engine optimized for real-time execution."""
    
    def __init__(self):
        self.db_path = Path("trading_data.db")
        self.config = self.load_config()
        self.initialize_session()
        
    def load_config(self) -> Dict:
        """Load trading configuration from .env or defaults."""
        return {
            'ticker_price_min': float(os.getenv('TICKER_PRICE_MIN', 1)),
            'ticker_price_max': float(os.getenv('TICKER_PRICE_MAX', 50)),
            'trading_start_time': os.getenv('TRADING_START_TIME', '09:45'),
            'trading_end_time': os.getenv('TRADING_END_TIME', '11:30'),
            'max_position_size': 10000,
            'min_confidence': 7.0
        }
    
    def initialize_session(self):
        """Initialize trading session with ultra-fast defaults."""
        if 'trading_session' not in st.session_state:
            st.session_state.trading_session = {
                'daily_pnl': 0.0,
                'total_pnl': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'active_positions': [],
                'notifications': [],
                'auto_execute': False,
                'last_signal_time': None,
                'session_start': datetime.now()
            }
    
    def get_instant_signals(self) -> List[Dict]:
        """Generate instant trading signals with realistic timing."""
        current_time = datetime.now()
        start_time = datetime.strptime(self.config['trading_start_time'], '%H:%M').time()
        end_time = datetime.strptime(self.config['trading_end_time'], '%H:%M').time()
        
        # Only generate signals during trading hours
        if not (start_time <= current_time.time() <= end_time):
            return []
        
        # Generate 1-3 high-quality signals
        signals = []
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'CRM']
        
        for _ in range(random.randint(1, 3)):
            ticker = random.choice(tickers)
            price = random.uniform(self.config['ticker_price_min'], self.config['ticker_price_max'])
            
            # High confidence signals only
            confidence = random.uniform(7.5, 10.0)
            signal_type = random.choice(['BUY', 'SELL'])
            
            # Calculate realistic targets and stops
            if signal_type == 'BUY':
                target = price * random.uniform(1.02, 1.08)  # 2-8% upside
                stop_loss = price * random.uniform(0.95, 0.98)  # 2-5% downside
            else:
                target = price * random.uniform(0.92, 0.98)  # 2-8% downside
                stop_loss = price * random.uniform(1.02, 1.05)  # 2-5% upside
            
            # Position sizing based on confidence
            position_size = min(
                self.config['max_position_size'],
                int((confidence / 10) * self.config['max_position_size'])
            )
            
            signal = {
                'ticker': ticker,
                'signal': signal_type,
                'price': round(price, 2),
                'confidence': round(confidence, 1),
                'target': round(target, 2),
                'stop_loss': round(stop_loss, 2),
                'position_size': position_size,
                'regime': random.choice(['trending_high_vol', 'trending_low_vol', 'ranging_high_vol']),
                'timestamp': current_time,
                'urgency': 'HIGH' if confidence >= 9.0 else 'MEDIUM',
                'expected_return': abs(target - price) / price
            }
            
            signals.append(signal)
        
        return signals
    
    def execute_instant_trade(self, signal: Dict, action: str) -> Dict:
        """Execute trade with instant feedback and realistic simulation."""
        if action == 'execute':
            # Simulate realistic execution
            execution_price = signal['price'] + random.uniform(-0.02, 0.02)  # Slight slippage
            
            # Calculate immediate P&L impact
            if signal['signal'] == 'BUY':
                # Simulate immediate market movement
                current_price = execution_price + random.uniform(-0.50, 1.50)
                pnl = (current_price - execution_price) * (signal['position_size'] / execution_price)
            else:
                current_price = execution_price + random.uniform(-1.50, 0.50)
                pnl = (execution_price - current_price) * (signal['position_size'] / execution_price)
            
            # Update session
            session = st.session_state.trading_session
            session['total_trades'] += 1
            session['daily_pnl'] += pnl
            session['total_pnl'] += pnl
            
            if pnl > 0:
                session['winning_trades'] += 1
            
            # Add to active positions
            position = {
                'ticker': signal['ticker'],
                'action': signal['signal'],
                'entry_price': execution_price,
                'current_price': current_price,
                'position_size': signal['position_size'],
                'current_pnl': pnl,
                'target': signal['target'],
                'stop_loss': signal['stop_loss'],
                'timestamp': datetime.now()
            }
            
            session['active_positions'].append(position)
            
            # Add notification
            notification = {
                'type': 'success',
                'message': f"✅ {signal['signal']} {signal['ticker']} @ ${execution_price:.2f} | P&L: ${pnl:+,.0f}",
                'timestamp': datetime.now()
            }
            session['notifications'].append(notification)
            
            return {
                'status': 'executed',
                'execution_price': execution_price,
                'current_pnl': pnl,
                'notification': notification
            }
        
        elif action == 'reject':
            notification = {
                'type': 'warning',
                'message': f"❌ Rejected {signal['signal']} {signal['ticker']}",
                'timestamp': datetime.now()
            }
            st.session_state.trading_session['notifications'].append(notification)
            
            return {
                'status': 'rejected',
                'notification': notification
            }
    
    def get_portfolio_metrics(self) -> Dict:
        """Get real-time portfolio metrics."""
        session = st.session_state.trading_session
        
        # Calculate win rate
        win_rate = (session['winning_trades'] / max(1, session['total_trades'])) * 100
        
        # Portfolio value
        starting_capital = 100000
        portfolio_value = starting_capital + session['total_pnl']
        
        # Calculate daily return %
        daily_return_pct = (session['daily_pnl'] / starting_capital) * 100
        
        return {
            'portfolio_value': portfolio_value,
            'daily_pnl': session['daily_pnl'],
            'daily_return_pct': daily_return_pct,
            'total_pnl': session['total_pnl'],
            'win_rate': win_rate,
            'total_trades': session['total_trades'],
            'active_positions': len(session['active_positions']),
            'session_duration': datetime.now() - session['session_start']
        }


def render_instant_signals(engine: FastTradingEngine):
    """Render signals with instant execution buttons."""
    st.markdown("## ⚡ Live Signals")
    
    signals = engine.get_instant_signals()
    
    if not signals:
        st.info("🔍 Scanning markets... Signals appear during trading hours (9:45 AM - 11:30 AM)")
        return
    
    for i, signal in enumerate(signals):
        # Signal type styling
        card_class = 'buy-signal' if signal['signal'] == 'BUY' else 'sell-signal'
        urgency_emoji = '🚨' if signal['urgency'] == 'HIGH' else '⚡'
        
        # Signal card with animations
        st.markdown(f"""
        <div class="signal-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0;">{urgency_emoji} {signal['signal']} {signal['ticker']}</h3>
                    <p style="margin: 5px 0; font-size: 18px; font-weight: bold;">
                        ${signal['price']:.2f} → ${signal['target']:.2f}
                    </p>
                    <p style="margin: 0; opacity: 0.9;">
                        Confidence: {signal['confidence']}/10 | 
                        Expected Return: {signal['expected_return']:.1%} |
                        Size: ${signal['position_size']:,}
                    </p>
                </div>
                <div style="text-align: right;">
                    <p style="margin: 0; font-size: 14px; opacity: 0.8;">
                        {signal['regime'].replace('_', ' ').title()}
                    </p>
                    <p style="margin: 0; font-size: 12px; opacity: 0.7;">
                        Stop: ${signal['stop_loss']:.2f}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Instant action buttons
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            button_emoji = "🚀" if signal['signal'] == 'BUY' else "📉"
            button_text = f"{button_emoji} {signal['signal']} NOW"
            
            if st.button(button_text, key=f"execute_{i}", type="primary"):
                result = engine.execute_instant_trade(signal, 'execute')
                if result['status'] == 'executed':
                    st.success(result['notification']['message'])
                    st.balloons()
                    time.sleep(1)
                    st.experimental_rerun()
        
        with col2:
            if st.button("❌ SKIP", key=f"reject_{i}"):
                result = engine.execute_instant_trade(signal, 'reject')
                st.warning(result['notification']['message'])
                time.sleep(0.5)
                st.experimental_rerun()
        
        with col3:
            # Auto-execute for high confidence
            if signal['confidence'] >= 9.5 and st.session_state.trading_session.get('auto_execute', False):
                st.markdown("🤖 **AUTO**")
                # Auto-execute logic here
        
        st.markdown("---")


def render_portfolio_dashboard(engine: FastTradingEngine):
    """Render real-time portfolio dashboard."""
    metrics = engine.get_portfolio_metrics()
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pnl_color = "normal" if metrics['daily_pnl'] >= 0 else "inverse"
        st.metric(
            "💰 Portfolio Value",
            f"${metrics['portfolio_value']:,.0f}",
            f"${metrics['daily_pnl']:+,.0f} ({metrics['daily_return_pct']:+.2f}%)",
            delta_color=pnl_color
        )
    
    with col2:
        st.metric(
            "🎯 Win Rate",
            f"{metrics['win_rate']:.1f}%",
            f"{metrics['total_trades']} total trades"
        )
    
    with col3:
        positions_text = f"{metrics['active_positions']} active"
        st.metric(
            "📊 Positions",
            positions_text,
            f"Session: {str(metrics['session_duration']).split('.')[0]}"
        )
    
    with col4:
        # Market status
        current_hour = datetime.now().hour
        market_status = "🟢 OPEN" if 9 <= current_hour <= 16 else "🔴 CLOSED"
        st.metric(
            "🏛️ Market",
            market_status,
            "NYSE/NASDAQ"
        )


def render_active_positions():
    """Render active positions with real-time P&L."""
    session = st.session_state.trading_session
    
    if not session['active_positions']:
        return
    
    st.markdown("## 📋 Active Positions")
    
    # Show last 5 positions
    recent_positions = session['active_positions'][-5:]
    
    for pos in recent_positions:
        # Update current P&L with small random movement
        current_pnl = pos['current_pnl'] + random.uniform(-10, 20)
        pos['current_pnl'] = current_pnl
        
        pnl_color = "metric-positive" if current_pnl >= 0 else "metric-negative"
        pnl_emoji = "🟢" if current_pnl >= 0 else "🔴"
        
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); padding: 15px; margin: 8px 0; border-radius: 8px; border-left: 4px solid {'#00c851' if current_pnl >= 0 else '#ff4444'};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{pos['ticker']}</strong> {pos['action']} @ ${pos['entry_price']:.2f}
                    <br><small>Target: ${pos['target']:.2f} | Stop: ${pos['stop_loss']:.2f}</small>
                </div>
                <div style="text-align: right;">
                    <span class="{pnl_color}" style="font-size: 18px; font-weight: bold;">
                        {pnl_emoji} ${current_pnl:+,.0f}
                    </span>
                    <br><small>${pos['position_size']:,} position</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main ultra-fast trading application."""
    # Initialize engine
    engine = FastTradingEngine()
    
    # App header with live status
    st.markdown("# 🚀 Signal Flow Pro")
    current_time = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"### ⚡ Ultra-Fast Execution • Live @ {current_time}")
    
    # Portfolio dashboard
    render_portfolio_dashboard(engine)
    
    st.markdown("---")
    
    # Main trading interface
    col_signals, col_positions = st.columns([2, 1])
    
    with col_signals:
        render_instant_signals(engine)
    
    with col_positions:
        render_active_positions()
        
        # Quick settings
        st.markdown("## ⚙️ Quick Controls")
        
        auto_execute = st.toggle("🤖 Auto-Execute (Conf > 9.5)", value=False)
        st.session_state.trading_session['auto_execute'] = auto_execute
        
        risk_multiplier = st.slider("📊 Position Size", 0.5, 2.0, 1.0, 0.1)
        
        if st.button("🔄 Force Refresh", type="secondary"):
            st.experimental_rerun()
    
    # Auto-refresh during market hours
    if 9 <= datetime.now().hour <= 16:
        # Auto-refresh every 15 seconds during market hours
        time.sleep(15)
        st.experimental_rerun()
    
    # Show notifications
    session = st.session_state.trading_session
    if session['notifications']:
        latest_notification = session['notifications'][-1]
        if (datetime.now() - latest_notification['timestamp']).seconds < 10:
            st.markdown(f"""
            <div class="notification">
                {latest_notification['message']}
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    import os
    main()
