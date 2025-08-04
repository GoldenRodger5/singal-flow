# 🚨 CRITICAL RAILWAY ENVIRONMENT VARIABLES FIX

## ISSUE: Worker deployment failed due to missing Alpaca environment variables

The Alpaca Python SDK expects these specific environment variable names:

### ✅ REQUIRED ADDITIONS TO RAILWAY ENVIRONMENT VARIABLES:

```bash
# These are the standard Alpaca SDK environment variable names
APCA_API_KEY_ID=PK0AXIMBK2QK7S7OWZOA
APCA_API_SECRET_KEY=UUdh7kkklfhZXFCKhKn4iGinKB6tDOQZhpeLVnOF
APCA_API_BASE_URL=https://paper-api.alpaca.markets

# Keep the existing ones for compatibility
ALPACA_API_KEY=PK0AXIMBK2QK7S7OWZOA
ALPACA_SECRET=UUdh7kkklfhZXFCKhKn4iGinKB6tDOQZhpeLVnOF
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### 🔧 HOW TO FIX IN RAILWAY:

1. **Go to your Railway project dashboard**
2. **Click on your service**
3. **Go to "Variables" tab** 
4. **Add these 3 new environment variables:**
   - `APCA_API_KEY_ID` = `PK0AXIMBK2QK7S7OWZOA`
   - `APCA_API_SECRET_KEY` = `UUdh7kkklfhZXFCKhKn4iGinKB6tDOQZhpeLVnOF`
   - `APCA_API_BASE_URL` = `https://paper-api.alpaca.markets`

5. **Click "Deploy" to restart with new variables**

### ⚡ ALSO FIXED:
- Removed import-time initialization of AlpacaTradingService
- Made trading service use lazy loading like database manager
- All trading_service calls now use get_trading_service()

### 🎯 RESULT:
After adding these environment variables, both the web and worker deployments should succeed on Railway.

### 🔍 VERIFICATION:
The deployment logs should show:
- "✅ Trading service connected. Account: [status]"
- No more "Key ID must be given to access Alpaca trade API" errors
