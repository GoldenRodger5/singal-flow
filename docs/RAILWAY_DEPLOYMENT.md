# Railway Deployment Guide for Signal Flow Trading Bot

## 🚀 Complete Railway Setup Instructions

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended) or email
3. Verify your account

### Step 2: Deploy from GitHub
1. **Connect your repository:**
   - Click "New Project" 
   - Select "Deploy from GitHub repo"
   - Choose your `singal-flow` repository
   - Click "Deploy Now"

2. **Railway will automatically:**
   - Detect it's a Python project
   - Install requirements.txt
   - Try to start the application

### Step 3: Configure Environment Variables
1. **In your Railway dashboard:**
   - Click on your deployed project
   - Go to "Variables" tab
   - Add each variable from `railway.env.template`:

**Required Variables (get from your local .env file):**
```
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ALPACA_API_KEY=your-alpaca-api-key-here
ALPACA_SECRET=your-alpaca-secret-here
POLYGON_API_KEY=your-polygon-api-key-here
TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
WHATSAPP_FROM=whatsapp:+1234567890
WHATSAPP_TO=whatsapp:+1234567890
```

**System Configuration:**
```
SYSTEM_MODE=paper_trading
AUTOMATION_MODE=paper_trading
LOG_LEVEL=INFO
RAILWAY_DEPLOYMENT=true
```

### Step 4: Set Start Command
1. **In Railway dashboard:**
   - Go to "Settings" tab
   - Find "Start Command" section
   - Set to: `python railway_start.py`

### Step 5: Configure Health Checks
1. **In Settings:**
   - Health Check Path: `/health`
   - Health Check Timeout: `300`
   - Enable automatic restarts

### Step 6: Deploy and Monitor
1. **Click "Deploy"** - Railway will rebuild with new settings
2. **Monitor logs:**
   - Go to "Deployments" tab
   - Click on latest deployment
   - Watch real-time logs

## 📊 What You'll See

### Successful Deployment Logs:
```
🌟 Signal Flow - Railway Deployment Starting
💚 Health check server started on port 8000
🚀 Starting Signal Flow Trading System on Railway
📅 Start time: 2025-07-29 10:30:00
🔄 Mode: Paper Trading (Safe)
✅ Trading system initialized successfully
🎯 System will run continuously until stopped
```

### Health Check URLs:
- **Main**: `https://your-app.railway.app/`
- **Health**: `https://your-app.railway.app/health`
- **Status**: `https://your-app.railway.app/status`

## 🎛️ Managing Your Bot

### View Performance:
```bash
# Check if bot is running
curl https://your-app.railway.app/health

# View trading status
curl https://your-app.railway.app/status
```

### Access Logs:
1. Railway Dashboard → Deployments → View Logs
2. Real-time monitoring of all trading activity

### WhatsApp Notifications:
- You'll receive trade alerts on WhatsApp
- System status updates
- Error notifications

## 💰 Costs

### Railway Free Tier:
- **$5 credit/month** (usually covers small trading bots)
- **500 hours/month** execution time
- **1GB RAM** 
- **1 CPU**

### If you exceed free tier:
- **~$3-8/month** for continuous operation
- Much cheaper than VPS alternatives

## 🛡️ Safety Features

### Automatic Protections:
- Paper trading only (no real money)
- Daily loss limits (2%)
- Max trades per day (25)
- Automatic restarts on failures

### Manual Controls:
- Stop anytime via Railway dashboard
- Change environment variables instantly
- View all activity in real-time

## 🔧 Troubleshooting

### Common Issues:

**1. Deployment Fails:**
- Check all environment variables are set
- Verify API keys are correct
- Review build logs for missing dependencies

**2. Health Check Fails:**
- Wait 2-3 minutes for full startup
- Check if port 8000 is accessible
- Review application logs

**3. Trading Not Working:**
- Verify ALPACA_BASE_URL=https://paper-api.alpaca.markets
- Check SYSTEM_MODE=paper_trading
- Ensure market hours (9:30 AM - 4:00 PM EST)

### Get Help:
- Railway logs show detailed error messages
- WhatsApp notifications alert you to issues
- Health endpoints provide system status

## ✅ Success Checklist

- [ ] Railway account created
- [ ] Repository connected and deployed
- [ ] All environment variables added
- [ ] Start command set to `python railway_start.py`
- [ ] Health check returning 200 OK
- [ ] WhatsApp test message received
- [ ] Logs showing trading system startup

**Your bot will now run 24/7 and trade automatically in paper mode!** 🎯
