# Signal Flow - Production Deployment Guide

## 🚀 Production Deployment Status

### Backend (Railway) ✅
- **URL**: https://web-production-3e19d.up.railway.app
- **Status**: Deploying with new API endpoints
- **Mode**: Paper Trading (Safe)

### Frontend (Vercel) 🚀
- **Ready for deployment**
- **Framework**: Next.js 14
- **Status**: Production build successful

## 📋 Deployment Instructions

### Railway Backend Deployment

The backend is configured to auto-deploy from GitHub. Files added:
- `Procfile` - Process definition
- `railway.json` - Build/deploy configuration  
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version
- `start.py` - Deployment entry point

**API Endpoints:**
- `/health` - Health check
- `/api/holdings` - Real portfolio positions from Alpaca
- `/api/portfolio` - Portfolio summary and account info

### Vercel Frontend Deployment

**Option 1: Automatic (Recommended)**
1. Connect GitHub repository to Vercel
2. Set root directory to `frontend/`
3. Environment variable: `NEXT_PUBLIC_BACKEND_URL=https://web-production-3e19d.up.railway.app`
4. Deploy automatically

**Option 2: Manual**
```bash
cd frontend
npm install
npm run build
npx vercel --prod
```

## 🔧 Environment Configuration

### Backend (Railway)
```env
ALPACA_API_KEY=YOUR_ALPACA_KEY
ALPACA_SECRET=YOUR_ALPACA_SECRET
ALPACA_BASE_URL=https://paper-api.alpaca.markets
OPENAI_API_KEY=YOUR_OPENAI_KEY
POLYGON_API_KEY=YOUR_POLYGON_KEY
MONGODB_URL=YOUR_MONGODB_URL
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_BACKEND_URL=https://web-production-3e19d.up.railway.app
```

## ✅ Production Checklist

- [x] Railway backend configured with Procfile
- [x] API endpoints for real data (/api/holdings, /api/portfolio)
- [x] Frontend build successful (no TypeScript errors)
- [x] Removed all mock/test data from dashboard
- [x] Error handling for API unavailability
- [x] Production environment files
- [x] Vercel deployment configuration

## 🎯 Real Data Connections

### Current Status:
- **Holdings**: Fetched from Alpaca paper trading account
- **Portfolio**: Real account data (buying power, equity, etc.)
- **No Mock Data**: All hardcoded test data removed
- **Clean State**: Shows empty when no positions (expected after MongoDB purge)

### Expected Behavior:
- Dashboard shows "No holdings found" until AI system creates new trades
- Performance charts use real portfolio value
- All data comes from live Alpaca API
- System operates in paper trading mode for safety

## 🔄 Deployment Status Check

```bash
# Check Railway backend
curl https://web-production-3e19d.up.railway.app/health

# Check API endpoints (once deployed)
curl https://web-production-3e19d.up.railway.app/api/holdings
curl https://web-production-3e19d.up.railway.app/api/portfolio
```

## 📱 Dashboard Features

- **System Overview**: Health monitoring
- **Trading Performance**: Real portfolio metrics
- **Holdings**: Live positions from Alpaca
- **AI Analysis**: Market sentiment and insights
- **Control Panel**: System configuration
- **Enhanced Mode**: Advanced features toggle

All components now use real data from the Railway backend API.
