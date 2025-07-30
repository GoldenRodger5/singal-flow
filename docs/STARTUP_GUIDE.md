# 🚀 Signal Flow Trading System - Startup Guide

## ✅ **SINGLE ENTRY POINT**

**Use ONLY this command to start the complete system:**

```bash
python production_api.py
```

## 🎯 **What This Starts**

When you run `production_api.py`, it automatically starts:

✅ **FastAPI Production Server** (Port 8000)  
✅ **Complete AI Trading System** (All 6 agents)  
✅ **Health Monitoring** & WebSocket updates  
✅ **Database Logging** & Trade tracking  
✅ **Telegram Notifications** & Alerts  
✅ **Real-time Market Scanning** every minute  

## 📊 **Access Points**

- **API**: http://localhost:8000
- **Health Dashboard**: http://localhost:8000/health/detailed  
- **WebSocket**: ws://localhost:8000/ws/health
- **System Status**: http://localhost:8000/system/status

## 🗑️ **Deprecated Files (Don't Use)**

These files are **OBSOLETE** and should not be used:
- ~~start_full_automation.py~~
- ~~start_webhook.py~~
- ~~start_enhanced.py~~
- ~~start_trading.py~~
- ~~start_trading_system.py~~
- ~~start_local_trading.py~~
- ~~run_production.py~~
- ~~launch_production.py~~
- ~~start.py~~ (simple wrapper)

## 🎯 **Current Configuration**

**For Testing** (currently active):
- Confidence threshold: **5.5/10** (lowered from 7.0)
- Sentiment analysis: **DISABLED**
- Sector limit: **6 stocks** per sector (increased from 3)
- Risk/Reward ratio: **1.8:1** (lowered from 2.0)
- Max daily trades: **8** (increased from 5)

## 📱 **Getting Notifications**

The system will automatically:
1. Scan market every minute
2. Find setups using AI analysis  
3. Send Telegram alerts for 5.5+ confidence trades
4. Log all decisions to database

**Just run the system and wait for alerts!**
