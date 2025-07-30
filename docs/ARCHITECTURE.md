# 🏗️ SignalFlow Trading System - Architecture Documentation

## 📋 **SYSTEM OVERVIEW**

SignalFlow is an AI-powered trading system optimized for low-cap momentum trading ($0.75-$10 stocks). The system uses advanced technical analysis, machine learning, and automated position sizing to identify and execute profitable trades.

---

## 🏛️ **ARCHITECTURE COMPONENTS**

### **Core Application Layer**
```
├── main.py                    # Main orchestrator and system entry point
├── start_trading.py           # Primary launch script with UI
├── enhanced_trading_ui.py     # Streamlit-based trading interface
└── telegram_webhook.py        # Telegram bot webhook handler
```

### **Agent Layer** (`/agents/`)
AI-powered trading agents that handle specific responsibilities:

- **`market_watcher_agent.py`** - Scans markets for trading opportunities
- **`trade_recommender_agent.py`** - Makes final trading decisions with AI
- **`sentiment_agent.py`** - Analyzes news and social sentiment
- **`reasoning_agent.py`** - Explains trading decisions
- **`execution_monitor_agent.py`** - Monitors active positions
- **`summary_agent.py`** - Generates performance reports

### **Services Layer** (`/services/`)
Core business logic and data processing:

#### **Trading Core**
- **`config.py`** - Central configuration management
- **`data_provider.py`** - Market data API integration (Polygon)
- **`alpaca_trading.py`** - Trade execution via Alpaca
- **`dynamic_screener.py`** - Real-time stock screening

#### **Technical Analysis**
- **`indicators.py`** - Basic technical indicators
- **`enhanced_indicators.py`** - Advanced regime-aware indicators
- **`williams_r_indicator.py`** - Williams %R momentum oscillator
- **`bollinger_squeeze_detector.py`** - Volatility compression detection
- **`momentum_multiplier.py`** - Explosive momentum detection

#### **Position Management**
- **`enhanced_position_sizer.py`** - Kelly Criterion + volatility scaling
- **`market_regime_detector.py`** - Market condition analysis
- **`interactive_trading.py`** - Manual trade confirmation

#### **AI & Learning**
- **`ai_learning_engine.py`** - Machine learning for trade improvement
- **`learning_manager.py`** - Learning cycle orchestration
- **`enhanced_decision_logger.py`** - Decision tracking and analysis
- **`learning_dashboard_api.py`** - API for learning metrics

#### **Communication**
- **`telegram_bot.py`** - Interactive Telegram notifications
- **`production_telegram.py`** - Production Telegram integration
- **`twilio_whatsapp.py`** - WhatsApp notifications (optional)

#### **System Management**
- **`system_orchestrator.py`** - System-wide coordination
- **`automated_trading_manager.py`** - Automated execution management
- **`database_manager.py`** - MongoDB data persistence
- **`error_handler.py`** - Error management and recovery
- **`health_monitor.py`** - System health monitoring

### **Utility Layer** (`/utils/`)
- **`logger_setup.py`** - Centralized logging configuration

### **Data Layer** (`/data/`)
- **Trade logs** - Historical trade data
- **Watchlists** - Dynamic stock lists
- **AI decisions** - Learning engine data
- **Performance metrics** - System analytics

---

## 🔄 **SYSTEM FLOW**

### **1. Market Scanning**
```
Market Watcher Agent → Dynamic Screener → Filter by Low-Cap Criteria
    ↓
Williams %R + Bollinger Squeeze Analysis → Momentum Multiplier
    ↓
Volume & Float Validation → Generate Setup
```

### **2. Trade Analysis**
```
Setup → Sentiment Agent → News Analysis
    ↓
Trade Recommender Agent → Technical Analysis + AI Learning
    ↓
Enhanced Position Sizer → Kelly Criterion + Volatility Scaling
    ↓
Momentum Multiplier → Dynamic Profit Targets
```

### **3. Decision Making**
```
Confidence Score + Momentum Score → Validation
    ↓
Interactive Trading → Telegram Notification → User Approval
    ↓
Execution Monitor → Position Management
```

### **4. Learning Cycle**
```
Trade Outcome → Enhanced Decision Logger → AI Learning Engine
    ↓
Pattern Recognition → Adaptive Thresholds → Improved Signals
```

---

## 📡 **API ENDPOINTS**

### **Learning Dashboard API** (`/services/learning_dashboard_api.py`)

#### **Status Endpoints**
- **`GET /api/learning/status`** - Learning system status
- **`GET /api/learning/health`** - System health check
- **`GET /api/learning/version`** - API version info

