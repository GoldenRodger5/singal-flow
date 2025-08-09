#!/bin/bash

# Frontend Dashboard Deployment Script
# Deploys the updated frontend to Vercel

echo "🚀 Deploying Signal Flow Dashboard to Vercel..."
echo "================================================="

# Check if we're in the project root
if [ ! -d "frontend" ]; then
    echo "❌ Error: Must be run from project root directory"
    exit 1
fi

# Navigate to frontend directory
cd frontend

echo "📦 Installing dependencies..."
npm install

echo "🔧 Building the application..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    echo "🌐 Deploying to Vercel..."
    npx vercel --prod --confirm
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 SUCCESS! Dashboard deployed successfully"
        echo "================================================="
        echo "🔗 Dashboard URL: https://signal-flow-dashboard.vercel.app"
        echo "🔗 Backend API: https://web-production-3e19d.up.railway.app"
        echo ""
        echo "📊 API Endpoints now available:"
        echo "   • /api/holdings - Portfolio holdings"
        echo "   • /api/account - Account information"
        echo "   • /api/dashboard/market/pulse - Market overview"
        echo "   • /api/dashboard/ai/signals - AI trading signals"
        echo "   • /api/dashboard/ai/learning-metrics - AI learning metrics"
        echo "   • /api/config/system - System configuration"
        echo "   • /api/config/status - System status"
        echo ""
        echo "✅ Frontend should now connect properly to backend!"
    else
        echo "❌ Deployment failed"
        exit 1
    fi
else
    echo "❌ Build failed"
    exit 1
fi
