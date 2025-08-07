#!/usr/bin/env python3
"""
Quick test of the fixed services
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv('/Users/isaacmineo/Main/projects/singal-flow/.env')

# Add backend to path
sys.path.insert(0, '/Users/isaacmineo/Main/projects/singal-flow/backend')

async def test_ai_signal_generation():
    """Test AI signal generation with fixed imports."""
    print("🤖 Testing AI Signal Generation...")
    try:
        from backend.services.ai_signal_generation import ai_signal_service
        
        # Test getting active signals
        active_signals = await ai_signal_service.get_active_signals()
        print(f"✅ Found {len(active_signals)} active signals")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_performance_analytics():
    """Test performance analytics with fixed imports."""
    print("📊 Testing Performance Analytics...")
    try:
        from backend.services.performance_analytics import performance_service
        
        # Test overall performance (should handle empty data gracefully)
        overall = await performance_service.get_overall_performance()
        print(f"✅ Overall Performance: {overall.total_return:.2f}% return")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_api_key():
    """Test if Polygon API key is working."""
    print("🔑 Testing Polygon API Key...")
    try:
        polygon_key = os.getenv('POLYGON_API_KEY')
        if not polygon_key:
            print("❌ No Polygon API key found")
            return False
        
        print(f"✅ Polygon API key present: {polygon_key[:8]}...")
        
        # Test basic request to check if key works
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            test_url = f"https://api.polygon.io/v1/marketstatus/now?apikey={polygon_key}"
            
            async with session.get(test_url) as response:
                if response.status == 200:
                    print("✅ Polygon API key is working")
                    return True
                elif response.status == 403:
                    print("❌ Polygon API key denied (403) - check plan limits or key validity")
                    return False
                else:
                    print(f"❌ Polygon API returned status: {response.status}")
                    return False
        
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

async def main():
    """Run quick tests."""
    print("🚀 Quick Test of Fixed Services")
    print("=" * 50)
    
    tests = [
        ("Polygon API Key", test_api_key),
        ("AI Signal Generation", test_ai_signal_generation),
        ("Performance Analytics", test_performance_analytics),
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\n")
    
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed < len(tests):
        print("\n🔧 Recommendations:")
        if passed == 0:
            print("- Check Polygon API key validity and plan limits")
            print("- Ensure all environment variables are properly set")
        else:
            print("- Most services working, minor fixes needed")

if __name__ == "__main__":
    asyncio.run(main())
