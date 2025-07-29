"""
Real-time Signal Notification System
Integrates with Signal Flow trading system for instant notifications
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Dict, List
import os

# For desktop notifications
try:
    import plyer
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False

# For web notifications in Streamlit
import streamlit as st


class SignalNotifier:
    """Real-time signal notification system."""
    
    def __init__(self):
        self.db_path = Path("logs/performance.db")
        self.last_check = datetime.now()
        self.notified_signals = set()
        
    async def check_for_new_signals(self) -> List[Dict]:
        """Check for new trading signals since last check."""
        if not self.db_path.exists():
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM signals 
                WHERE timestamp > ? AND executed = FALSE
                ORDER BY confidence DESC
            """
            
            import pandas as pd
            new_signals_df = pd.read_sql_query(
                query, conn, 
                params=[self.last_check.strftime('%Y-%m-%d %H:%M:%S')]
            )
            
            self.last_check = datetime.now()
            
            # Filter out already notified signals
            new_signals = []
            for _, signal in new_signals_df.iterrows():
                signal_id = f"{signal['ticker']}_{signal['timestamp']}"
                if signal_id not in self.notified_signals:
                    new_signals.append(signal.to_dict())
                    self.notified_signals.add(signal_id)
            
            return new_signals
    
    def send_desktop_notification(self, signal: Dict):
        """Send desktop notification for new signal."""
        if not NOTIFICATIONS_AVAILABLE:
            return
        
        signal_type = signal['signal_type'].upper()
        ticker = signal['ticker']
        confidence = signal['confidence']
        price = signal.get('current_price', 'N/A')
        
        title = f"🎯 {signal_type} Signal: {ticker}"
        message = f"Confidence: {confidence:.1f}/10\nPrice: ${price}\nClick to view in app"
        
        try:
            plyer.notification.notify(
                title=title,
                message=message,
                app_name="Signal Flow Trader",
                timeout=10,
                app_icon=None
            )
        except Exception as e:
            print(f"Notification error: {e}")
    
    def create_streamlit_notification(self, signal: Dict) -> str:
        """Create Streamlit notification HTML."""
        signal_type = signal['signal_type'].upper()
        ticker = signal['ticker']
        confidence = signal['confidence']
        regime = signal['market_regime'].replace('_', ' ').title()
        
        color = "#00C851" if signal_type == "BULLISH" else "#ff4444"
        
        return f"""
        <div style="
            position: fixed;
            top: 20px;
            right: 20px;
            background: {color};
            color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 9999;
            max-width: 300px;
            animation: slideIn 0.5s ease-out;
        ">
            <h3 style="margin: 0 0 10px 0;">🎯 {signal_type} SIGNAL</h3>
            <p style="margin: 5px 0; font-size: 18px; font-weight: bold;">{ticker}</p>
            <p style="margin: 5px 0;">Confidence: {confidence:.1f}/10</p>
            <p style="margin: 5px 0;">Regime: {regime}</p>
            <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">
                Auto-refresh in progress...
            </p>
        </div>
        
        <style>
        @keyframes slideIn {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        </style>
        """


class LiveSignalFeed:
    """Live signal feed integrated with your trading system."""
    
    def __init__(self):
        self.signals_cache = []
        self.last_signal_time = datetime.now()
        
    def get_mock_signal_during_hours(self) -> Dict:
        """Generate realistic signals during your trading hours (9:45-11:30)."""
        current_time = datetime.now()
        
        # Only generate signals during trading hours
        if not (current_time.hour == 9 and current_time.minute >= 45) and current_time.hour != 10 and not (current_time.hour == 11 and current_time.minute <= 30):
            return None
        
        # Don't generate signals too frequently
        if (current_time - self.last_signal_time).seconds < 300:  # 5 minutes minimum
            return None
        
        import random
        
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMZN']
        ticker = random.choice(tickers)
        
        # Generate realistic signal based on your parameters
        signal_type = random.choice(['bullish', 'bearish'])
        confidence = random.uniform(7.0, 9.5)  # Your min threshold is likely 7+
        
        # Mock price data
        base_price = random.uniform(50, 300)  # Within your TICKER_PRICE_MIN/MAX
        expected_move = random.uniform(0.03, 0.08)  # Your MIN_EXPECTED_MOVE is 0.03
        
        signal = {
            'ticker': ticker,
            'signal_type': signal_type,
            'confidence': confidence,
            'market_regime': random.choice([
                'trending_low_vol', 'trending_high_vol', 
                'mean_reverting_low_vol', 'mean_reverting_high_vol', 'uncertain'
            ]),
            'current_price': base_price,
            'target_price': base_price * (1 + expected_move) if signal_type == 'bullish' else base_price * (1 - expected_move),
            'stop_loss': base_price * (1 - expected_move/2) if signal_type == 'bullish' else base_price * (1 + expected_move/2),
            'position_size': random.randint(5000, 15000),  # Based on your position sizing
            'kelly_fraction': random.uniform(0.1, 0.25),
            'rsi_zscore': random.uniform(-2.5, 2.5),
            'momentum_divergence': random.choice(['bullish', 'bearish', 'none']),
            'volume_trend': random.choice(['strong', 'moderate', 'weak']),
            'timestamp': current_time,
            'executed': False
        }
        
        self.last_signal_time = current_time
        return signal
    
    def should_notify(self, signal: Dict) -> bool:
        """Determine if signal should trigger notification."""
        if not signal:
            return False
            
        # Notify for high confidence signals
        if signal['confidence'] >= 8.0:
            return True
            
        # Notify for signals in favorable regimes
        if 'trending' in signal['market_regime'] and signal['confidence'] >= 7.5:
            return True
            
        return False


# Integration functions for the main trading app
def integrate_with_trading_app():
    """Integration code for trading_app.py"""
    
    # Initialize notification system
    if 'notifier' not in st.session_state:
        st.session_state.notifier = SignalNotifier()
    
    if 'signal_feed' not in st.session_state:
        st.session_state.signal_feed = LiveSignalFeed()
    
    # Check for new signals
    new_signal = st.session_state.signal_feed.get_mock_signal_during_hours()
    
    if new_signal and st.session_state.signal_feed.should_notify(new_signal):
        # Add to session state for display
        if 'current_signals' not in st.session_state:
            st.session_state.current_signals = []
        
        # Add new signal (keep only last 3)
        st.session_state.current_signals.append(new_signal)
        st.session_state.current_signals = st.session_state.current_signals[-3:]
        
        # Send desktop notification
        st.session_state.notifier.send_desktop_notification(new_signal)
        
        # Show in-app notification
        notification_html = st.session_state.notifier.create_streamlit_notification(new_signal)
        st.markdown(notification_html, unsafe_allow_html=True)
        
        # Auto-refresh to show new signal
        time.sleep(2)
        st.experimental_rerun()
    
    # Return current signals for display
    return st.session_state.get('current_signals', [])
