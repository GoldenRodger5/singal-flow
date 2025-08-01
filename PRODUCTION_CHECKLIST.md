# 🚀 Signal Flow - Production Deployment Checklist

## Pre-Deployment Requirements ✅

### 1. Environment Variables (Backend - Railway)
- [x] `ALPACA_API_KEY` - Your Alpaca API key
- [x] `ALPACA_SECRET_KEY` - Your Alpaca secret key  
- [x] `ALPACA_BASE_URL` - Set to paper trading URL for safety
- [x] `MONGODB_URL` - MongoDB Atlas connection string
- [x] `OPENAI_API_KEY` - OpenAI API key for AI features
- [ ] `POLYGON_API_KEY` - Market data (optional)

### 2. Environment Variables (Frontend - Vercel)  
- [x] `NEXT_PUBLIC_BACKEND_URL` - Railway backend URL
- [x] Set to: `https://web-production-3e19d.up.railway.app`

### 3. Trading Account Setup
- [ ] Alpaca account verified and funded
- [ ] **IMPORTANT**: Confirm paper trading vs live trading mode
- [ ] Risk management limits configured
- [ ] Emergency contacts set up

## Deployment Steps 

### Backend (Railway)
1. Push code to repository
2. Railway auto-deploys from `backend/scripts/production_api.py`
3. Verify health endpoint: `https://your-railway-url.up.railway.app/health`
4. Check trading API connectivity: `/api/account`

### Frontend (Vercel)
1. Push code to repository  
2. Vercel auto-deploys Next.js app
3. Verify dashboard loads and shows backend connection
4. Test control panel functionality

## Safety Checklist 🛡️

- [ ] **CRITICAL**: Verify paper trading mode is enabled
- [ ] Emergency stop button tested and working
- [ ] Position size limits configured appropriately
- [ ] Risk management rules activated
- [ ] Monitoring and alerts set up
- [ ] Backup plans in place

## Post-Deployment Verification

### Functional Tests
- [ ] Dashboard loads without errors
- [ ] System status shows all green
- [ ] Control panel actions work (test sync data first)
- [ ] Trading data displays correctly
- [ ] Emergency stop functionality verified

### Performance Tests
- [ ] Real-time data updates every 15 seconds
- [ ] Backend responds within 2 seconds
- [ ] Error handling works properly
- [ ] Health monitoring active

## Production Monitoring

### Key Metrics to Watch
- Account balance and positions
- System uptime and health
- API response times
- Error rates and failures
- Trading performance

### Alerts Setup
- Low account balance
- System downtime
- API failures
- Unusual trading activity
- Emergency stop triggers

## Market Hours Considerations 

### Regular Trading Hours
- **Pre-market**: 4:00 AM - 9:30 AM ET
- **Market**: 9:30 AM - 4:00 PM ET  
- **After-hours**: 4:00 PM - 8:00 PM ET

### System Behavior
- More frequent updates during market hours (15 seconds)
- Market status indicator in dashboard
- Automated trading follows market schedule

## Emergency Procedures 🚨

### If Something Goes Wrong
1. **FIRST**: Click Emergency Stop in Control Panel
2. **SECOND**: Check Alpaca dashboard directly
3. **THIRD**: Contact your broker if needed
4. **FOURTH**: Review system logs

### Emergency Contacts
- Alpaca Support: support@alpaca.markets
- Your broker contact information
- System administrator contact

## Notes
- All times are in Eastern Time (ET)
- Paper trading recommended for initial deployment
- Monitor closely during first few trading sessions
- Keep emergency procedures easily accessible

---
**Remember**: This system handles real money. Always prioritize safety and proper testing.
