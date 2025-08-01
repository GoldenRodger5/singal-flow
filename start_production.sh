#!/bin/bash

# Signal Flow Trading System - Production Startup Script
# This script ensures all components are ready for market trading

echo "🚀 Starting Signal Flow Trading System for Live Market Trading"
echo "======================================================================="

# Check if market is open (basic check)
current_hour=$(date +%H)
current_day=$(date +%u)  # 1=Monday, 7=Sunday

if [ $current_day -ge 6 ] || [ $current_hour -lt 9 ] || [ $current_hour -gt 16 ]; then
    echo "⚠️  WARNING: Market may be closed. Current time: $(date)"
    echo "   - Regular market hours: Monday-Friday 9:30 AM - 4:00 PM ET"
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Startup cancelled"
        exit 1
    fi
fi

echo "✅ Pre-flight checks passed"
echo

# Backend startup
echo "🔧 Starting Backend API Server..."
cd backend
python scripts/production_api.py &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to initialize..."
sleep 10

# Check backend health
echo "🏥 Checking backend health..."
curl -f http://localhost:8000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Backend is healthy and ready"
else
    echo "❌ Backend health check failed"
    kill $BACKEND_PID
    exit 1
fi

echo
echo "🎯 Signal Flow Trading System is LIVE and ready for market trading!"
echo "   - Backend API: http://localhost:8000"
echo "   - Health Check: http://localhost:8000/health"
echo "   - Control Panel: Available in frontend"
echo
echo "📊 Access your trading dashboard at the frontend URL"
echo "⚠️  IMPORTANT: This is connected to live trading - use emergency stop if needed"
echo

# Keep the backend running
wait $BACKEND_PID
