#!/usr/bin/env python3
"""
Test Polygon.io API Integration
Tests real market data fetching to ensure AI is using live data
"""
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

class PolygonAPITester:
    """Test Polygon.io API functionality and data quality."""
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = "https://api.polygon.io"
        
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not found in environment variables")
        
        logger.info(f"🔍 Testing Polygon.io API...")
        logger.info(f"🔑 API Key: {self.api_key[:8]}...{self.api_key[-4:]}")
    
    def test_api_connection(self) -> bool:
        """Test basic API connectivity."""
        try:
            logger.info("🔗 Testing API connection...")
            
            url = f"{self.base_url}/v2/aggs/ticker/AAPL/prev?adjusted=true&apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ API connection successful")
                logger.info(f"📊 Response status: {data.get('status', 'unknown')}")
                return True
            else:
                logger.error(f"❌ API connection failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ API connection error: {e}")
            return False
    
    def test_real_time_quotes(self) -> bool:
        """Test real-time quote fetching."""
        try:
            logger.info("📡 Testing real-time quotes...")
            
            test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
            successful_quotes = 0
            
            for symbol in test_symbols:
                # Test last trade endpoint
                url = f"{self.base_url}/v2/last/trade/{symbol}?apikey={self.api_key}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'results' in data and data['results']:
                        price = data['results']['p']
                        timestamp = data['results']['t']
                        
                        # Convert timestamp to readable format
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        
                        logger.info(f"✅ {symbol}: ${price:.2f} at {dt.strftime('%H:%M:%S')}")
                        successful_quotes += 1
                    else:
                        logger.warning(f"⚠️ {symbol}: No data in response")
                else:
                    logger.warning(f"⚠️ {symbol}: API error {response.status_code}")
            
            success_rate = successful_quotes / len(test_symbols) * 100
            logger.info(f"📊 Quote success rate: {success_rate:.1f}% ({successful_quotes}/{len(test_symbols)})")
            
            return success_rate >= 60  # Consider 60% success rate as passing
            
        except Exception as e:
            logger.error(f"❌ Real-time quotes test error: {e}")
            return False
    
    def test_historical_data(self) -> bool:
        """Test historical data fetching for technical analysis."""
        try:
            logger.info("📈 Testing historical data...")
            
            # Get 5 days of minute data for SPY
            from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/v2/aggs/ticker/SPY/range/1/minute/{from_date}/{to_date}?adjusted=true&sort=asc&apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data and data['results']:
                    results = data['results']
                    logger.info(f"✅ Historical data received: {len(results)} data points")
                    
                    # Analyze data quality
                    latest_point = results[-1]
                    logger.info(f"📊 Latest data point:")
                    logger.info(f"   🕐 Time: {datetime.fromtimestamp(latest_point['t']/1000)}")
                    logger.info(f"   💰 Close: ${latest_point['c']:.2f}")
                    logger.info(f"   📈 High: ${latest_point['h']:.2f}")
                    logger.info(f"   📉 Low: ${latest_point['l']:.2f}")
                    logger.info(f"   📊 Volume: {latest_point['v']:,}")
                    
                    # Check data freshness (should be within last 24 hours for market days)
                    latest_time = datetime.fromtimestamp(latest_point['t']/1000)
                    hours_old = (datetime.now() - latest_time).total_seconds() / 3600
                    
                    if hours_old < 72:  # Within 3 days (accounting for weekends)
                        logger.info(f"✅ Data freshness: {hours_old:.1f} hours old (FRESH)")
                        return True
                    else:
                        logger.warning(f"⚠️ Data freshness: {hours_old:.1f} hours old (STALE)")
                        return False
                else:
                    logger.error("❌ No historical data in response")
                    return False
            else:
                logger.error(f"❌ Historical data request failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Historical data test error: {e}")
            return False
    
    def test_market_data_for_ai(self) -> bool:
        """Test market data specifically for AI analysis."""
        try:
            logger.info("🧠 Testing market data for AI analysis...")
            
            # Test symbols in the $1-50 range (our compliance range)
            test_symbols = ['F', 'BAC', 'T', 'PFE', 'INTC', 'NIO', 'SOFI', 'PLTR', 'BB', 'NOK', 'SIRI']
            compliant_symbols = []
            
            for symbol in test_symbols:
                # Get current price
                url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev?adjusted=true&apikey={self.api_key}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'results' in data and len(data['results']) > 0:
                        price = data['results'][0]['c']  # Close price
                        
                        # Check compliance with $1-50 range
                        if 1.0 <= price <= 50.0:
                            compliant_symbols.append((symbol, price))
                            logger.info(f"✅ {symbol}: ${price:.2f} (COMPLIANT)")
                        else:
                            logger.warning(f"⚠️ {symbol}: ${price:.2f} (OUT OF RANGE)")
                    else:
                        logger.warning(f"⚠️ {symbol}: No price data")
                else:
                    logger.warning(f"⚠️ {symbol}: API error {response.status_code}")
            
            logger.info(f"📊 Compliant symbols found: {len(compliant_symbols)}/{len(test_symbols)}")
            
            if compliant_symbols:
                logger.info("🎯 AI will use these symbols for paper trading:")
                for symbol, price in compliant_symbols[:5]:  # Show first 5
                    logger.info(f"   💼 {symbol}: ${price:.2f}")
                return True
            else:
                logger.error("❌ No compliant symbols found")
                return False
                
        except Exception as e:
            logger.error(f"❌ AI market data test error: {e}")
            return False
    
    def test_api_rate_limits(self) -> bool:
        """Test API rate limits and response times."""
        try:
            logger.info("⏱️ Testing API rate limits...")
            
            import time
            
            # Make 5 quick requests to test rate limiting
            response_times = []
            successful_requests = 0
            
            for i in range(5):
                start_time = time.time()
                
                url = f"{self.base_url}/v2/aggs/ticker/SPY/prev?adjusted=true&apikey={self.api_key}"
                response = requests.get(url, timeout=5)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
                if response.status_code == 200:
                    successful_requests += 1
                    logger.info(f"   Request {i+1}: {response_time:.0f}ms ✅")
                else:
                    logger.warning(f"   Request {i+1}: {response_time:.0f}ms ❌ (Status: {response.status_code})")
                
                time.sleep(0.5)  # Small delay between requests
            
            avg_response_time = sum(response_times) / len(response_times)
            success_rate = successful_requests / 5 * 100
            
            logger.info(f"📊 Rate limit test results:")
            logger.info(f"   ⏱️ Average response time: {avg_response_time:.0f}ms")
            logger.info(f"   ✅ Success rate: {success_rate:.0f}%")
            
            return success_rate >= 80 and avg_response_time < 2000  # 80% success, <2s response
            
        except Exception as e:
            logger.error(f"❌ Rate limit test error: {e}")
            return False
    
    def run_comprehensive_test(self) -> dict:
        """Run all tests and return comprehensive results."""
        logger.info("🚀 Starting comprehensive Polygon.io API test...")
        logger.info("=" * 60)
        
        test_results = {
            'api_connection': False,
            'real_time_quotes': False,
            'historical_data': False,
            'ai_market_data': False,
            'rate_limits': False
        }
        
        # Run all tests
        test_results['api_connection'] = self.test_api_connection()
        print()  # Line break
        
        test_results['real_time_quotes'] = self.test_real_time_quotes()
        print()
        
        test_results['historical_data'] = self.test_historical_data()
        print()
        
        test_results['ai_market_data'] = self.test_market_data_for_ai()
        print()
        
        test_results['rate_limits'] = self.test_api_rate_limits()
        print()
        
        # Calculate overall score
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        overall_score = passed_tests / total_tests * 100
        
        # Print final results
        logger.info("📊 POLYGON API TEST RESULTS")
        logger.info("=" * 60)
        
        for test_name, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            formatted_name = test_name.replace('_', ' ').title()
            logger.info(f"{formatted_name}: {status}")
        
        logger.info(f"\n🎯 Overall Score: {overall_score:.0f}% ({passed_tests}/{total_tests} tests passed)")
        
        if overall_score >= 80:
            logger.info("🎉 EXCELLENT: Polygon API is ready for production AI trading!")
        elif overall_score >= 60:
            logger.info("👍 GOOD: Polygon API is functional with minor issues")
        else:
            logger.error("⚠️ ISSUES: Polygon API needs attention before AI trading")
        
        return test_results


def main():
    """Main test function."""
    try:
        tester = PolygonAPITester()
        results = tester.run_comprehensive_test()
        
        # Return exit code based on results
        passed_tests = sum(results.values())
        total_tests = len(results)
        
        if passed_tests >= total_tests * 0.8:  # 80% pass rate
            print("\n✅ Polygon API testing completed successfully!")
            return 0
        else:
            print(f"\n⚠️ Polygon API testing completed with issues ({passed_tests}/{total_tests} passed)")
            return 1
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
