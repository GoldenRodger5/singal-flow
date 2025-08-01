#!/bin/bash

echo "🚀 Signal Flow Deployment Verification"
echo "======================================"
echo ""

# Check Railway backend deployment
echo "🔍 Checking Railway Backend..."
RAILWAY_URL="https://web-production-3e19d.up.railway.app"

echo "   Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" "$RAILWAY_URL/health" -o /dev/null)
if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "   ✅ Backend health check: PASSED"
else
    echo "   ❌ Backend health check: FAILED (HTTP $HEALTH_RESPONSE)"
fi

echo "   Testing account endpoint..."
ACCOUNT_RESPONSE=$(curl -s -w "%{http_code}" "$RAILWAY_URL/api/account" -o /dev/null)
if [ "$ACCOUNT_RESPONSE" = "200" ]; then
    echo "   ✅ Account API: PASSED"
else
    echo "   ❌ Account API: FAILED (HTTP $ACCOUNT_RESPONSE)"
fi

echo "   Testing control status endpoint..."
CONTROL_RESPONSE=$(curl -s -w "%{http_code}" "$RAILWAY_URL/api/control/status" -o /dev/null)
if [ "$CONTROL_RESPONSE" = "200" ]; then
    echo "   ✅ Control Panel API: PASSED"
else
    echo "   ❌ Control Panel API: FAILED (HTTP $CONTROL_RESPONSE)"
fi

echo ""
echo "🎯 Deployment Status Summary:"
echo "   Backend URL: $RAILWAY_URL"
echo "   Frontend: Will be deployed to Vercel automatically"
echo ""
echo "📊 Next Steps:"
echo "   1. Check Railway dashboard for deployment logs"
echo "   2. Verify Vercel deployment completes"
echo "   3. Test frontend dashboard functionality"
echo "   4. Verify control panel operations"
echo ""
echo "🛡️ Safety Reminder:"
echo "   - System is in PAPER TRADING mode"
echo "   - Emergency stop is available in control panel"
echo "   - Monitor positions closely"
echo ""
echo "Market is open - Ready to trade! 📈"
