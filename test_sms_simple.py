#!/usr/bin/env python3
"""
Simple SMS test - easier than WhatsApp setup
"""
import os
from dotenv import load_dotenv
load_dotenv()

def test_sms():
    """Test simple SMS notification."""
    try:
        from twilio.rest import Client
        
        # Use your existing credentials
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        # For SMS, use your Twilio phone number directly
        sms_from = os.getenv('SMS_FROM', '+1234567890')   # Your Twilio number
        sms_to = os.getenv('SMS_TO', '+1987654321')       # Your phone number
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body="""🤖 Signal Flow Bot Test!

✅ SMS notifications working!
📊 AAPL BUY signal detected
💰 Price: $150.25
🎯 Confidence: 8.5/10

Your trading bot is ready! 🚀""",
            from_=sms_from,
            to=sms_to
        )
        
        print(f"✅ SMS sent successfully!")
        print(f"   Message SID: {message.sid}")
        print(f"   From: {sms_from}")
        print(f"   To: {sms_to}")
        
        return True
        
    except Exception as e:
        print(f"❌ SMS test failed: {e}")
        return False

if __name__ == "__main__":
    print("📱 Testing Simple SMS Notification")
    print("-" * 40)
    test_sms()
