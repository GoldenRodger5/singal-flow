#!/bin/bash

# Signal Flow - Production Trading Dashboard Launcher
echo "🚀 Starting Signal Flow Production Trading Dashboard..."
echo "=============================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check if streamlit is installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "📦 Installing Streamlit..."
    python3 -m pip install streamlit plotly pandas
fi

# Set environment variables for backend integration
export PYTHONPATH="$SCRIPT_DIR/backend:$PYTHONPATH"

echo "✅ Environment configured"
echo "📊 Dashboard will be available at: http://localhost:8501"
echo "⚠️  WARNING: This is LIVE TRADING - All actions are REAL!"
echo ""
echo "🎛️  Controls:"
echo "   - Use sidebar for quick actions"
echo "   - Trading tab for buy/sell orders"
echo "   - Portfolio tab to manage positions"
echo "   - AI tab for predictions"
echo "   - Config tab for settings"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo "=============================================="

# Launch the dashboard
python3 -m streamlit run production_dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --theme.backgroundColor="#0E1117" \
    --theme.secondaryBackgroundColor="#262730" \
    --theme.primaryColor="#FF4B4B" \
    --theme.textColor="#FAFAFA"
