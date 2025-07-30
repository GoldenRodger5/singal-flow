# 🚀 SignalFlow - AI-Powered Low-Cap Momentum Trading System

> **Advanced trading system optimized for $0.75-$10 momentum opportunities with AI learning and enhanced position sizing**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Trading Focus](https://img.shields.io/badge/Focus-Low--Cap%20Momentum-green.svg)](https://github.com/yourusername/signalflow)

---

## 🎯 **SYSTEM OVERVIEW**

SignalFlow is a sophisticated AI-powered trading system specifically designed for low-cap momentum trading. It combines advanced technical analysis, machine learning, and mathematical position sizing to identify and execute profitable trades in the $0.75-$10 price range.

### **🔥 Key Features**
- **Low-Cap Focus**: Optimized for $0.75-$10 momentum stocks
- **Enhanced Position Sizing**: 25-50% aggressive positions with Kelly Criterion
- **Williams %R + Momentum Multiplier**: Advanced momentum detection
- **AI Learning Engine**: Continuous improvement from trade outcomes
- **Interactive Telegram Bot**: Real-time trade notifications and approval
- **Sub-$3 Specialization**: Special handling for penny stock opportunities

### **📈 Performance Targets**
- **Profit Range**: 7-100% per trade
- **Win Rate**: 60-75% (enhanced entry timing)
- **Hold Time**: 2-10 days (momentum cycle optimization)
- **Position Sizing**: Mathematical optimization vs fixed percentages

---

## 🚀 **QUICK START**

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Configure Environment**
Copy `.env.template` to `.env` and add your API keys:
```bash
cp .env.template .env
# Edit .env with your API keys
```

### **3. Start Trading**
```bash
# Complete trading system (recommended)
python start_trading.py

# AI learning system with dashboard
python scripts/launch_ai_system.py

# Fast UI only
python scripts/launch_fast_ui.py
```

### **4. Access Interfaces**
- **Trading UI**: http://localhost:8501
- **AI Dashboard**: http://localhost:8001/docs
- **Telegram Bot**: Automatic notifications

---

## 📁 **PROJECT STRUCTURE**

```
signalflow/
├── 📄 start_trading.py          # Main entry point
├── 📄 enhanced_trading_ui.py    # Streamlit trading interface
├── 📄 main.py                   # Core system orchestrator
├── 📄 telegram_webhook.py       # Telegram bot handler
├── 📁 agents/                   # AI trading agents
│   ├── market_watcher_agent.py  # Market scanning
│   ├── trade_recommender_agent.py # Trade decisions
│   ├── sentiment_agent.py       # News analysis
│   └── execution_monitor_agent.py # Position monitoring
├── 📁 services/                 # Core business logic
│   ├── config.py               # Configuration management
│   ├── enhanced_position_sizer.py # Kelly Criterion sizing
│   ├── momentum_multiplier.py   # Explosive momentum detection
│   ├── williams_r_indicator.py  # Momentum oscillator
│   ├── ai_learning_engine.py    # Machine learning core
│   └── telegram_bot.py          # Interactive notifications
├── 📁 scripts/                  # Launch and utility scripts
├── 📁 tests/                    # System validation tests
├── 📁 docs/                     # Comprehensive documentation
├── 📁 deployment/               # Production deployment files
└── 📁 data/                     # Trading data and logs
```

---

## 🔧 **CONFIGURATION**

### **Trading Parameters**
- **Price Range**: $0.75 - $10.00 (low-cap focus)
- **Position Size**: 25% base, 50% maximum
- **Volume Filter**: 2M+ daily volume
- **Confidence Threshold**: 6.0+ (lowered for data collection)
- **Risk Management**: 15% max daily loss

### **Technical Indicators**
- **Williams %R**: Momentum oscillator (-80/-20 levels)
- **Bollinger Squeeze**: Volatility compression detection
- **Momentum Multiplier**: Explosive potential scoring (0-10)
- **Volume Confirmation**: 2x average volume requirement

### **AI Learning**
- **Decision Logging**: Every trade recorded with context
- **Adaptive Thresholds**: Confidence scores adjust based on performance
- **Pattern Recognition**: Successful setups automatically weighted higher
- **Continuous Improvement**: Daily learning cycles optimize strategy

---

## 📊 **SYSTEM CAPABILITIES**

### **Market Scanning**
- Real-time screening of 100+ stocks
- Gap detection (3-25% gaps)
- Float size filtering (10M-50M shares)
- Volume spike identification

### **Trade Analysis**
- Williams %R momentum scoring
- Bollinger Squeeze timing
- Momentum multiplier explosive detection
- AI-enhanced confidence scoring

### **Position Management**
- Kelly Criterion mathematical sizing
- Volatility-scaled risk adjustment
- Sub-$3 stock position boosts
- Dynamic profit target adjustment

### **Risk Management**
- Multi-layered stop loss protection
- Portfolio volatility targeting
- Sector exposure limits
- Correlation-aware allocation

---

## 🤖 **AI LEARNING FEATURES**

### **What the AI Learns**
- **Pattern Recognition**: Which setups lead to profitable trades
- **Market Conditions**: When strategies work best
- **Position Sizing**: Optimal allocation for different scenarios
- **Entry Timing**: Best moments to enter positions
- **Exit Strategy**: When to take profits or cut losses

### **Continuous Improvement**
- **Real-time Learning**: After each trade execution
- **Daily Analysis**: End-of-day performance review
- **Weekly Optimization**: Strategy effectiveness assessment
- **Adaptive Thresholds**: Confidence scores adjust automatically

---

## 📱 **TELEGRAM INTEGRATION**

### **Interactive Trading**
- Real-time signal notifications
- One-click trade execution buttons
- Position size adjustments (double/half)
- Trade status updates
- Performance summaries

### **Smart Notifications**
- Sub-$3 stock special alerts
- Momentum multiplier scores
- Volume spike confirmations
- Profit target adjustments

---

## 🧪 **TESTING & VALIDATION**

### **Run System Tests**
```bash
# Complete system validation
python tests/test_enhanced_momentum_system.py

# Individual component tests
python tests/test_polygon_api.py
python tests/test_mongodb_atlas.py
```

### **Paper Trading**
Start with paper trading (default) to:
- Collect 20-30 trades for AI learning
- Validate system performance
- Optimize parameters
- Build confidence before live trading

---

## 📈 **PERFORMANCE OPTIMIZATION**

### **Expected Improvements Over Time**
- **Week 1-2**: System learns patterns, calibrates thresholds
- **Week 3-4**: Performance stabilizes, improvements visible
- **Month 2+**: Full optimization benefits realized

### **Success Indicators**
- Momentum multiplier scores consistently above 6.0
- Williams %R oversold bounces with volume confirmation
- Position sizing recommendations align with Kelly Criterion
- AI confidence scores correlate with actual trade outcomes

---

## 🔒 **SECURITY & RELIABILITY**

### **API Security**
- Environment variable configuration
- No hardcoded credentials
- Secure API key management
- Rate limiting compliance

### **Error Handling**
- Graceful degradation on component failure
- Automatic fallback to basic indicators
- Comprehensive logging and monitoring
- Connection resilience and retry logic

---

## 📚 **DOCUMENTATION**

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Start Scripts Guide](START_SCRIPTS.md)** - Launch options and workflows
- **[Enhanced Features](docs/ENHANCED_MOMENTUM_SYSTEM_COMPLETE.md)** - Implementation details

---

## 🤝 **SUPPORT**

### **Common Issues**
1. **API Errors**: Check API keys and rate limits
2. **No Signals**: Verify market hours and screening criteria
3. **UI Not Loading**: Wait 60 seconds, check port 8501
4. **Telegram Issues**: Verify bot token and chat ID

### **System Health**
```bash
# Check system status
python -c "from services.config import Config; print('✅ Config OK')"

# View real-time logs
tail -f logs/signalflow.log

# Test momentum detection
python tests/test_enhanced_momentum_system.py
```

---

## ⚠️ **RISK DISCLAIMER**

This software is for educational and research purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results. Always start with paper trading and use proper risk management.

---

## 📄 **LICENSE**

MIT License - see [LICENSE](LICENSE) file for details.

---

**🎯 Ready to capture explosive low-cap momentum opportunities? Start with `python start_trading.py`!**

*SignalFlow v2.0 - Enhanced Low-Cap Momentum Trading System*