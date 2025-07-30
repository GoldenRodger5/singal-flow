# Frontend - Vercel Deployment (Next.js Dashboard)

## Directory Structure
```
frontend/
├── app/                   # Next.js 14 App Router
│   ├── api/              # API routes (proxy to Railway)
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Main dashboard page
│   └── globals.css       # Global styles
├── components/           # React components
│   ├── SystemOverview.tsx
│   ├── TradingPerformance.tsx
│   ├── Holdings.tsx
│   ├── AIAnalysis.tsx
│   ├── RealtimeCharts.tsx
│   ├── ControlPanel.tsx
│   └── EnhancedControlPanel.tsx
├── package.json          # Dependencies and scripts
├── next.config.js        # Next.js configuration
├── tailwind.config.js    # Tailwind CSS config
├── tsconfig.json         # TypeScript configuration
└── postcss.config.js     # PostCSS configuration
```

## Package.json Scripts
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build", 
    "start": "next start",
    "lint": "next lint"
  }
}
```

## Vercel Environment Variables
```env
RAILWAY_TRADING_URL=https://web-production-3e19d.up.railway.app
MONGODB_URL=your_mongodb_connection_string_here
OPENAI_API_KEY=your_openai_api_key_here
ALPACA_API_KEY=your_alpaca_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
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
