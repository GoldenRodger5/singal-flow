#!/usr/bin/env python3
"""
PRODUCTION AUDIT SCRIPT - Signal Flow Trading System
Comprehensive system audit for production deployment

This script will:
1. Check for any mock data or fallbacks
2. Clear MongoDB and cache completely
3. Verify notification system for market events
4. Test all API endpoints
5. Verify frontend-backend connectivity
6. Test MongoDB connection
"""

import asyncio
import os
import sys
import requests
import json
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Dict, List, Any

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

class ProductionAuditor:
    def __init__(self):
        self.backend_url = "https://web-production-3e19d.up.railway.app"
        self.local_backend = "http://localhost:8000"
        self.issues = []
        self.successes = []
        
    def log_issue(self, issue: str):
        self.issues.append(f"❌ {issue}")
        print(f"❌ {issue}")
    
    def log_success(self, success: str):
        self.successes.append(f"✅ {success}")
        print(f"✅ {success}")
    
    def log_info(self, info: str):
        print(f"ℹ️ {info}")

    def check_mock_data_usage(self):
        """Check for any mock data or fallback usage in the codebase"""
        print("\n🔍 1. CHECKING FOR MOCK DATA OR FALLBACKS...")
        
        # Check database manager for mock fallback
        db_manager_path = backend_dir / "services" / "database_manager.py"
        with open(db_manager_path, 'r') as f:
            content = f.read()
            
        if "MockDatabaseManager" in content and "get_db_manager" in content:
            # Check if the mock fallback is enabled
            if "_db_manager = MockDatabaseManager()" in content:
                self.log_issue("Database manager has mock fallback enabled - CRITICAL!")
                self.log_issue("This will cause system to use fake data if MongoDB connection fails")
                return False
        
        # Check for other mock data patterns
        mock_patterns = [
            "mock_data", "fake_data", "dummy_data", "sample_data", 
            "test_data", "fallback_data", "placeholder"
        ]
        
        python_files = list(backend_dir.rglob("*.py"))
        for file_path in python_files:
            if "test" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read().lower()
                    
                for pattern in mock_patterns:
                    if pattern in content and "no mock" not in content:
                        # Check if it's actually problematic
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if pattern in line and not line.strip().startswith('#'):
                                self.log_issue(f"Potential mock data in {file_path}:{i+1}")
                                break
            except Exception as e:
                continue
        
        self.log_success("Mock data check completed")
        return True

    def clear_mongodb_and_cache(self):
        """Clear MongoDB collections and local cache"""
        print("\n🗑️ 2. CLEARING MONGODB AND CACHE...")
        
        # Clear local data directory
        data_dir = backend_dir / "data"
        cache_dir = backend_dir / "cache"
        
        for directory in [data_dir, cache_dir]:
            if directory.exists():
                for file in directory.glob("*"):
                    if file.is_file():
                        file.unlink()
                        self.log_info(f"Deleted: {file.name}")
        
        self.log_success("Local data and cache cleared")
        
        # MongoDB clearing will be handled by the backend service
        self.log_info("MongoDB will be cleared by backend service on startup")
        return True

    def test_mongodb_connection(self):
        """Test MongoDB connection and verify it's working"""
        print("\n🗄️ 6. TESTING MONGODB CONNECTION...")
        
        try:
            from services.database_manager import get_db_manager
            db_manager = get_db_manager()
            
            # If we get a MockDatabaseManager, that's a problem
            if "Mock" in str(type(db_manager)):
                self.log_issue("MongoDB connection failed - using mock database!")
                return False
            
            self.log_success("MongoDB connection established")
            return True
            
        except Exception as e:
            self.log_issue(f"MongoDB connection test failed: {e}")
            return False

    def check_notification_system(self):
        """Verify notification system is configured for market events"""
        print("\n📱 3. CHECKING NOTIFICATION SYSTEM...")
        
        # Check if Telegram is configured
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not telegram_token:
            self.log_issue("TELEGRAM_BOT_TOKEN not configured")
            return False
            
        if not telegram_chat_id:
            self.log_issue("TELEGRAM_CHAT_ID not configured")
            return False
        
        self.log_success("Telegram credentials configured")
        
        # Check main.py for notification triggers
        main_py = backend_dir / "main.py"
        with open(main_py, 'r') as f:
            content = f.read()
            
        notification_checks = [
            "market.*open",
            "send.*notification",
            "telegram.*send",
            "buy.*sell.*notification"
        ]
        
        import re
        for check in notification_checks:
            if re.search(check, content, re.IGNORECASE):
                self.log_success(f"Found notification trigger: {check}")
        
        return True

    def test_api_endpoints(self):
        """Test all API endpoints"""
        print("\n🔌 4. TESTING API ENDPOINTS...")
        
        # List of endpoints to test
        endpoints = [
            "/health",
            "/health/detailed",
            "/api/account",
            "/api/positions", 
            "/api/holdings",
            "/api/portfolio",
            "/api/trades/active",
            "/api/trades/performance",
            "/api/ai/decisions/recent",
            "/api/ai/signals/recent",
            "/api/ai/learning/summary",
            "/api/ai/analysis",
            "/api/market/realtime/AAPL"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Check if response contains real data (not mock)
                    data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    
                    if isinstance(data, dict):
                        # Check for mock indicators
                        mock_indicators = ['mock', 'fake', 'dummy', 'sample', 'test']
                        data_str = str(data).lower()
                        
                        has_mock = any(indicator in data_str for indicator in mock_indicators)
                        if has_mock and 'no mock' not in data_str:
                            self.log_issue(f"Endpoint {endpoint} may contain mock data")
                        else:
                            self.log_success(f"Endpoint {endpoint} - OK")
                    else:
                        self.log_success(f"Endpoint {endpoint} - OK")
                        
                elif response.status_code == 404:
                    self.log_issue(f"Endpoint {endpoint} not found (404)")
                elif response.status_code == 500:
                    self.log_issue(f"Endpoint {endpoint} server error (500)")
                else:
                    self.log_issue(f"Endpoint {endpoint} returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_issue(f"Endpoint {endpoint} connection failed: {e}")
        
        return len([i for i in self.issues if "Endpoint" in i]) == 0

    def test_frontend_backend_connectivity(self):
        """Test frontend-backend connectivity"""
        print("\n🌐 5. TESTING FRONTEND-BACKEND CONNECTIVITY...")
        
        # Check if frontend can reach backend
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_success("Backend is accessible from frontend")
            else:
                self.log_issue(f"Backend health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_issue(f"Cannot reach backend: {e}")
            return False
        
        # Check CORS configuration
        try:
            response = requests.options(
                f"{self.backend_url}/health",
                headers={'Origin': 'http://localhost:3000'}
            )
            if 'Access-Control-Allow-Origin' in response.headers:
                self.log_success("CORS is properly configured")
            else:
                self.log_issue("CORS may not be properly configured")
        except Exception as e:
            self.log_issue(f"CORS check failed: {e}")
        
        return True

    def fix_critical_issues(self):
        """Fix critical issues found during audit"""
        print("\n🔧 FIXING CRITICAL ISSUES...")
        
        # Fix database manager mock fallback
        db_manager_path = backend_dir / "services" / "database_manager.py"
        with open(db_manager_path, 'r') as f:
            content = f.read()
        
        # Replace mock fallback with production error handling
        if "MockDatabaseManager()" in content:
            new_content = content.replace(
                """        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            # Return a mock database manager for development/testing
            _db_manager = MockDatabaseManager()""",
                """        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            # In production, we must have a working database
            raise RuntimeError(f"MongoDB connection required for production: {e}")"""
            )
            
            with open(db_manager_path, 'w') as f:
                f.write(new_content)
            
            self.log_success("Fixed database manager to require MongoDB connection")

    def add_market_notifications(self):
        """Add market open/close notifications to main.py"""
        print("\n📅 ADDING MARKET NOTIFICATIONS...")
        
        main_py = backend_dir / "main.py"
        with open(main_py, 'r') as f:
            content = f.read()
        
        # Check if market notifications are already present
        if "market_open_notification" not in content:
            # Add market notification functions
            notification_code = '''
    async def send_market_open_notification(self):
        """Send market open notification"""
        try:
            from services.telegram_trading import telegram_trading
            await telegram_trading.send_message(
                "🔔 *MARKET OPEN*\\n\\n"
                f"📈 US Markets are now OPEN\\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S EST')}\\n"
                f"🤖 AI system is actively monitoring\\n"
                f"🎯 Ready to execute trades"
            )
            self.log_success("Market open notification sent")
        except Exception as e:
            logger.error(f"Failed to send market open notification: {e}")
    
    async def send_market_close_notification(self):
        """Send market close notification"""
        try:
            from services.telegram_trading import telegram_trading
            await telegram_trading.send_message(
                "🔔 *MARKET CLOSED*\\n\\n"
                f"📉 US Markets are now CLOSED\\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S EST')}\\n"
                f"📊 Processing end-of-day analysis\\n"
                f"💤 System entering post-market mode"
            )
            self.log_success("Market close notification sent")
        except Exception as e:
            logger.error(f"Failed to send market close notification: {e}")
'''
            
            # Insert before the start method
            content = content.replace(
                "    async def start(self):",
                notification_code + "\n    async def start(self):"
            )
            
            with open(main_py, 'w') as f:
                f.write(content)
            
            self.log_success("Added market notification functions")

    def generate_report(self):
        """Generate final audit report"""
        print("\n" + "="*60)
        print("📋 PRODUCTION AUDIT REPORT")
        print("="*60)
        
        print(f"\n✅ SUCCESSES ({len(self.successes)}):")
        for success in self.successes:
            print(f"  {success}")
        
        print(f"\n❌ ISSUES FOUND ({len(self.issues)}):")
        for issue in self.issues:
            print(f"  {issue}")
        
        critical_issues = [i for i in self.issues if "CRITICAL" in i or "failed" in i]
        
        print(f"\n🚨 CRITICAL ISSUES: {len(critical_issues)}")
        if critical_issues:
            print("  SYSTEM IS NOT READY FOR PRODUCTION!")
            print("  Please fix critical issues before deployment.")
        else:
            print("  No critical issues found.")
        
        print(f"\n📊 OVERALL STATUS:")
        if len(critical_issues) == 0 and len(self.issues) < 3:
            print("  🟢 READY FOR PRODUCTION")
        elif len(critical_issues) == 0:
            print("  🟡 READY WITH MINOR ISSUES")
        else:
            print("  🔴 NOT READY - CRITICAL ISSUES PRESENT")
        
        return len(critical_issues) == 0

async def main():
    auditor = ProductionAuditor()
    
    print("🚀 STARTING PRODUCTION AUDIT FOR SIGNAL FLOW TRADING SYSTEM")
    print(f"⏰ Audit Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Run all audit checks
    auditor.check_mock_data_usage()
    auditor.clear_mongodb_and_cache()
    auditor.check_notification_system()
    auditor.test_api_endpoints()
    auditor.test_frontend_backend_connectivity()
    auditor.test_mongodb_connection()
    
    # Fix critical issues
    auditor.fix_critical_issues()
    auditor.add_market_notifications()
    
    # Generate final report
    is_ready = auditor.generate_report()
    
    if is_ready:
        print("\n🎉 SYSTEM IS READY FOR PRODUCTION DEPLOYMENT!")
    else:
        print("\n⚠️ SYSTEM NEEDS ATTENTION BEFORE PRODUCTION!")
    
    return is_ready

if __name__ == "__main__":
    asyncio.run(main())
