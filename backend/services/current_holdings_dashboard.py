"""
Current Holdings Dashboard - Real-time position tracking
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def show_current_holdings():
    """Display current trading positions with P&L tracking."""
    st.markdown("## 📊 Current Holdings Dashboard")
    
    try:
        # Load holdings data
        holdings_data = get_holdings_data()
        
        if holdings_data.empty:
            st.info("📈 No current positions. Ready for new trades!")
            return
            
        # Display summary metrics
        show_portfolio_summary(holdings_data)
        
        # Display individual positions
        show_position_details(holdings_data)
        
        # Show recent trades
        show_recent_trades()
        
    except Exception as e:
        logger.error(f"Error displaying holdings: {e}")
        st.error(f"Error loading holdings data: {e}")


def get_holdings_data():
    """Load current holdings data from CSV files."""
    try:
        # Check for holdings file
        holdings_file = 'data/current_holdings.csv'
        
        if os.path.exists(holdings_file):
            holdings_df = pd.read_csv(holdings_file)
            
            # Add calculated P&L columns if not present
            if 'unrealized_pnl' not in holdings_df.columns:
                holdings_df['unrealized_pnl'] = 0.0
                holdings_df['unrealized_pnl_percent'] = 0.0
                
            return holdings_df
        else:
            # Return empty DataFrame with proper columns
            return pd.DataFrame(columns=[
                'symbol', 'quantity', 'avg_price', 'current_price', 
                'market_value', 'unrealized_pnl', 'unrealized_pnl_percent',
                'entry_date', 'entry_confidence'
            ])
            
    except Exception as e:
        logger.error(f"Error loading holdings data: {e}")
        return pd.DataFrame()


def show_portfolio_summary(holdings_df):
    """Display portfolio summary metrics."""
    if holdings_df.empty:
        return
        
    # Calculate summary metrics
    total_value = holdings_df['market_value'].sum()
    total_pnl = holdings_df['unrealized_pnl'].sum()
    avg_pnl_percent = holdings_df['unrealized_pnl_percent'].mean()
    position_count = len(holdings_df)
    
    # Display in columns
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric(
            "💰 Portfolio Value", 
            f"${total_value:,.2f}",
            help="Total market value of all positions"
        )
        
    with metric_col2:
        st.metric(
            "📈 Total P&L", 
            f"${total_pnl:,.2f}",
            delta=f"{avg_pnl_percent:.1f}%",
            help="Total unrealized profit/loss"
        )
        
    with metric_col3:
        st.metric(
            "📊 Positions", 
            f"{position_count}",
            help="Number of current positions"
        )
        
    with metric_col4:
        # Calculate winners vs losers
        winners = len(holdings_df[holdings_df['unrealized_pnl'] > 0])
        win_rate = (winners / position_count * 100) if position_count > 0 else 0
        st.metric(
            "🎯 Win Rate", 
            f"{win_rate:.0f}%",
            help="Percentage of profitable positions"
        )


def show_position_details(holdings_df):
    """Display detailed position information."""
    st.markdown("### 📋 Position Details")
    
    # Sort by P&L percentage descending
    holdings_df = holdings_df.sort_values('unrealized_pnl_percent', ascending=False)
    
    for idx, position in holdings_df.iterrows():
        with st.expander(f"🏷️ {position['symbol']} - ${position['unrealized_pnl']:,.2f} ({position['unrealized_pnl_percent']:.1f}%)"):
            
            pos_col1, pos_col2, pos_col3 = st.columns(3)
            
            with pos_col1:
                st.write("**Position Info:**")
                st.write(f"• Symbol: {position['symbol']}")
                st.write(f"• Quantity: {position['quantity']:,.0f}")
                st.write(f"• Entry Date: {position.get('entry_date', 'N/A')}")
                st.write(f"• Entry Confidence: {position.get('entry_confidence', 'N/A')}")
                
            with pos_col2:
                st.write("**Pricing:**")
                st.write(f"• Avg Price: ${position['avg_price']:.4f}")
                st.write(f"• Current Price: ${position['current_price']:.4f}")
                st.write(f"• Market Value: ${position['market_value']:,.2f}")
                
                # Calculate price change
                price_change = position['current_price'] - position['avg_price']
                price_change_percent = (price_change / position['avg_price']) * 100
                st.write(f"• Price Change: ${price_change:.4f} ({price_change_percent:.1f}%)")
                
            with pos_col3:
                st.write("**P&L Analysis:**")
                st.write(f"• Unrealized P&L: ${position['unrealized_pnl']:,.2f}")
                st.write(f"• P&L Percentage: {position['unrealized_pnl_percent']:.1f}%")
                
                # Show P&L color coding
                if position['unrealized_pnl'] > 0:
                    st.success("📈 Profitable Position")
                elif position['unrealized_pnl'] < 0:
                    st.error("📉 Loss Position")
                else:
                    st.info("➡️ Breakeven Position")
                
                # Action buttons
                if st.button(f"📤 Close {position['symbol']}", key=f"close_{position['symbol']}"):
                    st.warning(f"Close position feature for {position['symbol']} - Implementation needed")


def show_recent_trades():
    """Display recent trade history."""
    st.markdown("### 📜 Recent Trades")
    
    try:
        # Load trade history
        trade_file = 'data/trade_history.csv'
        
        if os.path.exists(trade_file):
            trades_df = pd.read_csv(trade_file)
            
            # Show last 10 trades
            recent_trades = trades_df.tail(10).sort_values('timestamp', ascending=False)
            
            if not recent_trades.empty:
                # Display in table format
                display_cols = ['timestamp', 'symbol', 'action', 'quantity', 'price', 'confidence_score']
                available_cols = [col for col in display_cols if col in recent_trades.columns]
                
                st.dataframe(
                    recent_trades[available_cols],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No recent trades found")
        else:
            st.info("No trade history available yet")
            
    except Exception as e:
        logger.error(f"Error loading recent trades: {e}")
        st.warning("Could not load recent trade history")


def create_sample_holdings():
    """DEPRECATED: Now gets real holdings from Alpaca API - NO SAMPLE DATA."""
    try:
        from services.alpaca_trading import AlpacaTradingService
        
        logger.info("📊 Getting REAL holdings from Alpaca API")
        
        alpaca = AlpacaTradingService()
        
        # Get real positions from Alpaca
        positions = await alpaca.get_positions()
        
        if not positions:
            logger.info("No current positions")
            return pd.DataFrame()  # Return empty dataframe
        
        # Convert to dataframe format
        holdings_data = {
            'symbol': [],
            'quantity': [],
            'avg_price': [],
            'current_price': [],
            'market_value': [],
            'unrealized_pnl': [],
            'unrealized_pnl_percent': [],
            'entry_date': [],
            'entry_confidence': []
        }
        
        for position in positions:
            if float(position.get('qty', 0)) != 0:  # Only open positions
                holdings_data['symbol'].append(position.get('symbol'))
                holdings_data['quantity'].append(float(position.get('qty', 0)))
                holdings_data['avg_price'].append(float(position.get('avg_cost', 0)))
                holdings_data['current_price'].append(float(position.get('market_value', 0)) / float(position.get('qty', 1)))
                holdings_data['market_value'].append(float(position.get('market_value', 0)))
                holdings_data['unrealized_pnl'].append(float(position.get('unrealized_pl', 0)))
                holdings_data['unrealized_pnl_percent'].append(float(position.get('unrealized_plpc', 0)) * 100)
                holdings_data['entry_date'].append(position.get('updated_at', '')[:10])  # Date only
                holdings_data['entry_confidence'].append(8.0)  # Default confidence
        
        df = pd.DataFrame(holdings_data)
        
        if not df.empty:
            df.to_csv('data/current_holdings.csv', index=False)
            logger.info(f"Real holdings data saved: {len(df)} positions")
        
        return df
        
    except Exception as e:
        logger.error(f"Error getting real holdings: {e}")
        # Return empty dataframe instead of sample data
        return pd.DataFrame()
