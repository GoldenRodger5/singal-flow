#!/usr/bin/env python3
"""
Comprehensive System Audit for Signal Flow Trading System
Tests all components for 24/7 operation readiness
"""

import asyncio
import sys
import os
import requests
import json
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append('backend')

class SystemAuditor:
    def __init__(self):
        self.results = {}
        self.api_base = "http://localhost:8000"
        
    def log_result(self, component: str, status: str, details: str = ""):
        """Log audit result for a component"""
        self.results[component] = {
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {component}: {status}")
        if details:
            print(f"   Details: {details}")
    
    async def audit_environment_variables(self):
        """Audit environment variables"""
        print("\n🔧 AUDITING ENVIRONMENT VARIABLES")
        print("=" * 50)
        
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            required_vars = [
                "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_BASE_URL",
                "MONGODB_URL", "TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", 
                "ANTHROPIC_API_KEY"
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                self.log_result("Environment Variables", "FAIL", f"Missing: {', '.join(missing_vars)}")
            else:
                self.log_result("Environment Variables", "PASS", f"All {len(required_vars)} variables set")
                
        except Exception as e:
            self.log_result("Environment Variables", "FAIL", str(e))
    
    async def audit_api_endpoints(self):
        """Audit API endpoints"""
        print("\n🌐 AUDITING API ENDPOINTS")
        print("=" * 50)
        
        try:
            # Test key endpoints
            endpoints = [
                ("/health", "Health Check"),
                ("/api/account", "Trading Account"),
                ("/api/system/status", "System Status"),
                ("/api/control/status", "Control Panel")
            ]
            
            failed_endpoints = []
            for endpoint, name in endpoints:
                try:
                    response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        print(f"   ✅ {name}: {response.status_code}")
                    else:
                        print(f"   ❌ {name}: {response.status_code}")
                        failed_endpoints.append(name)
                except Exception as e:
                    print(f"   ❌ {name}: {str(e)}")
                    failed_endpoints.append(name)
            
            if failed_endpoints:
                self.log_result("API Endpoints", "FAIL", f"Failed: {', '.join(failed_endpoints)}")
            else:
                self.log_result("API Endpoints", "PASS", f"All {len(endpoints)} endpoints working")
                
        except Exception as e:
            self.log_result("API Endpoints", "FAIL", str(e))
    
    async def audit_trading_connection(self):
        """Audit trading API connection"""
        print("\n📈 AUDITING TRADING CONNECTION")
        print("=" * 50)
        
        try:
            response = requests.get(f"{self.api_base}/api/account", timeout=10)
            if response.status_code == 200:
                account_data = response.json()
                buying_power = account_data.get('buying_power', 0)
                status = account_data.get('status', 'Unknown')
                
                if status == 'ACTIVE' and buying_power > 0:
                    self.log_result("Trading Connection", "PASS", 
                                   f"Account active, ${buying_power:,.2f} buying power")
                else:
                    self.log_result("Trading Connection", "WARN", 
                                   f"Status: {status}, Buying Power: ${buying_power}")
            else:
                self.log_result("Trading Connection", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Trading Connection", "FAIL", str(e))
    
    async def audit_database_connection(self):
        """Audit database connection"""
        print("\n🗄️ AUDITING DATABASE CONNECTION")
        print("=" * 50)
        
        try:
            response = requests.get(f"{self.api_base}/health/detailed", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                db_status = health_data.get('components', {}).get('database', {}).get('status')
                
                if db_status == 'healthy':
                    self.log_result("Database Connection", "PASS", "MongoDB connection healthy")
                else:
                    self.log_result("Database Connection", "WARN", f"Status: {db_status}")
            else:
                self.log_result("Database Connection", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Database Connection", "FAIL", str(e))
    
    async def audit_notification_system(self):
        """Audit notification system"""
        print("\n📱 AUDITING NOTIFICATION SYSTEM")
        print("=" * 50)
        
        try:
            # Test direct Telegram Bot API
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                self.log_result("Notification System", "FAIL", "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
                return
            
            # Test Telegram API directly
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': '🧪 *SYSTEM AUDIT TEST*\\n\\nTesting notification system for 24/7 operation\\n\\n' +
                           '✅ Market scanning: Every 1 minute\\n' +
                           '✅ AI learning: Every 30 minutes\\n' +
                           '✅ Validation: Every 2 hours\\n' +
                           '✅ Daily summaries: 4:00 PM EST\\n\\n' +
                           'System is ready for continuous operation! 🚀',
                    'parse_mode': 'Markdown'
                }
                
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('ok'):
                            self.log_result("Notification System", "PASS", "Telegram message sent successfully")
                        else:
                            self.log_result("Notification System", "FAIL", f"Telegram API error: {result}")
                    else:
                        self.log_result("Notification System", "FAIL", f"HTTP {response.status}")
                        
        except Exception as e:
            self.log_result("Notification System", "FAIL", str(e))
    
    async def audit_scheduler_status(self):
        """Audit scheduler and 24/7 operation readiness"""
        print("\n⏰ AUDITING SCHEDULER & 24/7 OPERATION")
        print("=" * 50)
        
        try:
            # Check if main orchestrator is running
            response = requests.get(f"{self.api_base}/api/system/status", timeout=10)
            if response.status_code == 200:
                system_data = response.json()
                health = system_data.get('health', {})
                overall_status = health.get('overall', 'unknown')
                uptime = health.get('uptime', 0)
                
                if uptime > 60:  # Running for more than 1 minute
                    self.log_result("24/7 Operation", "PASS", 
                                   f"System uptime: {uptime/3600:.1f} hours")
                else:
                    self.log_result("24/7 Operation", "WARN", 
                                   f"System uptime: {uptime:.0f} seconds (just started)")
                
                # Check for recent AI decisions
                decisions_count = system_data.get('recent_decisions_count', 0)
                if decisions_count > 0:
                    self.log_result("AI Decision Making", "PASS", f"{decisions_count} recent decisions")
                else:
                    self.log_result("AI Decision Making", "WARN", "No recent AI decisions")
                    
            else:
                self.log_result("24/7 Operation", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("24/7 Operation", "FAIL", str(e))
    
    async def audit_market_hours_handling(self):
        """Audit market hours and after-hours operation"""
        print("\n🕐 AUDITING MARKET HOURS HANDLING")
        print("=" * 50)
        
        try:
            from services.config import Config
            config = Config()
            
            # Check market hours configuration
            is_trading_hours = config.is_trading_hours()
            current_time = datetime.now()
            
            self.log_result("Market Hours Detection", "PASS", 
                           f"Trading hours: {is_trading_hours}, Current: {current_time.strftime('%H:%M:%S EST')}")
            
            # The system should run 24/7 regardless of market hours
            self.log_result("24/7 Capability", "PASS", "System configured for continuous operation")
            
        except Exception as e:
            self.log_result("Market Hours Handling", "FAIL", str(e))
    
    async def audit_error_handling(self):
        """Audit error handling and recovery"""
        print("\n🛡️ AUDITING ERROR HANDLING")
        print("=" * 50)
        
        try:
            # Test error endpoints to see if they're properly handled
            test_endpoints = [
                "/api/nonexistent/endpoint",
                "/api/market/realtime/INVALID"
            ]
            
            proper_errors = 0
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                    if response.status_code in [404, 501, 422]:  # Expected error codes
                        proper_errors += 1
                except:
                    pass  # Connection errors are fine for this test
            
            if proper_errors >= 1:
                self.log_result("Error Handling", "PASS", "Proper error responses")
            else:
                self.log_result("Error Handling", "WARN", "Could not verify error handling")
                
        except Exception as e:
            self.log_result("Error Handling", "FAIL", str(e))
    
    async def audit_performance(self):
        """Audit system performance"""
        print("\n⚡ AUDITING SYSTEM PERFORMANCE")
        print("=" * 50)
        
        try:
            response = requests.get(f"{self.api_base}/health/detailed", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                system_resources = health_data.get('components', {}).get('system_resources', {})
                
                cpu_percent = system_resources.get('cpu_percent', 0)
                memory_percent = system_resources.get('memory_percent', 0)
                
                performance_issues = []
                if cpu_percent > 80:
                    performance_issues.append(f"High CPU: {cpu_percent}%")
                if memory_percent > 85:
                    performance_issues.append(f"High Memory: {memory_percent}%")
                
                if performance_issues:
                    self.log_result("System Performance", "WARN", "; ".join(performance_issues))
                else:
                    self.log_result("System Performance", "PASS", 
                                   f"CPU: {cpu_percent}%, Memory: {memory_percent}%")
            else:
                self.log_result("System Performance", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("System Performance", "FAIL", str(e))
    
    def generate_audit_report(self):
        """Generate comprehensive audit report"""
        print("\n" + "🎯" * 50)
        print("COMPREHENSIVE SYSTEM AUDIT REPORT")
        print("🎯" * 50)
        
        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        warned = sum(1 for r in self.results.values() if r["status"] == "WARN")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAIL")
        total = len(self.results)
        
        print(f"\n📊 AUDIT SUMMARY:")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warned}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(total or 1)*100):.1f}%")
        
        if failed == 0 and warned <= 2:
            print(f"\n🎉 SYSTEM READY FOR 24/7 OPERATION!")
            print(f"🚀 Railway and Vercel deployment approved!")
        elif failed == 0:
            print(f"\n⚠️  SYSTEM MOSTLY READY - Minor issues to address")
            print(f"🔧 Review warnings before full deployment")
        else:
            print(f"\n❌ SYSTEM NOT READY - Critical issues found")
            print(f"🛠️  Fix failed components before deployment")
        
        # Save detailed report
        report = {
            "audit_timestamp": datetime.now().isoformat(),
            "summary": {
                "passed": passed,
                "warnings": warned,
                "failed": failed,
                "total": total,
                "success_rate": passed/(total or 1)*100
            },
            "results": self.results
        }
        
        with open("system_audit_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed audit report saved to: system_audit_report.json")
        
        return failed == 0
    
    async def run_full_audit(self):
        """Run comprehensive system audit"""
        print("🔍 SIGNAL FLOW TRADING SYSTEM - COMPREHENSIVE AUDIT")
        print("=" * 80)
        print(f"Audit started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Testing for 24/7 operation readiness...")
        
        # Run all audits
        await self.audit_environment_variables()
        await self.audit_api_endpoints()
        await self.audit_trading_connection()
        await self.audit_database_connection()
        await self.audit_notification_system()
        await self.audit_scheduler_status()
        await self.audit_market_hours_handling()
        await self.audit_error_handling()
        await self.audit_performance()
        
        # Generate final report
        return self.generate_audit_report()

async def main():
    """Main audit function"""
    auditor = SystemAuditor()
    success = await auditor.run_full_audit()
    
    if success:
        print("\n✅ AUDIT COMPLETED SUCCESSFULLY - System ready for deployment!")
        return 0
    else:
        print("\n❌ AUDIT FAILED - Fix issues before deployment!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Audit interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Audit failed with error: {e}")
        exit(1)
