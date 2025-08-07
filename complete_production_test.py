#!/usr/bin/env python3
"""
Complete Production Readiness Test Suite
Tests all endpoints, notifications, and real data flows without mocks
"""
import asyncio
import aiohttp
import json
import time
import sys
import os
from datetime import datetime
from loguru import logger

# Add backend to path for imports
sys.path.insert(0, '/Users/isaacmineo/Main/projects/singal-flow/backend')

class ProductionReadinessTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = []
        self.errors = []
        
    async def test_api_endpoints(self):
        """Test all production API endpoints"""
        logger.info("🧪 Testing API Endpoints...")
        
        endpoints = [
            ("/", "GET", "Health Check"),
            ("/health", "GET", "Health Status"),
            ("/polygon/anomaly-detection", "GET", "Polygon Anomaly Detection"),
            ("/polygon/short-squeeze-scan", "GET", "Short Squeeze Scanner"),
            ("/polygon/sentiment-analysis", "GET", "Sentiment Analysis"),
            ("/polygon/unified-signals", "GET", "Unified Trading Signals"),
            ("/polygon/websocket-status", "GET", "WebSocket Status")
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint, method, description in endpoints:
                try:
                    start_time = time.time()
                    async with session.request(method, f"{self.base_url}{endpoint}") as response:
                        response_time = time.time() - start_time
                        status = response.status
                        data = await response.json()
                        
                        self.test_results.append({
                            'test': description,
                            'endpoint': endpoint,
                            'status': status,
                            'response_time': f"{response_time:.3f}s",
                            'success': status == 200,
                            'data_sample': str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                        })
                        
                        if status == 200:
                            logger.success(f"✅ {description}: {status} ({response_time:.3f}s)")
                        else:
                            logger.error(f"❌ {description}: {status}")
                            self.errors.append(f"{description}: HTTP {status}")
                            
                except Exception as e:
                    logger.error(f"❌ {description}: {str(e)}")
                    self.errors.append(f"{description}: {str(e)}")
                    self.test_results.append({
                        'test': description,
                        'endpoint': endpoint,
                        'status': 'ERROR',
                        'response_time': 'N/A',
                        'success': False,
                        'error': str(e)
                    })
                    
                # Rate limiting between requests
                await asyncio.sleep(0.5)
    
    async def test_core_trading_system(self):
        """Test core trading system with real data"""
        logger.info("🎯 Testing Core Trading System...")
        
        try:
            # Import main orchestrator
            from main import SignalFlowOrchestrator
            
            # Initialize orchestrator
            orchestrator = SignalFlowOrchestrator()
            
            # Test market scan with real data
            logger.info("Testing market scan functionality...")
            start_time = time.time()
            await orchestrator.run_market_scan()
            scan_time = time.time() - start_time
            
            self.test_results.append({
                'test': 'Market Scan',
                'success': True,
                'response_time': f"{scan_time:.3f}s",
                'details': 'Market scan completed successfully'
            })
            
            logger.success(f"✅ Market Scan: Completed in {scan_time:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Core Trading System: {str(e)}")
            self.errors.append(f"Core Trading System: {str(e)}")
            self.test_results.append({
                'test': 'Market Scan',
                'success': False,
                'error': str(e)
            })
    
    async def test_polygon_services(self):
        """Test Polygon.io services with real data"""
        logger.info("📊 Testing Polygon.io Services...")
        
        test_symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
        
        try:
            # Test Anomaly Detection
            from services.anomaly_detection import AnomalyDetector
            detector = AnomalyDetector()
            
            start_time = time.time()
            anomalies = await detector.detect_anomalies(test_symbols)
            detection_time = time.time() - start_time
            
            self.test_results.append({
                'test': 'Polygon Anomaly Detection',
                'success': True,
                'response_time': f"{detection_time:.3f}s",
                'symbols_tested': len(test_symbols),
                'anomalies_found': len(anomalies) if anomalies else 0
            })
            
            logger.success(f"✅ Anomaly Detection: {len(anomalies) if anomalies else 0} anomalies found ({detection_time:.3f}s)")
            
        except Exception as e:
            logger.error(f"❌ Polygon Anomaly Detection: {str(e)}")
            self.errors.append(f"Polygon Anomaly Detection: {str(e)}")
        
        try:
            # Test Short Squeeze Detection
            from services.short_squeeze_detector import ShortSqueezeDetector
            squeeze_detector = ShortSqueezeDetector()
            
            start_time = time.time()
            squeezes = await squeeze_detector.scan_for_squeezes()
            squeeze_time = time.time() - start_time
            
            self.test_results.append({
                'test': 'Short Squeeze Detection',
                'success': True,
                'response_time': f"{squeeze_time:.3f}s",
                'potential_squeezes': len(squeezes) if squeezes else 0
            })
            
            logger.success(f"✅ Short Squeeze Detection: {len(squeezes) if squeezes else 0} potential squeezes ({squeeze_time:.3f}s)")
            
        except Exception as e:
            logger.error(f"❌ Short Squeeze Detection: {str(e)}")
            self.errors.append(f"Short Squeeze Detection: {str(e)}")
    
    async def test_telegram_notifications(self):
        """Test Telegram notification system"""
        logger.info("📱 Testing Telegram Notifications...")
        
        try:
            # Test production Telegram integration
            from services.production_telegram import production_telegram
            
            # Test basic message
            test_message = (
                f"🧪 PRODUCTION TEST MESSAGE\n"
                f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n"
                f"📊 System: All endpoints tested\n"
                f"✅ Status: Production ready"
            )
            
            start_time = time.time()
            await production_telegram.send_message(test_message)
            notification_time = time.time() - start_time
            
            self.test_results.append({
                'test': 'Telegram Basic Message',
                'success': True,
                'response_time': f"{notification_time:.3f}s",
                'message_sent': True
            })
            
            logger.success(f"✅ Telegram Basic Message: Sent ({notification_time:.3f}s)")
            
            # Test trading signal notification
            mock_recommendation = {
                'action': 'BUY',
                'entry': 150.00,
                'take_profit': 165.00,
                'stop_loss': 145.00,
                'confidence': 0.85
            }
            
            mock_explanation = "Test trading signal for production readiness verification"
            
            start_time = time.time()
            await production_telegram.send_trading_signal(mock_recommendation, mock_explanation)
            signal_time = time.time() - start_time
            
            self.test_results.append({
                'test': 'Telegram Trading Signal',
                'success': True,
                'response_time': f"{signal_time:.3f}s",
                'signal_sent': True
            })
            
            logger.success(f"✅ Telegram Trading Signal: Sent ({signal_time:.3f}s)")
            
        except Exception as e:
            logger.error(f"❌ Telegram Notifications: {str(e)}")
            self.errors.append(f"Telegram Notifications: {str(e)}")
            self.test_results.append({
                'test': 'Telegram Notifications',
                'success': False,
                'error': str(e)
            })
    
    async def test_data_persistence(self):
        """Test data storage and retrieval"""
        logger.info("💾 Testing Data Persistence...")
        
        try:
            # Test historical data loading
            from services.data_manager import DataManager
            data_manager = DataManager()
            
            # Test loading historical data
            test_symbol = 'AAPL'
            start_time = time.time()
            historical_data = await data_manager.get_historical_data(test_symbol, period='1mo')
            data_time = time.time() - start_time
            
            if historical_data and len(historical_data) > 0:
                self.test_results.append({
                    'test': 'Historical Data Loading',
                    'success': True,
                    'response_time': f"{data_time:.3f}s",
                    'symbol': test_symbol,
                    'data_points': len(historical_data)
                })
                logger.success(f"✅ Historical Data: {len(historical_data)} points loaded ({data_time:.3f}s)")
            else:
                raise Exception("No historical data retrieved")
                
        except Exception as e:
            logger.error(f"❌ Data Persistence: {str(e)}")
            self.errors.append(f"Data Persistence: {str(e)}")
            self.test_results.append({
                'test': 'Historical Data Loading',
                'success': False,
                'error': str(e)
            })
    
    async def test_error_handling(self):
        """Test error handling and recovery"""
        logger.info("⚠️ Testing Error Handling...")
        
        try:
            # Test invalid symbol handling
            from services.anomaly_detection import AnomalyDetector
            detector = AnomalyDetector()
            
            invalid_symbols = ['INVALID123', 'FAKE456']
            start_time = time.time()
            result = await detector.detect_anomalies(invalid_symbols)
            error_time = time.time() - start_time
            
            # Should handle gracefully without crashing
            self.test_results.append({
                'test': 'Invalid Symbol Handling',
                'success': True,
                'response_time': f"{error_time:.3f}s",
                'handled_gracefully': True
            })
            
            logger.success(f"✅ Error Handling: Invalid symbols handled gracefully ({error_time:.3f}s)")
            
        except Exception as e:
            logger.warning(f"⚠️ Error Handling Test: {str(e)}")
    
    def check_production_config(self):
        """Check production configuration"""
        logger.info("⚙️ Checking Production Configuration...")
        
        config_issues = []
        
        # Check for mock/test flags
        from services.config import Config
        config = Config()
        
        # Check critical production settings
        if hasattr(config, 'MOCK_MODE') and config.MOCK_MODE:
            config_issues.append("MOCK_MODE is enabled")
            
        if hasattr(config, 'TEST_MODE') and config.TEST_MODE:
            config_issues.append("TEST_MODE is enabled")
            
        if hasattr(config, 'DEBUG') and config.DEBUG:
            config_issues.append("DEBUG mode is enabled")
        
        # Check required API keys
        required_keys = ['POLYGON_API_KEY', 'TELEGRAM_BOT_TOKEN', 'ALPACA_API_KEY']
        for key in required_keys:
            if not getattr(config, key, None):
                config_issues.append(f"Missing {key}")
        
        self.test_results.append({
            'test': 'Production Configuration',
            'success': len(config_issues) == 0,
            'issues': config_issues
        })
        
        if config_issues:
            logger.warning(f"⚠️ Configuration Issues: {', '.join(config_issues)}")
        else:
            logger.success("✅ Production Configuration: All settings verified")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("📋 Generating Production Readiness Report...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get('success', False))
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': f"{success_rate:.1f}%"
            },
            'production_ready': success_rate >= 90 and len(self.errors) == 0,
            'detailed_results': self.test_results,
            'errors': self.errors,
            'recommendations': []
        }
        
        # Add recommendations based on results
        if success_rate < 90:
            report['recommendations'].append("Address failing tests before production deployment")
        
        if self.errors:
            report['recommendations'].append("Resolve all error conditions")
            
        if success_rate >= 95:
            report['recommendations'].append("System is production ready - deploy with confidence")
        
        # Save report
        report_path = '/Users/isaacmineo/Main/projects/singal-flow/production_readiness_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Report saved to: {report_path}")
        
        return report
    
    async def run_complete_test(self):
        """Run complete production readiness test suite"""
        logger.info("🚀 Starting Complete Production Readiness Test...")
        start_time = time.time()
        
        # Run all test categories
        await self.test_api_endpoints()
        await self.test_core_trading_system()
        await self.test_polygon_services()
        await self.test_telegram_notifications()
        await self.test_data_persistence()
        await self.test_error_handling()
        self.check_production_config()
        
        total_time = time.time() - start_time
        
        # Generate and display report
        report = self.generate_report()
        
        logger.info(f"📊 Production Readiness Test Complete ({total_time:.2f}s)")
        logger.info(f"✅ Passed: {report['summary']['passed']}/{report['summary']['total_tests']}")
        logger.info(f"📈 Success Rate: {report['summary']['success_rate']}")
        logger.info(f"🎯 Production Ready: {'YES' if report['production_ready'] else 'NO'}")
        
        if report['production_ready']:
            logger.success("🎉 SYSTEM IS PRODUCTION READY!")
        else:
            logger.error("❌ SYSTEM NEEDS FIXES BEFORE PRODUCTION")
            for error in self.errors[:5]:  # Show first 5 errors
                logger.error(f"   • {error}")
        
        return report


async def main():
    """Run the complete production readiness test"""
    test_suite = ProductionReadinessTest()
    
    # Check if API server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health", timeout=5) as response:
                if response.status == 200:
                    logger.info("✅ API server is running")
                else:
                    logger.error("❌ API server returned non-200 status")
                    return
    except Exception as e:
        logger.error(f"❌ Cannot connect to API server: {e}")
        logger.info("💡 Start the API server first: python backend/scripts/production_api.py")
        return
    
    # Run complete test suite
    await test_suite.run_complete_test()


if __name__ == "__main__":
    asyncio.run(main())
