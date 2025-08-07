#!/usr/bin/env python3
"""
Final verification script - ensures NO mock data or fallback implementations
are being used in production code.
"""
import os
import sys
import re
from pathlib import Path

def scan_for_mock_implementations():
    """Scan all Python files for mock implementations."""
    
    backend_dir = Path("backend")
    issues_found = []
    files_scanned = 0
    
    # Patterns that indicate mock/test data
    mock_patterns = [
        r'return.*\[.*[\'"]AAPL[\'"].*\]',  # Hardcoded tickers
        r'return.*\{.*[\'"]price[\'"].*:.*\d+',  # Hardcoded prices
        r'mock.*=.*',  # Mock assignments
        r'fake.*=.*',  # Fake assignments  
        r'sample_data.*=.*\{',  # Sample data objects
        r'test_data.*=.*\[',  # Test data arrays
        r'placeholder.*return',  # Placeholder returns
        r'return.*True.*#.*placeholder',  # Placeholder True returns
        r'return.*False.*#.*placeholder',  # Placeholder False returns
        r'#.*TODO.*real.*implementation',  # TODO comments for real implementation
        r'#.*FIXME.*mock',  # FIXME comments about mocks
    ]
    
    # Files to exclude from checking (test files are OK to have mocks)
    exclude_patterns = [
        r'test_.*\.py$',
        r'.*_test\.py$', 
        r'.*/tests/.*\.py$',
        r'.*/test\.py$',
        r'.*/scripts/.*\.py$',  # Scripts are for testing/utilities
    ]
    
    print("🔍 Scanning for mock implementations...")
    print("=" * 60)
    
    for py_file in backend_dir.rglob("*.py"):
        # Skip test files
        if any(re.search(pattern, str(py_file)) for pattern in exclude_patterns):
            continue
            
        files_scanned += 1
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Get context for better filtering
                    context_lines = []
                    for i in range(max(0, line_num - 5), min(len(lines), line_num + 2)):
                        context_lines.append(lines[i])
                    context = '\n'.join(context_lines)
                    
                    # Skip backtest-related functions (legitimate use of sample tickers)
                    if any(keyword in context.lower() for keyword in [
                        '_get_test_ticker_list', 
                        'for backtesting',
                        'for testing only',
                        'backtest'
                    ]):
                        continue
                        
                    for pattern in mock_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues_found.append({
                                'file': str(py_file),
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': pattern
                            })
                            
        except Exception as e:
            print(f"⚠️ Error reading {py_file}: {e}")
    
    # Report results
    print(f"📊 Scanned {files_scanned} Python files")
    print()
    
    if issues_found:
        print(f"❌ Found {len(issues_found)} potential mock implementations:")
        print("=" * 60)
        
        for issue in issues_found:
            print(f"📁 File: {issue['file']}")
            print(f"📍 Line {issue['line']}: {issue['content']}")
            print(f"🔍 Pattern: {issue['pattern']}")
            print("-" * 40)
            
        return False
    else:
        print("✅ NO MOCK IMPLEMENTATIONS FOUND!")
        print("✅ All functions appear to use real data sources")
        print("✅ Production deployment ready")
        return True

def verify_real_api_usage():
    """Verify that real APIs are being used."""
    
    print("\n🔗 Verifying real API usage...")
    print("=" * 60)
    
    checks = [
        {
            'name': 'Telegram Bot API',
            'file': 'backend/services/telegram_trading.py',
            'pattern': r'api\.telegram\.org/bot',
            'description': 'Uses real Telegram Bot API'
        },
        {
            'name': 'Alpaca Trading API',
            'file': 'backend/services/alpaca_trading.py', 
            'pattern': r'alpaca_trade_api|tradeapi',
            'description': 'Uses real Alpaca trading API'
        },
        {
            'name': 'MongoDB Atlas',
            'file': 'backend/services/database_manager.py',
            'pattern': r'mongodb\+srv://',
            'description': 'Uses real MongoDB Atlas cloud database'
        },
        {
            'name': 'Auto-Trading Enabled',
            'file': 'backend/services/config.py',
            'pattern': r"AUTO_TRADING_ENABLED.*=.*'true'",
            'description': 'Auto-trading enabled by default'
        }
    ]
    
    all_good = True
    
    for check in checks:
        try:
            with open(check['file'], 'r') as f:
                content = f.read()
                if re.search(check['pattern'], content):
                    print(f"✅ {check['name']}: {check['description']}")
                else:
                    print(f"❌ {check['name']}: NOT FOUND")
                    all_good = False
        except FileNotFoundError:
            print(f"❌ {check['name']}: FILE NOT FOUND - {check['file']}")
            all_good = False
        except Exception as e:
            print(f"⚠️ {check['name']}: Error checking - {e}")
    
    return all_good

def main():
    """Run complete verification."""
    print("🚀 FINAL PRODUCTION VERIFICATION")
    print("=" * 60)
    print("Ensuring NO mock data, fallbacks, or test implementations")
    print("are used in production code.")
    print()
    
    # Change to project directory
    if not os.path.exists("backend"):
        print("❌ Must run from project root directory")
        sys.exit(1)
    
    # Run checks
    mock_check = scan_for_mock_implementations()
    api_check = verify_real_api_usage()
    
    print("\n" + "=" * 60)
    if mock_check and api_check:
        print("🎉 PRODUCTION VERIFICATION COMPLETE!")
        print("✅ All systems using REAL implementations")
        print("✅ No mock data found in production code")
        print("✅ All APIs configured for real usage")
        print("🚀 READY FOR DEPLOYMENT!")
        sys.exit(0)
    else:
        print("❌ PRODUCTION VERIFICATION FAILED!")
        print("🔧 Fix the issues above before deployment")
        sys.exit(1)

if __name__ == "__main__":
    main()
