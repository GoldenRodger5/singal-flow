# Backend - Railway Deployment (Python Trading System)

## Directory Structure
```
backend/
├── main.py                 # Trading system orchestrator
├── railway_start.py        # Railway deployment entry point
├── agents/                 # AI trading agents
├── services/              # Trading services (Alpaca, MongoDB, etc.)
├── utils/                 # Utilities and logging
├── data/                  # Trading data and configs
├── tests/                 # Test files
├── requirements.txt       # Python dependencies
├── railway.json          # Railway deployment config
└── Procfile              # Railway startup commands
```

## Environment Variables (.env)
```env
# LLM APIs
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Trading APIs
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
POLYGON_API_KEY=your_polygon_api_key_here

# Database
MONGODB_URL=mongodb+srv://isaacmineo:4Pb2VGg4lThvzozF@signalflow.xd8mfgw.mongodb.net/?retryWrites=true&w=majority&appName=SignalFlow
MONGODB_NAME=signal_flow_trading

# Notifications
TELEGRAM_BOT_TOKEN=8413143996:AAFS1o9P5rXtVw0-3N3gseDoMaGhm62Mdf4
TELEGRAM_CHAT_ID=7546286152

# System Configuration
PAPER_TRADING=true
AUTO_TRADING_ENABLED=true
ENVIRONMENT=production
```

## Railway Deployment Commands
```bash
# Start command (defined in Procfile)
python railway_start.py

# Health check endpoint
https://web-production-3e19d.up.railway.app/health
```

## API Endpoints Available
- GET / - Root status
- GET /health - Health check
- GET /status - Trading system status  
- GET /positions - Current positions
- GET /account - Account information
- GET /trades - Recent trades
- GET /performance - Performance metrics
- GET /ai-predictions - AI predictions
- GET /market-sentiment - Market sentiment
