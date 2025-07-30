#!/usr/bin/env python3
"""
Launch Enhanced Trading UI
"""

import sys
import os
import subprocess

def main():
    """Launch the enhanced trading UI with Streamlit."""
    
    print("🚀 Launching SignalFlow Enhanced Trading UI...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('enhanced_trading_ui.py'):
        print("❌ Error: enhanced_trading_ui.py not found!")
        print("Please run this script from the SignalFlow project directory.")
        return 1
    
    # Check if streamlit is available
    try:
        import streamlit
        print("✅ Streamlit found")
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'streamlit'])
    
    # Check if plotly is available
    try:
        import plotly
        print("✅ Plotly found")
    except ImportError:
        print("❌ Plotly not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'plotly'])
    
    # Launch the enhanced UI
    print("\n🎯 Starting Enhanced Trading UI...")
    print("📊 Enhanced features include:")
    print("   • Dynamic configuration controls")
    print("   • Current holdings dashboard")
    print("   • AI price predictions")
    print("   • Real-time settings updates")
    print("   • Enhanced position sizing")
    print("   • Live P&L tracking")
    print("\n🌐 Opening in your browser...")
    print("⚠️  Note: Close with Ctrl+C when done")
    print("=" * 50)
    
    # Run streamlit
    try:
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 
            'enhanced_trading_ui.py',
            '--server.port', '8501',
            '--server.address', 'localhost'
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Enhanced Trading UI stopped.")
        return 0
    except Exception as e:
        print(f"\n❌ Error launching UI: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
