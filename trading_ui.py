"""
Interactive Trading UI for Signal Flow
Complete trading control panel with real-time monitoring and execution
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import time

# Set page config
st.set_page_config(
    page_title="Signal Flow Trading Control",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
    }
    .signal-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
    }
    .bullish {
        border-left: 4px solid #51cf66;
    }
    .bearish {
        border-left: 4px solid #ff6b6b;
    }
    .neutral {
        border-left: 4px solid #868e96;
    }
</style>
""", unsafe_allow_html=True)


class TradingUI:
    """Interactive trading UI controller."""
    
    def __init__(self):
        self.db_path = Path("logs/performance.db")
        
    def load_recent_signals(self, limit: int = 10) -> pd.DataFrame:
        """Load recent trading signals."""
        if not self.db_path.exists():
            return pd.DataFrame()
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, ticker, signal_type, confidence, market_regime,
                       rsi_zscore, momentum_divergence, volume_trend,
                       position_size, kelly_fraction, executed
                FROM signals 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            return pd.read_sql_query(query, conn, params=[limit])
    
    def load_active_positions(self) -> pd.DataFrame:
        """Load currently active positions."""
        # This would integrate with your broker API
        # For now, return mock data
        mock_positions = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'quantity': [100, 75, 50],
            'entry_price': [150.25, 280.50, 2500.75],
            'current_price': [152.10, 275.20, 2485.30],
            'pnl': [185.00, -397.50, -772.50],
            'pnl_percent': [1.23, -1.42, -0.62],
            'market_regime': ['trending_low_vol', 'mean_reverting_high_vol', 'uncertain']
        })
        return mock_positions
    
    def get_current_market_regime(self) -> dict:
        """Get current market regime information."""
        # This would integrate with your regime detector
        return {
            'regime': 'trending_low_vol',
            'confidence': 0.78,
            'volatility_percentile': 25,
            'trend_strength': 0.65
        }


