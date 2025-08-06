#!/usr/bin/env python3
"""
Final System Readiness Test
"""
import asyncio
import requests
from datetime import datetime

async def final_system_test():
    print('🎯 FINAL SYSTEM READINESS TEST')
    print('=' * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: API Health
    total_tests += 1
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print('✅ API Health Check: PASS')
            tests_passed += 1
        else:
            print(f'❌ API Health Check: FAIL ({response.status_code})')
    except Exception as e:
        print(f'❌ API Health Check: FAIL ({e})')
    
    # Test 2: Trading Account
    total_tests += 1
    try:
        response = requests.get('http://localhost:8000/api/account', timeout=5)
        if response.status_code == 200:
            account = response.json()
            if account.get('status') == 'ACTIVE':
                print(f'✅ Trading Account: PASS (${float(account.get("buying_power", 0)):,.0f})')
                tests_passed += 1
            else:
                print(f'❌ Trading Account: FAIL (inactive)')
        else:
            print(f'❌ Trading Account: FAIL ({response.status_code})')
    except Exception as e:
        print(f'❌ Trading Account: FAIL ({e})')
    
    # Test 3: Database Connection
    total_tests += 1
    try:
        response = requests.get('http://localhost:8000/health/detailed', timeout=10)
        if response.status_code == 200:
            health = response.json()
            db_status = health.get('components', {}).get('database', {}).get('status')
            if db_status == 'healthy':
                print('✅ Database Connection: PASS')
                tests_passed += 1
            else:
                print(f'❌ Database Connection: FAIL ({db_status})')
        else:
            print(f'❌ Database Connection: FAIL ({response.status_code})')
    except Exception as e:
        print(f'❌ Database Connection: FAIL ({e})')
    
    # Test 4: System Uptime
    total_tests += 1
    try:
        response = requests.get('http://localhost:8000/api/system/status', timeout=5)
        if response.status_code == 200:
            system = response.json()
            uptime = system.get('health', {}).get('uptime', 0)
            if uptime > 300:  # 5 minutes
                print(f'✅ System Uptime: PASS ({uptime/3600:.1f} hours)')
                tests_passed += 1
            else:
                print(f'⚠️  System Uptime: WARN ({uptime:.0f} seconds)')
                tests_passed += 0.5  # Partial credit
        else:
            print(f'❌ System Uptime: FAIL ({response.status_code})')
    except Exception as e:
        print(f'❌ System Uptime: FAIL ({e})')
    
    # Test 5: Control Panel
    total_tests += 1
    try:
        response = requests.get('http://localhost:8000/api/control/status', timeout=5)
        if response.status_code == 200:
            control = response.json()
            trading_enabled = control.get('control_state', {}).get('auto_trading', False)
            if trading_enabled:
                print('✅ Control Panel: PASS (auto-trading enabled)')
                tests_passed += 1
            else:
                print('⚠️  Control Panel: WARN (auto-trading disabled)')
                tests_passed += 0.5  # Partial credit
        else:
            print(f'❌ Control Panel: FAIL ({response.status_code})')
    except Exception as e:
        print(f'❌ Control Panel: FAIL ({e})')
    
    # Test 6: Market Scan Trigger
    total_tests += 1
    try:
        response = requests.post('http://localhost:8000/api/system/trigger_scan', timeout=10)
        if response.status_code == 200:
            print('✅ Market Scan Trigger: PASS')
            tests_passed += 1
        else:
            print(f'❌ Market Scan Trigger: FAIL ({response.status_code})')
    except Exception as e:
        print(f'❌ Market Scan Trigger: FAIL ({e})')
    
    # Calculate final score
    success_rate = (tests_passed / total_tests) * 100
    
    print('\n' + '🎯' * 50)
    print('FINAL SYSTEM READINESS SCORE')
    print('🎯' * 50)
    print(f'✅ Tests Passed: {tests_passed}/{total_tests}')
    print(f'📊 Success Rate: {success_rate:.1f}%')
    
    if success_rate >= 90:
        print('\n🎉 SYSTEM READY FOR 24/7 PRODUCTION!')
        print('🚀 Deploy to Railway/Vercel: APPROVED')
        print('💪 Trading system is operational and stable')
    elif success_rate >= 75:
        print('\n⚠️  SYSTEM MOSTLY READY - Minor issues')
        print('🔧 Address warnings before full deployment')
    else:
        print('\n❌ SYSTEM NOT READY - Critical issues found')
        print('🛠️  Fix failed tests before deployment')
    
    print(f'\n📅 Test completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    return success_rate >= 90

if __name__ == "__main__":
    success = asyncio.run(final_system_test())
    print(f'\n🏁 FINAL RESULT: {"✅ APPROVED" if success else "❌ NEEDS WORK"}')
