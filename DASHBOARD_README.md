# 🚀 Signal Flow - Real Trading Dashboard

## Overview
Complete real-time trading dashboard with live data connections and actual buy/sell functionality. This is **LIVE TRADING** - all actions execute real orders.

## ⚡ Quick Start

```bash
# Launch the production dashboard
./start_dashboard.sh
```

Dashboard will be available at: **http://localhost:8501**

## 🎛️ Dashboard Features

### 🔴 Live Trading Tab
- **Quick Buy/Sell**: Execute immediate market orders
- **Live Signals**: Real-time AI trading signals with confidence scores
- **One-Click Execution**: Direct buy/sell buttons for each signal
- **Real-Time Data**: Live price feeds and market information

### 📊 Portfolio Tab
- **Account Overview**: Portfolio value, day P&L, buying power
- **Current Positions**: All holdings with real-time P&L
- **Position Management**: Sell buttons for each position
- **Performance Metrics**: Real-time profit/loss tracking

### 🤖 AI Analysis Tab
- **Model Performance**: Real accuracy metrics from AI learning engine
- **Live Predictions**: Current AI predictions with confidence scores
- **Learning Progress**: AI training status and improvement metrics
- **Prediction History**: Recent AI calls and outcomes

### ⚙️ Configuration Tab
- **Trading Settings**: Auto-trading toggle, position limits
- **Risk Management**: Stop-loss settings, daily limits
- **Confidence Thresholds**: Minimum AI confidence for auto-execution
- **Live Updates**: Changes apply immediately to trading system

## 🎯 Sidebar Controls

### Quick Actions
- **⏸️ Pause Trading**: Immediately stop auto-trading
- **▶️ Resume Trading**: Re-enable auto-trading
- **🔄 Scan Market**: Force immediate market scan
- **📱 Test Alert**: Send test Telegram notification

### Account Summary
- **Portfolio Value**: Real-time account balance
- **Day P&L**: Today's profit/loss
- **Buying Power**: Available cash for trading
- **Active Signals**: Current AI recommendations

## 🔗 Real Integrations

### APIs Connected
- ✅ **Alpaca Trading API**: Live order execution ($200K paper trading account)
- ✅ **Telegram Bot API**: Real-time notifications and alerts
- ✅ **Polygon.io**: Real-time market data and price feeds
- ✅ **MongoDB Atlas**: Trade logging and AI learning data
- ✅ **AI Learning Engine**: Live predictions and performance tracking

### Data Sources
- **Live Market Data**: Real-time price feeds via Polygon API
- **Account Data**: Direct from Alpaca trading account
- **AI Predictions**: Real-time from Signal Flow AI engine
- **Trade History**: All trades logged to production database
- **Performance Metrics**: Calculated from actual trading results

## ⚠️ Important Warnings

### LIVE TRADING SYSTEM
- **All orders are REAL** - Money will be spent/earned
- **No paper trading mode** - This is production trading
- **Immediate execution** - Orders execute instantly
- **Real money at risk** - Only use with funds you can afford to lose

### Account Requirements
- Alpaca trading account with API keys
- Telegram bot token and chat ID
- Polygon.io API key for market data
- MongoDB Atlas database connection

## 🚨 Emergency Controls

### Stop Trading Immediately
1. **Dashboard**: Click "⏸️ Pause Trading" in sidebar
2. **Command Line**: `python real_trading_controls.py pause`
3. **Telegram**: Send `/pause` to your trading bot

### Manual Order Execution
```bash
# Buy 100 shares of AAPL
python real_trading_controls.py buy AAPL 100

# Sell all TSLA shares
python real_trading_controls.py sell TSLA

# Check current positions
python real_trading_controls.py positions

# Get account status
python real_trading_controls.py account
```

## 📱 Telegram Integration

### Live Notifications
- ✅ Trade executions with order IDs
- ✅ AI signal alerts with confidence scores
- ✅ Account status updates
- ✅ System status changes
- ✅ Error alerts and warnings

### Interactive Commands
- `/status` - Get current account status
- `/positions` - List current holdings
- `/pause` - Pause auto-trading
- `/resume` - Resume auto-trading
- `/signals` - Get current AI signals

## 🔧 Technical Details

### File Structure
- `production_dashboard.py` - Main dashboard interface
- `real_trading_controls.py` - Direct trading controller
- `start_dashboard.sh` - Launch script
- `backend/services/` - All trading services

### Dependencies
- **Streamlit**: Web dashboard framework
- **Plotly**: Interactive charts and visualizations
- **Pandas**: Data manipulation and display
- **Alpaca Trade API**: Trading execution
- **aiohttp**: Async HTTP for Telegram
- **Motor**: Async MongoDB driver

### Environment Variables Required
```bash
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET=your_alpaca_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
POLYGON_API_KEY=your_polygon_key
MONGODB_URL=your_mongodb_connection
```

## 🎯 Usage Examples

### Execute Manual Buy Order
1. Go to "🔴 Live Trading" tab
2. Enter ticker symbol (e.g., "AAPL")
3. Enter amount in dollars (e.g., "$1000")
4. Click "🟢 EXECUTE BUY"
5. Order executes immediately with real money

### Sell All Shares of a Stock
1. Go to "📊 Portfolio" tab
2. Find the position you want to sell
3. Click "🔴 Sell" button next to it
4. All shares sold immediately at market price

### Act on AI Signal
1. Go to "🔴 Live Trading" tab
2. View "🚨 Live Trading Signals" section
3. Click buy/sell button on any signal
4. Order executes based on AI recommendation

### Monitor Performance
1. Go to "🤖 AI Analysis" tab
2. View model accuracy and prediction history
3. Check learning progress and improvement metrics
4. Monitor prediction success rate

## 🛡️ Safety Features

### Risk Controls
- **Position Size Limits**: Maximum position sizes enforced
- **Daily Trade Limits**: Maximum trades per day
- **Confidence Thresholds**: Minimum AI confidence required
- **Stop-Loss Orders**: Automatic risk management
- **Account Balance Checks**: Prevent over-leveraging

### Monitoring
- **Real-time Notifications**: All trades reported via Telegram
- **Trade Logging**: Complete audit trail in database
- **Error Handling**: Graceful failure with notifications
- **Health Checks**: System status monitoring

---

**Remember**: This is a LIVE TRADING system. All actions have real financial consequences. Only use with capital you can afford to lose and always monitor your positions closely.
