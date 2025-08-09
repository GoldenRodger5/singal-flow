#!/usr/bin/env python3
"""
MongoDB Connection Test - Local vs Production
Tests MongoDB connection both locally and diagnoses production issues
"""

import os
import sys
from pathlib import Path
from pymongo import MongoClient
from urllib.parse import quote_plus, urlparse
import asyncio
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def test_mongodb_connection_string(connection_string, test_name):
    """Test a MongoDB connection string and return detailed diagnostics."""
    print(f"\n{'='*60}")
    print(f"🔍 TESTING: {test_name}")
    print(f"{'='*60}")
    
    try:
        # Parse connection string
        parsed = urlparse(connection_string)
        print(f"📝 Connection String Analysis:")
        print(f"   • Protocol: {parsed.scheme}")
        print(f"   • Host: {parsed.hostname}")
        print(f"   • Database: {parsed.path[1:] if parsed.path else 'Not specified'}")
        print(f"   • Username: {parsed.username}")
        print(f"   • Password: {'*' * len(parsed.password) if parsed.password else 'Not specified'}")
        print(f"   • Full length: {len(connection_string)} characters")
        
        # Test connection
        print(f"\n🔄 Testing connection...")
        client = MongoClient(connection_string, serverSelectionTimeoutMS=10000)
        
        # Test ping
        result = client.admin.command('ping')
        print(f"✅ Ping successful: {result}")
        
        # Test database access
        db_name = parsed.path[1:] if parsed.path else "signal_flow_trading"
        db = client[db_name]
        
        # Test write operation
        test_collection = db['connection_test']
        test_doc = {
            "test": True,
            "timestamp": datetime.now(),
            "source": test_name
        }
        
        insert_result = test_collection.insert_one(test_doc)
        print(f"✅ Write test successful: {insert_result.inserted_id}")
        
        # Test read operation
        found_doc = test_collection.find_one({"_id": insert_result.inserted_id})
        print(f"✅ Read test successful: Found document")
        
        # Cleanup
        test_collection.delete_one({"_id": insert_result.inserted_id})
        print(f"✅ Cleanup successful")
        
        # List databases
        db_list = client.list_database_names()
        print(f"📊 Available databases: {db_list}")
        
        # List collections in target database
        if db_name in db_list:
            collections = db.list_collection_names()
            print(f"📂 Collections in '{db_name}': {collections}")
        
        client.close()
        print(f"🎉 {test_name} - ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ {test_name} - CONNECTION FAILED!")
        print(f"   Error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

def main():
    """Main test function."""
    print("🚀 MONGODB CONNECTION DIAGNOSTICS")
    print("=" * 80)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test 1: Local environment
    local_mongodb_url = os.getenv('MONGODB_URL')
    if local_mongodb_url:
        local_success = test_mongodb_connection_string(local_mongodb_url, "LOCAL ENVIRONMENT")
    else:
        print("❌ No MONGODB_URL found in local environment")
        local_success = False
    
    # Test 2: Config class
    try:
        from services.config import Config
        config = Config()
        if config.MONGODB_URL:
            config_success = test_mongodb_connection_string(config.MONGODB_URL, "CONFIG CLASS")
        else:
            print("❌ No MONGODB_URL found in Config class")
            config_success = False
    except Exception as e:
        print(f"❌ Failed to load Config class: {e}")
        config_success = False
    
    # Test 3: Production comparison
    print(f"\n{'='*60}")
    print(f"🔍 PRODUCTION ANALYSIS")
    print(f"{'='*60}")
    
    # Simulate what Railway might be doing
    import requests
    try:
        response = requests.get("https://web-production-3e19d.up.railway.app/debug/mongodb", timeout=10)
        if response.status_code == 200:
            prod_data = response.json()
            print(f"📊 Production MongoDB Debug Info:")
            for key, value in prod_data.items():
                print(f"   • {key}: {value}")
        else:
            print(f"❌ Production debug endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach production debug endpoint: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📋 SUMMARY")
    print(f"{'='*80}")
    print(f"Local Environment:     {'✅ SUCCESS' if local_success else '❌ FAILED'}")
    print(f"Config Class:          {'✅ SUCCESS' if config_success else '❌ FAILED'}")
    
    if local_success and not config_success:
        print("\n🔍 DIAGNOSIS: Config class may not be loading .env file properly")
    elif not local_success:
        print("\n🔍 DIAGNOSIS: MongoDB connection string or credentials issue")
        print("   • Check MONGODB_URL format")
        print("   • Verify MongoDB Atlas credentials")
        print("   • Ensure IP whitelist includes your current IP")
        print("   • Check if MongoDB Atlas cluster is running")
    
    # Test connection string format specifically
    if local_mongodb_url:
        print(f"\n🔍 CONNECTION STRING VALIDATION:")
        
        # Check for common issues
        issues = []
        if not local_mongodb_url.startswith('mongodb+srv://'):
            issues.append("Should start with 'mongodb+srv://' for Atlas")
        
        if '@' not in local_mongodb_url:
            issues.append("Missing '@' separator between credentials and host")
        
        if '?' not in local_mongodb_url:
            issues.append("Missing query parameters (should have ?retryWrites=true&w=majority)")
        
        if ' ' in local_mongodb_url:
            issues.append("Contains spaces (should be URL encoded)")
        
        if len(issues) > 0:
            print("   ⚠️ POTENTIAL ISSUES FOUND:")
            for issue in issues:
                print(f"      • {issue}")
        else:
            print("   ✅ Connection string format looks correct")

if __name__ == "__main__":
    main()
