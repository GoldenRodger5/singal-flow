#!/bin/bash
# Production Startup Script for Signal Flow Trading System

echo "🚀 Starting Signal Flow Production API..."

# Set environment variables
export PYTHONPATH="/Users/isaacmineo/Main/projects/singal-flow/backend:$PYTHONPATH"
export ENVIRONMENT="production"
export LOG_LEVEL="INFO"

# Navigate to project directory
cd /Users/isaacmineo/Main/projects/singal-flow

# Start the production API server
python backend/scripts/production_api.py

echo "📊 Signal Flow API Server stopped"
