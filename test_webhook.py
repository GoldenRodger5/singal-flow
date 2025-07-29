#!/usr/bin/env python3
"""
Test the webhook functionality locally using polling simulation
"""
import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def simulate_button_click():
    """Simulate a button click by directly calling the webhook handler."""
    
    # Test callback data
    test_callback = {
        "update_id": 123456,
        "callback_query": {
            "id": "test_callback_id",
            "from": {
                "id": int(os.getenv('TELEGRAM_CHAT_ID')),
                "first_name": "Test"
            },
            "message": {
                "message_id": 789,
                "date": int(time.time()),
                "chat": {
                    "id": int(os.getenv('TELEGRAM_CHAT_ID')),
                    "type": "private"
                }
            },
            "data": "execute_TSLA_BUY"
        }
    }
    
    try:
        # Send the simulated callback to our local webhook
        response = requests.post(
            "http://localhost:8000/webhook",
            json=test_callback,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Webhook test successful!")
            print("📱 Check Telegram for the trade execution response")
            return True
        else:
            print(f"❌ Webhook test failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_all_buttons():
    """Test all different button types."""
    
    test_buttons = [
        ("execute_TSLA_BUY", "Execute TSLA trade"),
        ("skip_AAPL_BUY", "Skip AAPL trade"),
        ("portfolio", "Show portfolio"),
        ("pause_bot", "Pause bot"),
        ("scan_market", "Scan market"),
        ("settings", "Show settings")
    ]
    
    print("🧪 Testing all button responses...")
    print("=" * 50)
    
    for callback_data, description in test_buttons:
        print(f"\n🔘 Testing: {description}")
        
        test_callback = {
            "update_id": 123456 + hash(callback_data) % 1000,
            "callback_query": {
                "id": f"test_{callback_data}",
                "from": {
                    "id": int(os.getenv('TELEGRAM_CHAT_ID')),
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 789,
                    "date": int(time.time()),
                    "chat": {
                        "id": int(os.getenv('TELEGRAM_CHAT_ID')),
                        "type": "private"
                    }
                },
                "data": callback_data
            }
        }
        
        try:
            response = requests.post(
                "http://localhost:8000/webhook",
                json=test_callback
            )
            
            if response.status_code == 200:
                print(f"  ✅ {description} - OK")
            else:
                print(f"  ❌ {description} - Failed ({response.status_code})")
                
        except Exception as e:
            print(f"  ❌ {description} - Error: {e}")
        
        time.sleep(1)  # Small delay between tests
    
    print(f"\n📱 Check Telegram for all the responses!")
    print("🎉 If you see responses, the webhook system is working!")

if __name__ == "__main__":
    print("🧪 Testing Telegram Webhook System")
    print("=" * 50)
    print("📡 Make sure the FastAPI server is running on localhost:8000")
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("✅ FastAPI server is running!")
        else:
            print("❌ Server responded with error")
            exit(1)
    except:
        print("❌ FastAPI server is not running!")
        print("💡 Run: python telegram_webhook.py")
        exit(1)
    
    # Test individual button
    print("\n1. 🔘 Testing single button click...")
    simulate_button_click()
    
    time.sleep(2)
    
    # Test all buttons
    print("\n2. 🧪 Testing all button types...")
    test_all_buttons()
    
    print("\n🎉 Test complete!")
    print("📱 All responses should appear in your Telegram chat")
    print("🚀 Ready for Railway deployment!")
