#!/bin/bash

# Railway Quick Deploy Script
# Run this to prepare your project for Railway deployment

echo "🚀 Preparing Signal Flow for Railway Deployment..."

# Create logs directory
mkdir -p logs

# Check if git repo is initialized
if [ ! -d ".git" ]; then
    echo "📝 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit - Signal Flow Trading Bot"
fi

# Check if we have a remote
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "⚠️  No git remote found."
    echo "📋 Please push this code to GitHub first:"
    echo ""
    echo "1. Create a new repository on GitHub"
    echo "2. Run these commands:"
    echo "   git remote add origin https://github.com/yourusername/singal-flow.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "3. Then deploy to Railway from your GitHub repo"
else
    echo "✅ Git repository is ready"
    echo "📤 Push any changes to GitHub:"
    git add .
    git commit -m "Railway deployment configuration" || echo "No changes to commit"
    git push
fi

echo ""
echo "🎯 Railway Deployment Checklist:"
echo "✅ railway.json - Railway configuration"
echo "✅ Procfile - Process configuration"  
echo "✅ requirements.txt - Python dependencies"
echo "✅ railway_start.py - Cloud entry point"
echo "✅ railway.env.template - Environment variables template"
echo "✅ RAILWAY_DEPLOYMENT.md - Setup instructions"
echo ""
echo "📋 Next Steps:"
echo "1. Push this code to GitHub"
echo "2. Go to railway.app and deploy from GitHub"
echo "3. Add environment variables from railway.env.template"
echo "4. Set start command: python railway_start.py"
echo ""
echo "🔗 Full instructions: See RAILWAY_DEPLOYMENT.md"
