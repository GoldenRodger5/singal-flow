"""
Real-time Performance Dashboard
Live monitoring of regime-aware trading performance
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import json


class PerformanceDashboard:
    """Interactive dashboard for trading performance monitoring."""
    
    def __init__(self, db_path: str = "logs/performance.db"):
        self.db_path = Path(db_path)
        
    def load_data(self) -> tuple:
        """Load performance data from database."""
        if not self.db_path.exists():
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        with sqlite3.connect(self.db_path) as conn:
            signals = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC", conn)
            executions = pd.read_sql_query("SELECT * FROM executions ORDER BY timestamp DESC", conn)
            exits = pd.read_sql_query("SELECT * FROM exits ORDER BY timestamp DESC", conn)
            daily_perf = pd.read_sql_query("SELECT * FROM daily_performance ORDER BY date DESC", conn)
            
        return signals, executions, exits, daily_perf
    
    def create_regime_performance_chart(self, signals_df: pd.DataFrame, exits_df: pd.DataFrame):
        """Create regime performance comparison chart."""
        if signals_df.empty or exits_df.empty:
            return go.Figure()
        
        # Calculate win rates by regime
        regime_stats = []
        for regime in signals_df['market_regime'].unique():
            regime_signals = signals_df[signals_df['market_regime'] == regime]
            regime_exits = exits_df[exits_df['execution_id'].isin(
                signals_df[signals_df['market_regime'] == regime].index
            )]
            
            if len(regime_exits) > 0:
                win_rate = (regime_exits['win'].sum() / len(regime_exits)) * 100
                avg_pnl = regime_exits['pnl_usd'].mean()
                total_trades = len(regime_exits)
                
                regime_stats.append({
                    'regime': regime,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_trades': total_trades
                })
        
        if not regime_stats:
            return go.Figure()
        
        regime_df = pd.DataFrame(regime_stats)
        
        # Create subplot with secondary y-axis
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Win Rate by Regime', 'Average P&L by Regime'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Win rate chart
        fig.add_trace(
            go.Bar(
                x=regime_df['regime'],
                y=regime_df['win_rate'],
                name='Win Rate (%)',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
        
        # Average P&L chart
        colors = ['green' if x > 0 else 'red' for x in regime_df['avg_pnl']]
        fig.add_trace(
            go.Bar(
                x=regime_df['regime'],
                y=regime_df['avg_pnl'],
                name='Avg P&L ($)',
                marker_color=colors
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title="Performance by Market Regime",
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_pnl_curve(self, exits_df: pd.DataFrame):
        """Create cumulative P&L curve."""
        if exits_df.empty:
            return go.Figure()
        
        exits_df = exits_df.sort_values('timestamp')
        exits_df['cumulative_pnl'] = exits_df['pnl_usd'].cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=exits_df['timestamp'],
            y=exits_df['cumulative_pnl'],
            mode='lines',
            name='Cumulative P&L',
            line=dict(color='blue', width=2)
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        fig.update_layout(
            title="Cumulative P&L Over Time",
            xaxis_title="Date",
            yaxis_title="Cumulative P&L ($)",
            height=400
        )
        
        return fig
    
    def create_signal_distribution(self, signals_df: pd.DataFrame):
        """Create signal type distribution chart."""
        if signals_df.empty:
            return go.Figure()
        
        signal_counts = signals_df['signal_type'].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=signal_counts.index,
            values=signal_counts.values,
            hole=0.3
        )])
        
        fig.update_layout(
            title="Signal Type Distribution",
            height=400
        )
        
        return fig
    
    def create_daily_metrics_table(self, daily_perf_df: pd.DataFrame):
        """Create daily performance metrics table."""
        if daily_perf_df.empty:
            return pd.DataFrame()
        
        # Format the dataframe for display
        display_df = daily_perf_df.copy()
        
        # Format percentage columns
        if 'win_rate' in display_df.columns:
            display_df['win_rate'] = (display_df['win_rate'] * 100).round(1).astype(str) + '%'
        
        # Format currency columns
        currency_cols = ['total_pnl', 'avg_win', 'avg_loss', 'largest_win', 'largest_loss']
        for col in currency_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "$0.00")
        
        return display_df[['date', 'total_trades', 'win_rate', 'total_pnl', 'avg_win', 'avg_loss']].head(10)


def run_dashboard():
    """Main dashboard application."""
    st.set_page_config(
        page_title="Signal Flow Performance Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Signal Flow Trading Performance Dashboard")
    st.markdown("---")
    
    dashboard = PerformanceDashboard()
    signals_df, executions_df, exits_df, daily_perf_df = dashboard.load_data()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    if not exits_df.empty:
        min_date = pd.to_datetime(exits_df['timestamp']).min().date()
        max_date = pd.to_datetime(exits_df['timestamp']).max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(max_date - timedelta(days=30), max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            exits_df = exits_df[
                (pd.to_datetime(exits_df['timestamp']).dt.date >= start_date) &
                (pd.to_datetime(exits_df['timestamp']).dt.date <= end_date)
            ]
            signals_df = signals_df[
                (pd.to_datetime(signals_df['timestamp']).dt.date >= start_date) &
                (pd.to_datetime(signals_df['timestamp']).dt.date <= end_date)
            ]
    
    # Key metrics row
    if not exits_df.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_trades = len(exits_df)
        wins = exits_df['win'].sum()
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = exits_df['pnl_usd'].sum()
        avg_pnl = exits_df['pnl_usd'].mean()
        
        with col1:
            st.metric("Total Trades", total_trades)
        
        with col2:
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
        with col3:
            st.metric("Total P&L", f"${total_pnl:.2f}")
        
        with col4:
            st.metric("Avg P&L", f"${avg_pnl:.2f}")
        
        with col5:
            if not daily_perf_df.empty and 'profit_factor' in daily_perf_df.columns:
                profit_factor = daily_perf_df['profit_factor'].mean()
                st.metric("Profit Factor", f"{profit_factor:.2f}")
            else:
                st.metric("Profit Factor", "N/A")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        regime_chart = dashboard.create_regime_performance_chart(signals_df, exits_df)
        st.plotly_chart(regime_chart, use_container_width=True)
    
    with col2:
        signal_dist_chart = dashboard.create_signal_distribution(signals_df)
        st.plotly_chart(signal_dist_chart, use_container_width=True)
    
    # P&L curve (full width)
    pnl_chart = dashboard.create_pnl_curve(exits_df)
    st.plotly_chart(pnl_chart, use_container_width=True)
    
    # Performance tables
    st.subheader("📈 Daily Performance Summary")
    daily_table = dashboard.create_daily_metrics_table(daily_perf_df)
    if not daily_table.empty:
        st.dataframe(daily_table, use_container_width=True)
    else:
        st.info("No performance data available yet. Start trading to see metrics!")
    
    # Recent signals table
    st.subheader("🎯 Recent Signals")
    if not signals_df.empty:
        recent_signals = signals_df[['timestamp', 'ticker', 'signal_type', 'confidence', 
                                   'market_regime', 'executed']].head(10)
        recent_signals['timestamp'] = pd.to_datetime(recent_signals['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(recent_signals, use_container_width=True)
    else:
        st.info("No signals recorded yet.")
    
    # Auto-refresh
    if st.sidebar.button("🔄 Refresh Data"):
        st.experimental_rerun()
    
    # Export functionality
    if st.sidebar.button("📊 Export Report"):
        from utils.performance_tracker import performance_tracker
        report_path = performance_tracker.export_performance_report(30)
        st.sidebar.success(f"Report exported: {report_path}")


if __name__ == "__main__":
    run_dashboard()