#### **Metrics Endpoints**
- **`GET /api/learning/metrics`** - Detailed learning metrics
- **`GET /api/learning/performance`** - Performance analytics
- **`GET /api/learning/insights`** - Daily insights & recommendations
- **`GET /api/learning/predictions`** - Recent predictions
- **`GET /api/learning/decisions`** - Decision history

#### **Control Endpoints**
- **`POST /api/learning/trigger-learning`** - Manual learning cycle
- **`POST /api/learning/trigger-backtest`** - Manual backtest
- **`POST /api/learning/reset`** - Reset learning data

### **Telegram Webhook** (`/telegram_webhook.py`)
- **`POST /webhook/telegram`** - Handles Telegram bot interactions
- **`POST /webhook/telegram/trade`** - Trade execution callbacks

---

## 🔧 **CONFIGURATION SYSTEM**

### **Environment Variables** (`.env`)
```bash
# Trading APIs
POLYGON_API_KEY=your_polygon_key
ALPACA_API_KEY=your_alpaca_key  
ALPACA_SECRET=your_alpaca_secret

# Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Parameters
TICKER_PRICE_MIN=0.75
TICKER_PRICE_MAX=10.0
POSITION_SIZE_PERCENT=0.25
MAX_POSITION_SIZE_PERCENT=0.50
MIN_CONFIDENCE_SCORE=6.0
PAPER_TRADING=true

# Database
MONGODB_URL=your_mongodb_connection
```

### **Configuration Classes** (`/services/config.py`)
- **Low-Cap Momentum Parameters** - Price range, volume, float requirements
- **Position Sizing Configuration** - Base size, maximums, sub-$3 adjustments
- **Technical Analysis Settings** - Williams %R, Bollinger Squeeze thresholds
- **Risk Management** - Daily limits, volatility targets
- **Trading Windows** - Market hours, pre-market, power hour

---

## 🧠 **AI LEARNING SYSTEM**

### **Learning Components**
1. **Decision Logging** - Records all trading decisions with context
2. **Outcome Tracking** - Monitors trade results and performance
3. **Pattern Recognition** - Identifies successful setups and conditions
4. **Adaptive Thresholds** - Adjusts confidence scores based on performance
5. **Strategy Optimization** - Improves position sizing and entry/exit timing

### **Learning Triggers**
- **Real-time**: After each trade execution
- **Daily**: End-of-day performance analysis
- **Weekly**: Strategy effectiveness review
- **Manual**: Via API endpoints or dashboard

---

## 🚦 **SYSTEM STATES**

### **Trading Modes**
- **Paper Trading** - Simulated trades for learning (default)
- **Interactive Trading** - Manual trade approval via Telegram
- **Auto Trading** - Fully automated execution (high-confidence only)

### **Market Regimes**
- **Trending High Vol** - Momentum strategies, wider stops
- **Trending Low Vol** - Trend following, tighter stops
- **Mean Reverting High Vol** - Contrarian plays, quick exits
- **Mean Reverting Low Vol** - Range trading strategies
- **Uncertain** - Conservative approach, reduced sizes

---

## 🔒 **SECURITY & RELIABILITY**

### **Error Handling**
- **Graceful Degradation** - System continues with reduced functionality
- **Automatic Fallbacks** - Enhanced → Basic indicators if components fail
- **Connection Resilience** - API retry logic and timeout handling
- **Data Validation** - Input sanitization and type checking

### **Monitoring**
- **Health Checks** - Continuous system monitoring
- **Performance Metrics** - Real-time system performance tracking
- **Alert System** - Telegram notifications for system issues
- **Logging** - Comprehensive logging for debugging and analysis

---

## 📊 **PERFORMANCE CHARACTERISTICS**

### **Latency**
- **Market Scanning**: ~30 seconds per cycle
- **Trade Analysis**: ~5 seconds per setup
- **Decision Making**: ~2 seconds
- **Execution**: ~1 second via Alpaca API

### **Throughput**
- **Daily Scans**: 100+ stocks analyzed
- **Signal Generation**: 15-25 setups per day
- **Trade Execution**: 5-10 high-quality trades
- **Data Processing**: Real-time with 60-second refresh

### **Resource Usage**
- **Memory**: ~200MB baseline, ~500MB during heavy processing
- **CPU**: Low usage except during ML training cycles
- **Network**: API calls to Polygon, Alpaca, Telegram
- **Storage**: MongoDB for persistent data, local logs

---

*Architecture Documentation v2.0 - Updated July 29, 2025*
