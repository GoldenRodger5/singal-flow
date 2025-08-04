# 🚀 RAILWAY ENVIRONMENT VARIABLES SETUP

## CRITICAL: Configure these environment variables in Railway Dashboard

Go to your Railway project dashboard and add these environment variables:

### 1. Database Configuration
```
MONGODB_URL=mongodb+srv://your_username:your_password@your_cluster.mongodb.net/your_database?retryWrites=true&w=majority
```

### 2. Trading API Keys
```
POLYGON_API_KEY=your_polygon_api_key_here
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET=your_alpaca_secret_key_here
```

### 3. Telegram Notifications
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### 4. Optional Environment Settings
```
ENVIRONMENT=production
PORT=8000
```

## 📋 HOW TO ADD THESE TO RAILWAY:

1. Go to your Railway project dashboard
2. Click on your service/project
3. Go to "Variables" tab
4. Click "New Variable" for each one above
5. Copy the exact variable name and add your actual values
6. Click "Deploy" to restart with new environment variables

## ⚠️ IMPORTANT NOTES:
- Replace all placeholder values with your actual API keys
- MONGODB_URL should be your actual MongoDB Atlas connection string
- Without these variables, the deployment WILL FAIL
- Keep these values secure and never commit them to Git

## 🔍 VERIFICATION:
After adding all variables, the Railway deployment should succeed and all services should initialize properly.
