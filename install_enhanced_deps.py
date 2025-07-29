#!/usr/bin/env python3
"""
Install and configure enhanced dependencies for Signal Flow Trading System.
"""
import subprocess
import sys
import os
from pathlib import Path

def install_package(package):
    """Install a Python package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    """Install all required packages for enhanced trading system."""
    print("🚀 Installing Enhanced Signal Flow Dependencies")
    print("=" * 50)
    
    # Enhanced dependencies for modern trading algorithms
    packages = [
        "numpy>=1.21.0",
        "pandas>=1.3.0", 
        "scipy>=1.7.0",
        "scikit-learn>=1.0.0",
        "pandas-ta>=0.3.14b",  # Technical analysis library
        "loguru>=0.6.0",
        "python-dotenv>=0.19.0",
        "aiohttp>=3.8.0",
        "asyncio",
        "dataclasses; python_version<'3.7'",
    ]
    
    # Optional but recommended for better performance
    optional_packages = [
        "numba>=0.56.0",  # For faster calculations
        "cython>=0.29.0",  # For compiled code speedup
        "bottleneck>=1.3.0",  # For faster pandas operations
    ]
    
    success_count = 0
    total_packages = len(packages)
    
    print("Installing core dependencies...")
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 Core Dependencies: {success_count}/{total_packages} installed successfully")
    
    # Install optional packages
    print("\nInstalling optional performance packages...")
    optional_success = 0
    for package in optional_packages:
        if install_package(package):
            optional_success += 1
    
    print(f"📈 Optional Dependencies: {optional_success}/{len(optional_packages)} installed successfully")
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"📁 Created data directory: {data_dir.absolute()}")
    
    # Note about TA-Lib
    print("\n" + "="*50)
    print("📋 IMPORTANT NOTES:")
    print("="*50)
    print("1. Some enhanced indicators use pandas-ta which is included")
    print("2. For best performance, consider installing TA-Lib:")
    print("   - macOS: brew install ta-lib && pip install TA-Lib")
    print("   - Ubuntu: sudo apt-get install libta-lib-dev && pip install TA-Lib")
    print("   - Windows: Download from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib")
    print("3. The system will work without TA-Lib using pandas-ta fallbacks")
    print("4. Enhanced indicators provide modern alternatives to RSI/MACD")
    print("5. Regime detection enables adaptive thresholds")
    print("6. Enhanced position sizing implements Kelly Criterion and volatility scaling")
    
    print(f"\n✨ Enhanced Signal Flow setup complete!")
    print(f"   Core success rate: {success_count/total_packages*100:.1f}%")
    print(f"   Ready for optimized trading with regime awareness!")

if __name__ == "__main__":
    main()