def main():
    """Main trading UI application."""
    ui = TradingUI()
    
    # Header
    st.title("🎯 Signal Flow Trading Control Panel")
    st.markdown("---")
    
    # Sidebar - Trading Controls
    st.sidebar.header("🎛️ Trading Controls")
    
    # Trading mode selection
    trading_mode = st.sidebar.selectbox(
        "Trading Mode",
        ["Paper Trading", "Live Trading", "Signal Only"],
        index=0
    )
    
    # Auto-execution toggle
    auto_execute = st.sidebar.toggle("Auto Execute Trades", value=False)
    
    # Risk controls
    st.sidebar.subheader("Risk Controls")
    max_portfolio_risk = st.sidebar.slider("Max Portfolio Risk %", 1, 10, 3)
    max_position_size = st.sidebar.slider("Max Position Size %", 5, 25, 15)
    
    # Regime thresholds
    st.sidebar.subheader("Regime Thresholds")
    trending_threshold = st.sidebar.slider("Trending Market Confidence", 6.0, 10.0, 7.5)
    mean_reverting_threshold = st.sidebar.slider("Mean Reverting Confidence", 7.0, 10.0, 8.0)
    
    # Main content area
    col1, col2, col3, col4 = st.columns(4)
    
    # Current market regime
    regime_info = ui.get_current_market_regime()
    
    with col1:
        st.metric(
            "Market Regime",
            regime_info['regime'].replace('_', ' ').title(),
            f"{regime_info['confidence']:.1%} confidence"
        )
    
    with col2:
        st.metric(
            "Volatility Percentile",
            f"{regime_info['volatility_percentile']}%",
            "Current vs 90-day history"
        )
    
    with col3:
        st.metric(
            "Trend Strength",
            f"{regime_info['trend_strength']:.2f}",
            "0.0 = Mean Reverting, 1.0 = Trending"
        )
    
    with col4:
        # Get portfolio value
        positions_df = ui.load_active_positions()
        total_pnl = positions_df['pnl'].sum() if not positions_df.empty else 0
        st.metric(
            "Portfolio P&L",
            f"${total_pnl:,.2f}",
            f"{(total_pnl/100000)*100:+.2f}%" if total_pnl else "0%"
        )
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Live Signals", "📊 Active Positions", "📈 Performance", "⚙️ Settings"])
    
    with tab1:
        st.subheader("🎯 Recent Trading Signals")
        
        # Load recent signals
        signals_df = ui.load_recent_signals(20)
        
        if not signals_df.empty:
            # Signal execution buttons
            col_left, col_right = st.columns([3, 1])
            
            with col_left:
                st.subheader("Pending Signals")
                
                # Filter unexecuted signals
                pending_signals = signals_df[signals_df['executed'] == False].head(5)
                
                for idx, signal in pending_signals.iterrows():
                    # Signal card styling based on type
                    card_class = "bullish" if signal['signal_type'] == 'bullish' else "bearish" if signal['signal_type'] == 'bearish' else "neutral"
                    
                    with st.container():
                        signal_col1, signal_col2, signal_col3 = st.columns([2, 2, 1])
                        
                        with signal_col1:
                            st.markdown(f"""
                            <div class="signal-card {card_class}">
                                <h4>{signal['ticker']} - {signal['signal_type'].title()}</h4>
                                <p><strong>Confidence:</strong> {signal['confidence']:.1f}/10</p>
                                <p><strong>Regime:</strong> {signal['market_regime'].replace('_', ' ').title()}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with signal_col2:
                            st.write(f"**RSI Z-Score:** {signal['rsi_zscore']:.2f}")
                            st.write(f"**Momentum:** {signal['momentum_divergence']}")
                            st.write(f"**Volume:** {signal['volume_trend']}")
                            st.write(f"**Position Size:** ${signal['position_size']:,.0f}")
                        
                        with signal_col3:
                            if trading_mode != "Signal Only":
                                if st.button(f"✅ Execute", key=f"exec_{idx}"):
                                    st.success(f"Executing trade for {signal['ticker']}")
                                    # Here you would integrate with trade execution
                                
                                if st.button(f"❌ Reject", key=f"reject_{idx}"):
                                    st.warning(f"Rejecting signal for {signal['ticker']}")
                        
                        st.markdown("---")
            
            with col_right:
                st.subheader("Signal Summary")
                
                # Signal type distribution
                signal_counts = signals_df['signal_type'].value_counts()
                fig_pie = go.Figure(data=[go.Pie(
                    labels=signal_counts.index,
                    values=signal_counts.values,
                    hole=0.4
                )])
                fig_pie.update_layout(
                    title="Signal Distribution (Last 20)",
                    height=300
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Execution rate
                execution_rate = (signals_df['executed'].sum() / len(signals_df)) * 100
                st.metric("Execution Rate", f"{execution_rate:.1f}%")
        else:
            st.info("No recent signals found. Signals will appear here as they are generated.")
    
    with tab2:
        st.subheader("📊 Active Positions")
        
        positions_df = ui.load_active_positions()
        
        if not positions_df.empty:
            # Position overview
            for idx, position in positions_df.iterrows():
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        position['ticker'],
                        f"{position['quantity']} shares",
                        f"${position['current_price']:.2f}"
                    )
                
                with col2:
                    st.metric(
                        "Entry Price",
                        f"${position['entry_price']:.2f}",
                        f"{position['pnl_percent']:+.2f}%"
                    )
                
                with col3:
                    st.metric(
                        "P&L",
                        f"${position['pnl']:+,.2f}",
                        "Unrealized"
                    )
                
                with col4:
                    st.metric(
                        "Market Regime",
                        position['market_regime'].replace('_', ' ').title(),
                        "Current"
                    )
                
                # Position actions
                action_col1, action_col2, action_col3 = st.columns(3)
                with action_col1:
                    if st.button(f"Close {position['ticker']}", key=f"close_{idx}"):
                        st.warning(f"Closing position in {position['ticker']}")
                
                with action_col2:
                    if st.button(f"Set Stop Loss", key=f"stop_{idx}"):
                        st.info(f"Setting stop loss for {position['ticker']}")
                
                with action_col3:
                    if st.button(f"Adjust Size", key=f"adjust_{idx}"):
                        st.info(f"Adjusting position size for {position['ticker']}")
                
                st.markdown("---")
        else:
            st.info("No active positions.")
    
    with tab3:
        st.subheader("📈 Performance Analytics")
        
        # Load performance data
        if ui.db_path.exists():
            with sqlite3.connect(ui.db_path) as conn:
                daily_perf = pd.read_sql_query(
                    "SELECT * FROM daily_performance ORDER BY date DESC LIMIT 30",
                    conn
                )
                
                if not daily_perf.empty:
                    # Performance metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_trades = daily_perf['total_trades'].sum()
                        st.metric("Total Trades", total_trades)
                    
                    with col2:
                        avg_win_rate = daily_perf['win_rate'].mean() * 100
                        st.metric("Win Rate", f"{avg_win_rate:.1f}%")
                    
                    with col3:
                        total_pnl = daily_perf['total_pnl'].sum()
                        st.metric("Total P&L", f"${total_pnl:,.2f}")
                    
                    with col4:
                        avg_profit_factor = daily_perf['profit_factor'].mean()
                        st.metric("Profit Factor", f"{avg_profit_factor:.2f}")
                    
                    # Performance chart
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=daily_perf['date'],
                        y=daily_perf['total_pnl'].cumsum(),
                        mode='lines',
                        name='Cumulative P&L',
                        line=dict(color='blue', width=2)
                    ))
                    
                    fig.update_layout(
                        title="Cumulative P&L Over Time",
                        xaxis_title="Date",
                        yaxis_title="Cumulative P&L ($)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No performance data available yet.")
        else:
            st.info("No performance database found. Start trading to see analytics.")
    
    with tab4:
        st.subheader("⚙️ System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Indicator Settings")
            
            # RSI Z-Score settings
            rsi_threshold = st.slider("RSI Z-Score Threshold", 1.0, 3.0, 1.5)
            
            # Momentum divergence sensitivity
            momentum_sensitivity = st.slider("Momentum Sensitivity", 0.1, 1.0, 0.5)
            
            # Volume confirmation required
            volume_confirmation = st.checkbox("Require Volume Confirmation", value=True)
            
            # Sector relative strength
            sector_weight = st.slider("Sector Strength Weight", 0.0, 2.0, 1.0)
        
        with col2:
            st.subheader("Risk Management")
            
            # Kelly Criterion settings
            kelly_max = st.slider("Max Kelly Fraction", 0.1, 0.5, 0.25)
            
            # Volatility scaling
            vol_scaling = st.checkbox("Enable Volatility Scaling", value=True)
            
            # Correlation adjustment
            correlation_limit = st.slider("Max Correlation", 0.3, 0.8, 0.6)
            
            # Portfolio heat map
            max_portfolio_vol = st.slider("Max Portfolio Volatility", 0.1, 0.3, 0.15)
        
        # Save settings button
        if st.button("💾 Save Settings", type="primary"):
            # Here you would save settings to configuration
            st.success("Settings saved successfully!")
    
    # Auto-refresh functionality
    if st.sidebar.button("🔄 Refresh Data"):
        st.experimental_rerun()
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=False)
    
    if auto_refresh:
        time.sleep(30)
        st.experimental_rerun()


if __name__ == "__main__":
    main()
