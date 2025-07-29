#!/usr/bin/env python3
"""
Install Missing Dependencies for Enhanced Features
Ensures all required packages are available for optimal performance.
"""
import subprocess
import sys
import os
from pathlib import Path

def install_package(package_name: str, description: str = ""):
    """Install a package with error handling."""
    try:
        print(f"📦 Installing {package_name}... {description}")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", package_name
        ])
        print(f"✅ {package_name} installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}: {e}")
        return False

def check_package(package_name: str):
    """Check if a package is already installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_enhanced_dependencies():
    """Install all dependencies for enhanced features."""
    print("🚀 Installing Enhanced Trading System Dependencies")
    print("=" * 60)
    
    # Core performance packages
    performance_packages = [
        ("numba>=0.56.0", "2-10x faster calculations"),
        ("scipy>=1.8.0", "Advanced statistical functions"),
        ("scikit-learn>=1.1.0", "Machine learning components"),
        ("pandas-ta>=0.3.14b", "Technical analysis library"),
    ]
    
    # Enhanced analysis packages
    analysis_packages = [
        ("plotly>=5.0.0", "Interactive charts"),
        ("dash>=2.0.0", "Web dashboard framework"),
        ("streamlit>=1.28.0", "Fast UI framework"),
        ("fastapi>=0.68.0", "API framework for services"),
        ("uvicorn>=0.15.0", "ASGI server"),
    ]
    
    # Data and connectivity packages
    data_packages = [
        ("yfinance>=0.1.87", "Market data provider"),
        ("alpaca-py>=0.7.0", "Alpaca trading API"),
        ("polygon-api-client>=0.2.0", "Polygon market data"),
        ("redis>=4.0.0", "Fast caching system"),
        ("sqlite3", "Built-in database"),
    ]
    
    # Optional acceleration packages
    optional_packages = [
        ("talib", "Traditional technical analysis (optional)"),
        ("cython", "Additional performance optimizations"),
        ("bottleneck", "Fast NumPy operations"),
        ("psutil", "System monitoring"),
    ]
    
    all_packages = performance_packages + analysis_packages + data_packages
    
    installed_count = 0
    failed_packages = []
    
    # Install core packages
    print("\n📊 Installing Core Performance Packages...")
    for package, description in performance_packages:
        package_name = package.split('>=')[0].split('==')[0]
        if not check_package(package_name) or package_name == "numba":  # Always try numba
            if install_package(package, description):
                installed_count += 1
            else:
                failed_packages.append(package)
        else:
            print(f"✅ {package_name} already installed")
    
    print("\n📈 Installing Analysis Packages...")
    for package, description in analysis_packages:
        package_name = package.split('>=')[0].split('==')[0]
        if not check_package(package_name):
            if install_package(package, description):
                installed_count += 1
            else:
                failed_packages.append(package)
        else:
            print(f"✅ {package_name} already installed")
    
    print("\n📡 Installing Data Packages...")
    for package, description in data_packages:
        if package == "sqlite3":  # Skip built-in
            continue
        package_name = package.split('>=')[0].split('==')[0]
        if not check_package(package_name):
            if install_package(package, description):
                installed_count += 1
            else:
                failed_packages.append(package)
        else:
            print(f"✅ {package_name} already installed")
    
    # Try optional packages
    print("\n🔧 Installing Optional Packages...")
    for package, description in optional_packages:
        package_name = package.split('>=')[0].split('==')[0]
        if not check_package(package_name):
            print(f"📦 Attempting to install {package}... {description}")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✅ {package_name} installed successfully!")
            except:
                print(f"⚠️  {package_name} installation failed (optional - continuing)")
        else:
            print(f"✅ {package_name} already installed")
    
    # Test installations
    print("\n🧪 Testing Enhanced Feature Availability...")
    
    # Test Numba
    try:
        import numba
        print("✅ Numba acceleration: AVAILABLE (2-10x performance boost)")
    except ImportError:
        print("❌ Numba acceleration: NOT AVAILABLE (standard performance)")
    
    # Test pandas-ta
    try:
        import pandas_ta
        print("✅ Technical analysis library: AVAILABLE")
    except ImportError:
        print("❌ Technical analysis library: NOT AVAILABLE")
    
    # Test enhanced features
    try:
        from services.enhanced_indicators import EnhancedIndicators
        print("✅ Enhanced indicators: AVAILABLE")
    except ImportError:
        print("❌ Enhanced indicators: NOT AVAILABLE")
    
    try:
        from services.market_regime_detector import MarketRegimeDetector
        print("✅ Market regime detection: AVAILABLE")
    except ImportError:
        print("❌ Market regime detection: NOT AVAILABLE")
    
    try:
        from services.enhanced_position_sizer import EnhancedPositionSizer
        print("✅ Kelly Criterion position sizing: AVAILABLE")
    except ImportError:
        print("❌ Kelly Criterion position sizing: NOT AVAILABLE")
    
    # Summary
    print("\n" + "="*60)
    print("📋 INSTALLATION SUMMARY")
    print("="*60)
    print(f"✅ Successfully installed: {installed_count} packages")
    
    if failed_packages:
        print(f"❌ Failed to install: {len(failed_packages)} packages")
        for package in failed_packages:
            print(f"   - {package}")
    
    if not failed_packages:
        print("🎉 All enhanced features are ready!")
        print("🚀 Your trading system has maximum performance capabilities!")
    else:
        print("⚠️  Some packages failed to install.")
        print("💡 The system will work with reduced functionality.")
    
    # Update .env with acceleration status
    try:
        import numba
        print("\n⚡ Updating .env with acceleration settings...")
        update_env_acceleration(True)
    except ImportError:
        print("\n⚠️  Updating .env - acceleration not available...")
        update_env_acceleration(False)
    
    return len(failed_packages) == 0

def update_env_acceleration(numba_available: bool):
    """Update .env file with acceleration status."""
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update or add acceleration setting
        if "USE_NUMBA_ACCELERATION" in content:
            # Update existing setting
            import re
            content = re.sub(
                r'USE_NUMBA_ACCELERATION=.*',
                f'USE_NUMBA_ACCELERATION={str(numba_available).lower()}',
                content
            )
        else:
            # Add new setting
            content += f"\nUSE_NUMBA_ACCELERATION={str(numba_available).lower()}\n"
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated .env: USE_NUMBA_ACCELERATION={str(numba_available).lower()}")

def main():
    """Main installation function."""
    print("🎯 Enhanced Trading System - Dependency Installation")
    print("This will install packages for maximum performance and functionality.")
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    
    print("✅ Python version compatible:", sys.version.split()[0])
    
    # Check pip
    try:
        import pip
        print("✅ pip available")
    except ImportError:
        print("❌ pip not available. Please install pip first.")
        return False
    
    # Start installation
    success = install_enhanced_dependencies()
    
    if success:
        print("\n🎉 Installation completed successfully!")
        print("🚀 Run your trading system with full enhanced features!")
        print("\n💡 Next steps:")
        print("   1. python main.py - Run the trading system")
        print("   2. python start_trading.py - Launch fast UI")
        print("   3. python test_enhanced_system.py - Test all features")
    else:
        print("\n⚠️  Installation completed with some issues.")
        print("💡 Your system will still work with reduced functionality.")
    
    return success

if __name__ == "__main__":
    main()
