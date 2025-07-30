# Signal Flow Dashboard

A Next.js dashboard for monitoring the Signal Flow AI Trading System.

## Features

- **Real-time System Overview**: Monitor system status, database connectivity, and automation status
- **Trading Performance**: View portfolio performance, P&L, and trading metrics
- **Holdings Management**: Track current positions with enhanced AI analysis
- **AI Analysis**: Real-time market sentiment and AI-powered insights
- **AI Learning Dashboard**: Monitor model performance and learning progress
- **Realtime Charts**: Live price charts with multiple symbol support
- **Control Panel**: Manage trading system settings and configurations
- **Enhanced Mode**: Toggle between basic and advanced features

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Environment Variables

Create a `.env.local` file:

```bash
NEXT_PUBLIC_BACKEND_URL=https://web-production-3e19d.up.railway.app
```

## Build & Deployment Commands

### Local Development
```bash
cd frontend
npm install
npm run dev        # Starts dev server on http://localhost:3000
```

### Production Build
```bash
cd frontend
npm run build      # Creates optimized production build
npm run start      # Starts production server locally
```

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
cd frontend
vercel --prod
```

## Vercel Configuration (vercel.json)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/next"
    }
  ],
  "env": {
    "RAILWAY_TRADING_URL": "@railway-trading-url",
    "MONGODB_URL": "@mongodb-url",
    "OPENAI_API_KEY": "@openai-api-key",
    "ALPACA_API_KEY": "@alpaca-api-key",
    "POLYGON_API_KEY": "@polygon-api-key"
  },
  "functions": {
    "app/api/**/*.ts": {
      "runtime": "nodejs18.x"
    }
  }
}
```

## Dashboard Features
- 📊 Real-time system monitoring
- 📈 Live trading performance
- 💼 Current holdings display  
- 🤖 AI predictions and sentiment
- 📉 Interactive price charts
- ⚙️ Enhanced trading controls
- 🔄 30-second data updates
- 📱 Mobile responsive design

## Data Sources
- **Railway Backend**: System status and coordination
- **Alpaca API**: Live trading data and positions
- **MongoDB Atlas**: AI predictions and historical data
- **Real-time Updates**: Every 30 seconds
