# 🚀 SignalFlow Start Scripts Guide

> **Complete reference for all system launch options and workflows**

---

## 📋 **QUICK REFERENCE**

| Script | Purpose | Use Case | Interface |
|--------|---------|----------|-----------|
| `start_trading.py` | Complete trading system | **Production trading** | Streamlit UI + Telegram |
| `scripts/launch_ai_system.py` | AI learning + dashboard | **Data collection & analysis** | FastAPI dashboard |
| `scripts/launch_fast_ui.py` | Trading interface only | **Manual trading** | Streamlit UI only |
| `main.py` | Core system orchestrator | **Background automation** | Telegram notifications |
| `telegram_webhook.py` | Interactive bot handler | **Telegram-first trading** | Telegram bot interface |

---

## 🎯 **PRIMARY START SCRIPTS**

### **1. start_trading.py** ⭐ *RECOMMENDED*
```bash
python start_trading.py
```
**Complete trading system with all features enabled**

**What it includes:**
- ✅ Real-time market scanning (100+ stocks)
- ✅ Williams %R momentum detection  
- ✅ Momentum multiplier scoring (0-10 scale)
- ✅ AI-enhanced trade recommendations
- ✅ Enhanced position sizing (Kelly Criterion)
- ✅ Interactive Telegram bot notifications
- ✅ Streamlit trading UI (localhost:8501)
- ✅ Automated trade execution (paper mode)
- ✅ AI learning from all trades

**Best for:**
- Production trading workflow
- Complete system operation
- Maximum feature utilization
- Recommended for all users
- Opens enhanced Streamlit UI in your browser
- Starts Telegram bot for notifications
- Enables interactive trade approval
- Perfect for daily trading

**Use when:** You want the full trading experience with UI

---

### **🧠 AI LEARNING SYSTEM**
```bash
python scripts/launch_ai_system.py
```
**What it does:**
- Starts the main trading system
- Launches AI learning dashboard API
- Enables continuous learning from trades
- Provides detailed analytics and insights
- API available at http://localhost:8001/docs

**Use when:** You want comprehensive AI learning and analytics

---

### **⚡ FAST UI ONLY**
```bash
python scripts/launch_fast_ui.py
```
**What it does:**
- Launches only the Streamlit trading interface
- Ultra-fast startup (30 seconds)
- No background services
- Perfect for quick signal checking

**Use when:** You just want to check signals quickly

---

### **🏭 PRODUCTION MODE**
```bash
python scripts/launch_production.py
```
**What it does:**
- Starts production-ready trading system
- Enhanced error handling and recovery
- Optimized for 24/7 operation
- Comprehensive logging and monitoring

**Use when:** Running in live production environment

---

## 🔧 **ADDITIONAL SCRIPTS**

### **📊 Production Dashboard**
```bash
python scripts/production_dashboard.py
```
- Real-time system monitoring
- Performance metrics visualization
- Health status overview

### **🎛️ Live Dashboard**
```bash
python scripts/live_dashboard.py
```
- Live trading activity monitoring
- Position tracking
- P&L visualization

### **📈 Stability Phase**
```bash
python scripts/run_stability_phase.py
```
- Paper trading with enhanced logging
- System performance validation
- Recommended for first 30 days

### **🔄 MongoDB Migration**
```bash
python scripts/migrate_to_full_mongodb.py
```
- Migrate local data to MongoDB Atlas
- Setup cloud database persistence
- One-time setup script

---

## 📱 **UI ACCESS POINTS**

After starting any script with UI:

- **Trading Interface:** http://localhost:8501
- **AI Learning Dashboard:** http://localhost:8001/docs
- **Production Monitor:** http://localhost:8002

---

## ⚙️ **CONFIGURATION**

Before first run, ensure your `.env` file has:

```bash
# Required APIs
POLYGON_API_KEY=your_polygon_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET=your_alpaca_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Settings
PAPER_TRADING=true
TICKER_PRICE_MIN=0.75
TICKER_PRICE_MAX=10.0
POSITION_SIZE_PERCENT=0.25
MAX_POSITION_SIZE_PERCENT=0.50
```

---

## 🎯 **RECOMMENDED WORKFLOW**

### **Day 1-7: Learning Phase**
```bash
python start_trading.py
```
- Start with paper trading
- Let system collect 20-30 trades
- Monitor Telegram notifications
- Review performance daily

### **Day 8-30: Optimization Phase**
```bash
python scripts/launch_ai_system.py
```
- Enable AI learning dashboard
- Analyze performance patterns
- Adjust configuration based on results
- Continue paper trading

### **Day 31+: Production Phase**
```bash
python scripts/launch_production.py
```
- Switch to live trading (small positions)
- Monitor system stability
- Scale up position sizes gradually
- Full production operation

---

## 🚨 **TROUBLESHOOTING**

### **Script Won't Start**
1. Check Python version: `python --version` (need 3.8+)
2. Install requirements: `pip install -r requirements.txt`
3. Verify API keys in `.env` file
4. Check logs in `/logs/` directory

### **UI Not Loading**
1. Wait 30-60 seconds for startup
2. Check browser at http://localhost:8501
3. Look for port conflicts
4. Restart script if needed

### **No Telegram Notifications**
1. Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
2. Test bot setup: `python tests/test_telegram_bot.py`
3. Check bot permissions

### **API Errors**
1. Verify Polygon API key has market data access
2. Confirm Alpaca account is funded and approved
3. Check API rate limits

---

## 📞 **QUICK HELP**

### **Check System Status**
```bash
python -c "from services.config import Config; print('✅ Config loaded successfully')"
```

### **Test Components**
```bash
python tests/test_enhanced_momentum_system.py
```

### **View Logs**
```bash
tail -f logs/signalflow.log
```

---

## 🎉 **SUCCESS INDICATORS**

When your system is running correctly, you should see:

✅ **Terminal Output:**
```
🚀 Starting Enhanced Signal Flow Trading System
✅ Low-cap momentum optimizations active
✅ Williams %R + Momentum Multiplier enabled
✅ Enhanced position sizing (25-50%)
✅ Sub-$3 stock specialization active
🎯 Scanning for $0.75-$10 momentum opportunities...
```

✅ **Browser Interface:** Streamlit app loads at localhost:8501

✅ **Telegram Notifications:** Bot sends "System online" message

✅ **API Response:** Learning dashboard accessible at localhost:8001/docs

---

*Start Scripts Guide v2.0 - Updated July 29, 2025*
