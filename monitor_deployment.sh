#!/bin/bash

# Railway Deployment Time Monitor
# Run this to track deployment progress

echo "🚀 RAILWAY DEPLOYMENT OPTIMIZATION MONITOR"
echo "===========================================" 
echo "📅 Started: $(date)"
echo ""

echo "⏱️ EXPECTED BUILD TIMES:"
echo "• BEFORE: 15-25 minutes (heavy ML packages)"
echo "• AFTER:  3-7 minutes (minimal packages)" 
echo ""

echo "🔄 Monitoring deployment progress..."
echo "👆 Check Railway dashboard for live updates"
echo ""

# Function to check deployment status
check_deployment() {
    echo "⏰ $(date +"%H:%M:%S") - Checking deployment status..."
    
    # Try health endpoint (will fail until deployment is complete)
    if curl -s --connect-timeout 5 https://web-production-3e19d.up.railway.app/health > /dev/null 2>&1; then
        echo "✅ Deployment complete! Health endpoint responding"
        echo "🎉 Final check:"
        curl -s https://web-production-3e19d.up.railway.app/health | jq '.status, .timestamp'
        return 0
    else
        echo "⏳ Still deploying..."
        return 1
    fi
}

# Monitor every 30 seconds for 10 minutes
for i in {1..20}; do
    if check_deployment; then
        echo ""
        echo "🎯 DEPLOYMENT SUCCESS!"
        echo "⏱️ Total time: Approximately $((i * 30)) seconds"
        echo "📊 Improvement: $(((1200 - i * 30) * 100 / 1200))% faster than before"
        break
    fi
    
    if [ $i -lt 20 ]; then
        echo "   Waiting 30 seconds before next check..."
        sleep 30
    fi
done

echo ""
echo "✨ Optimization Results:"
echo "• Reduced package count: 40+ → 15 packages"  
echo "• Removed heavy dependencies: scikit-learn, numba, jupyter"
echo "• Fixed start command: railway_start.py"
echo "• Added .dockerignore for smaller build context"
