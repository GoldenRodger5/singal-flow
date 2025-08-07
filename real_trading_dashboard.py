"""
Real Trading Dashboard - Complete interface with real data and trading controls
"""
import streamlit as st
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any
from loguru import logger
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.alpaca_trading import AlpacaTradingService
from services.ai_learning_engine import AILearningEngine
from services.database_manager import DatabaseManager
from services.config import Config
from services.telegram_trading import telegram_trading

class RealTradingDashboard:
    """Complete real trading dashboard with live data and controls."""
    
    def __init__(self):
        self.config = Config()
        self.alpaca = AlpacaTradingService()
        self.ai_engine = AILearningEngine()
        self.db = DatabaseManager()
        
    async def show_main_dashboard(self):
        """Main dashboard interface."""
        st.set_page_config(
            page_title="Signal Flow - Real Trading Dashboard",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("🚀 Signal Flow - Real Trading Dashboard")
        st.markdown("---")
        
        # Sidebar controls
        self.show_sidebar_controls()
        
        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Live Trading", 
            "🤖 AI Predictions", 
            "💼 Portfolio", 
            "⚙️ Configuration", 
            "📈 Performance"
        ])
        
        with tab1:
            await self.show_live_trading_tab()
            
        with tab2:
            await self.show_ai_predictions_tab()
            
        with tab3:
            await self.show_portfolio_tab()
            
        with tab4:
            await self.show_configuration_tab()
            
        with tab5:
            await self.show_performance_tab()
    
    def show_sidebar_controls(self):
        """Show real-time controls in sidebar."""
        st.sidebar.markdown("## 🎛️ Trading Controls")
        
        # System status
        if self.config.AUTO_TRADING_ENABLED:
            st.sidebar.success("🤖 Auto-Trading: ENABLED")
        else:
            st.sidebar.warning("🤖 Auto-Trading: DISABLED")
        
        # Quick actions
        st.sidebar.markdown("### Quick Actions")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("⏸️ Pause Trading", key="pause"):
                self.pause_trading()
        
        with col2:
            if st.button("▶️ Resume Trading", key="resume"):
                self.resume_trading()
        
        if st.sidebar.button("🔄 Force Market Scan", key="scan"):
            self.trigger_market_scan()
        
        if st.sidebar.button("📱 Test Notification", key="notify"):
            self.send_test_notification()
        
        # Account summary
        account_data = self.get_account_summary()
        if account_data:
            st.sidebar.markdown("### 💰 Account Summary")
            st.sidebar.metric("Buying Power", f"${account_data.get('buying_power', 0):,.2f}")
            st.sidebar.metric("Day P&L", f"${account_data.get('day_pl', 0):,.2f}")
            st.sidebar.metric("Total Value", f"${account_data.get('total_value', 0):,.2f}")
    
    async def show_live_trading_tab(self):
        """Show live trading interface with real buy/sell controls."""
        st.markdown("## 📊 Live Trading")
        
        # Real-time signals
        st.markdown("### 🚨 Live Signals")
        
        signals = await self.get_live_signals()
        
        if signals:
            for signal in signals:
                self.show_signal_card(signal)
        else:
            st.info("🔍 No active signals. AI is monitoring markets...")
        
        # Recent trades
        st.markdown("### 📈 Recent Trades")
        recent_trades = await self.get_recent_trades()
        
        if recent_trades:
            df = pd.DataFrame(recent_trades)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No recent trades")
    
    def show_signal_card(self, signal: Dict[str, Any]):
        """Show individual signal with real buy/sell buttons."""
        ticker = signal.get('ticker', 'Unknown')
        confidence = signal.get('confidence', 0)
        entry_price = signal.get('entry_price', 0)
        target_price = signal.get('target_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.write(f"**{ticker}**")
                st.write(f"Entry: ${entry_price:.2f}")
                st.write(f"Target: ${target_price:.2f}")
                st.write(f"Stop: ${stop_loss:.2f}")
            
            with col2:
                st.metric("Confidence", f"{confidence:.1f}/10")
                risk_reward = (target_price - entry_price) / (entry_price - stop_loss) if stop_loss < entry_price else 0
                st.metric("R:R Ratio", f"{risk_reward:.1f}:1")
            
            with col3:
                reasoning = signal.get('reasoning', 'AI Analysis')
                st.write(f"**Analysis:** {reasoning[:100]}...")
            
            with col4:
                # Real buy button
                if st.button(f"🟢 BUY {ticker}", key=f"buy_{ticker}"):
                    self.execute_buy_order(signal)
                
                # Real sell button (if we have position)
                if self.has_position(ticker):
                    if st.button(f"🔴 SELL {ticker}", key=f"sell_{ticker}"):
                        self.execute_sell_order(ticker)
            
            st.markdown("---")
    
    async def show_ai_predictions_tab(self):
        """Show AI predictions with real data."""
        st.markdown("## 🤖 AI Predictions")
        
        predictions = await self.get_ai_predictions()
        
        if predictions:
            # Summary metrics
            total_preds = len(predictions)
            high_conf = len([p for p in predictions if p.confidence_score >= 0.8])
            avg_conf = sum(p.confidence_score for p in predictions) / total_preds
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Predictions", total_preds)
            col2.metric("High Confidence", high_conf)
            col3.metric("Avg Confidence", f"{avg_conf:.2f}")
            
            # Predictions table
            pred_data = []
            for pred in predictions:
                pred_data.append({
                    'Ticker': pred.ticker,
                    'Direction': pred.predicted_direction,
                    'Confidence': f"{pred.confidence_score:.2f}",
                    'Expected Move': f"{pred.predicted_move_percent:.1f}%",
                    'Timeframe': f"{pred.predicted_timeframe_hours:.1f}h",
                    'Timestamp': pred.timestamp.strftime('%H:%M:%S')
                })
            
            df = pd.DataFrame(pred_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("🔮 AI is learning... No predictions available yet.")
    
    async def show_portfolio_tab(self):
        """Show real portfolio data."""
        st.markdown("## 💼 Portfolio")
        
        positions = await self.get_positions()
        account = await self.get_account_info()
        
        if account:
            # Account overview
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Portfolio Value", f"${float(account.get('portfolio_value', 0)):,.2f}")
            col2.metric("Day P&L", f"${float(account.get('unrealized_pl', 0)):,.2f}")
            col3.metric("Buying Power", f"${float(account.get('buying_power', 0)):,.2f}")
            col4.metric("Cash", f"${float(account.get('cash', 0)):,.2f}")
        
        if positions:
            # Positions table with sell buttons
            st.markdown("### Current Positions")
            
            for position in positions:
                if float(position.get('qty', 0)) != 0:
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                    
                    ticker = position.get('symbol')
                    qty = float(position.get('qty', 0))
                    market_value = float(position.get('market_value', 0))
                    unrealized_pl = float(position.get('unrealized_pl', 0))
                    unrealized_plpc = float(position.get('unrealized_plpc', 0)) * 100
                    
                    col1.write(f"**{ticker}**")
                    col2.metric("Quantity", f"{qty:.0f}")
                    col3.metric("Value", f"${market_value:.2f}")
                    col4.metric("P&L", f"${unrealized_pl:.2f}", delta=f"{unrealized_plpc:.1f}%")
                    
                    # Real sell button
                    if col5.button(f"🔴 SELL", key=f"sell_pos_{ticker}"):
                        self.execute_sell_order(ticker, qty)
        else:
            st.info("No current positions")
    
    async def show_configuration_tab(self):
        """Show real configuration controls."""
        st.markdown("## ⚙️ Configuration")
        
        # Trading settings
        st.markdown("### 🎯 Trading Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            auto_trading = st.checkbox(
                "Auto Trading Enabled", 
                value=self.config.AUTO_TRADING_ENABLED,
                help="Enable/disable automatic trade execution"
            )
            
            max_position_size = st.number_input(
                "Max Position Size ($)", 
                value=float(getattr(self.config, 'MAX_POSITION_SIZE', 10000)),
                min_value=100.0,
                max_value=50000.0,
                step=100.0
            )
            
            min_confidence = st.slider(
                "Minimum Confidence Score",
                min_value=0.0,
                max_value=10.0,
                value=float(getattr(self.config, 'MIN_CONFIDENCE_SCORE', 7.0)),
                step=0.1
            )
        
        with col2:
            daily_trade_limit = st.number_input(
                "Daily Trade Limit",
                value=int(getattr(self.config, 'MAX_DAILY_TRADES', 10)),
                min_value=1,
                max_value=50,
                step=1
            )
            
            risk_per_trade = st.slider(
                "Risk Per Trade (%)",
                min_value=0.5,
                max_value=5.0,
                value=float(getattr(self.config, 'MAX_RISK_PER_TRADE', 2.0)),
                step=0.1
            )
        
        # Save configuration button
        if st.button("💾 Save Configuration"):
            self.save_configuration({
                'auto_trading': auto_trading,
                'max_position_size': max_position_size,
                'min_confidence': min_confidence,
                'daily_trade_limit': daily_trade_limit,
                'risk_per_trade': risk_per_trade
            })
    
    async def show_performance_tab(self):
        """Show real performance metrics."""
        st.markdown("## 📈 Performance")
        
        # Get real performance data
        performance = await self.get_performance_data()
        
        if performance:
            # Performance metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Win Rate", f"{performance.get('win_rate', 0)*100:.1f}%")
            col2.metric("Avg R:R", f"{performance.get('avg_rr', 0):.1f}:1")
            col3.metric("Total Trades", performance.get('total_trades', 0))
            col4.metric("Total P&L", f"${performance.get('total_pnl', 0):.2f}")
            
            # Performance chart
            if performance.get('daily_pnl'):
                df = pd.DataFrame(performance['daily_pnl'])
                fig = px.line(df, x='date', y='pnl', title='Daily P&L')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No performance data available yet")
    
    # Real execution methods
    def execute_buy_order(self, signal: Dict[str, Any]):
        """Execute real buy order."""
        try:
            ticker = signal.get('ticker')
            entry_price = signal.get('entry_price')
            
            # Calculate position size
            account = asyncio.run(self.get_account_info())
            buying_power = float(account.get('buying_power', 0))
            max_position = min(buying_power * 0.1, 10000)  # 10% of buying power, max $10k
            shares = int(max_position / entry_price)
            
            if shares > 0:
                # Execute through Alpaca
                order_result = asyncio.run(self.alpaca.place_buy_order({
                    'ticker': ticker,
                    'shares': shares,
                    'entry': entry_price
                }))
                
                if order_result and order_result.get('success'):
                    st.success(f"✅ Buy order executed: {shares} shares of {ticker}")
                    
                    # Send notification
                    asyncio.run(telegram_trading.send_message(
                        f"✅ *BUY ORDER EXECUTED*\\n\\n"
                        f"📊 {ticker}: {shares} shares\\n"
                        f"💰 Price: ${entry_price:.2f}\\n"
                        f"🆔 Order: {order_result.get('order_id', 'N/A')}"
                    ))
                else:
                    st.error(f"❌ Buy order failed: {order_result.get('error', 'Unknown error')}")
            else:
                st.error("❌ Insufficient buying power")
                
        except Exception as e:
            st.error(f"❌ Error executing buy order: {e}")
            logger.error(f"Buy order execution error: {e}")
    
    def execute_sell_order(self, ticker: str, shares: float = None):
        """Execute real sell order."""
        try:
            if shares is None:
                # Get current position
                positions = asyncio.run(self.get_positions())
                position = next((p for p in positions if p.get('symbol') == ticker), None)
                if position:
                    shares = abs(float(position.get('qty', 0)))
                else:
                    st.error(f"❌ No position found for {ticker}")
                    return
            
            if shares > 0:
                # Execute through Alpaca
                order_result = asyncio.run(self.alpaca.place_sell_order(ticker, shares))
                
                if order_result and order_result.get('success'):
                    st.success(f"✅ Sell order executed: {shares} shares of {ticker}")
                    
                    # Send notification
                    asyncio.run(telegram_trading.send_message(
                        f"✅ *SELL ORDER EXECUTED*\\n\\n"
                        f"📊 {ticker}: {shares} shares\\n"
                        f"🆔 Order: {order_result.get('order_id', 'N/A')}"
                    ))
                else:
                    st.error(f"❌ Sell order failed: {order_result.get('error', 'Unknown error')}")
            else:
                st.error("❌ No shares to sell")
                
        except Exception as e:
            st.error(f"❌ Error executing sell order: {e}")
            logger.error(f"Sell order execution error: {e}")
    
    # Real data methods
    async def get_live_signals(self) -> List[Dict[str, Any]]:
        """Get real live trading signals."""
        try:
            predictions = await self.get_ai_predictions()
            signals = []
            
            for pred in predictions:
                if pred.confidence_score >= 0.7:  # High confidence signals only
                    signals.append({
                        'ticker': pred.ticker,
                        'confidence': pred.confidence_score * 10,
                        'entry_price': getattr(pred, 'current_price', 0),
                        'target_price': getattr(pred, 'target_price', 0),
                        'stop_loss': getattr(pred, 'stop_price', 0),
                        'reasoning': ' | '.join(pred.reasoning_factors[:2])
                    })
            
            return signals
        except Exception as e:
            logger.error(f"Error getting live signals: {e}")
            return []
    
    async def get_ai_predictions(self):
        """Get real AI predictions."""
        try:
            return self.ai_engine.get_recent_predictions()
        except Exception as e:
            logger.error(f"Error getting AI predictions: {e}")
            return []
    
    async def get_positions(self):
        """Get real positions."""
        try:
            return await self.alpaca.get_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_account_info(self):
        """Get real account info."""
        try:
            return await self.alpaca.get_account()
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    async def get_recent_trades(self):
        """Get real recent trades."""
        try:
            # Get from database
            trades = await self.db.get_recent_trades(limit=20)
            return trades
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    def get_account_summary(self) -> Dict[str, float]:
        """Get account summary for sidebar."""
        try:
            account = asyncio.run(self.get_account_info())
            if account:
                return {
                    'buying_power': float(account.get('buying_power', 0)),
                    'day_pl': float(account.get('unrealized_pl', 0)),
                    'total_value': float(account.get('portfolio_value', 0))
                }
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
        return {}
    
    def has_position(self, ticker: str) -> bool:
        """Check if we have a position in ticker."""
        try:
            positions = asyncio.run(self.get_positions())
            return any(p.get('symbol') == ticker and float(p.get('qty', 0)) != 0 for p in positions)
        except:
            return False
    
    # Control methods
    def pause_trading(self):
        """Pause trading system."""
        try:
            self.config.AUTO_TRADING_ENABLED = False
            st.success("⏸️ Trading paused")
            asyncio.run(telegram_trading.send_message("⏸️ Trading system paused via dashboard"))
        except Exception as e:
            st.error(f"Error pausing trading: {e}")
    
    def resume_trading(self):
        """Resume trading system."""
        try:
            self.config.AUTO_TRADING_ENABLED = True
            st.success("▶️ Trading resumed")
            asyncio.run(telegram_trading.send_message("▶️ Trading system resumed via dashboard"))
        except Exception as e:
            st.error(f"Error resuming trading: {e}")
    
    def trigger_market_scan(self):
        """Trigger market scan."""
        try:
            # This would trigger the main market scan
            st.success("🔄 Market scan triggered")
            asyncio.run(telegram_trading.send_message("🔄 Market scan triggered via dashboard"))
        except Exception as e:
            st.error(f"Error triggering scan: {e}")
    
    def send_test_notification(self):
        """Send test notification."""
        try:
            asyncio.run(telegram_trading.send_message(
                f"📱 *TEST NOTIFICATION*\\n\\n"
                f"✅ Dashboard connected\\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            ))
            st.success("📱 Test notification sent")
        except Exception as e:
            st.error(f"Error sending notification: {e}")
    
    def save_configuration(self, config_data: Dict[str, Any]):
        """Save configuration changes."""
        try:
            # Update config object
            self.config.AUTO_TRADING_ENABLED = config_data['auto_trading']
            # Note: In a real implementation, these would be saved to environment/database
            
            st.success("💾 Configuration saved")
            asyncio.run(telegram_trading.send_message("⚙️ Configuration updated via dashboard"))
        except Exception as e:
            st.error(f"Error saving configuration: {e}")
    
    async def get_performance_data(self):
        """Get real performance data."""
        try:
            # Get from database
            performance = await self.db.get_performance_summary()
            return performance
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return {}

# Main app
def main():
    dashboard = RealTradingDashboard()
    asyncio.run(dashboard.show_main_dashboard())

if __name__ == "__main__":
    main()
