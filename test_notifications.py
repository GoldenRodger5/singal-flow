#!/usr/bin/env python3
"""
Test script for all notification systems.
Tests WhatsApp, email, and webhook notifications.
"""
import asyncio
import os
from datetime import datetime
from loguru import logger

# Set up logging
logger.add("logs/notification_test.log", rotation="1 day")

def test_environment_variables():
    """Test that all required environment variables are set."""
    print("🔧 Testing Environment Variables")
    print("-" * 50)
    
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'WHATSAPP_FROM',
        'WHATSAPP_TO',
        'NOTIFICATION_EMAIL'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'TOKEN' in var or 'SID' in var:
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            missing_vars.append(var)
            print(f"❌ {var}: NOT SET")
    
    if missing_vars:
        print(f"\n⚠️  Missing variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ All environment variables are set!")
        return True

def test_whatsapp_notification():
    """Test WhatsApp notification via Twilio."""
    print("\n📱 Testing WhatsApp Notification")
    print("-" * 50)
    
    try:
        from twilio.rest import Client
        
        # Get Twilio credentials
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        whatsapp_from = os.getenv('WHATSAPP_FROM')
        whatsapp_to = os.getenv('WHATSAPP_TO')
        
        if not all([account_sid, auth_token, whatsapp_from, whatsapp_to]):
            print("❌ Missing Twilio/WhatsApp configuration")
            return False
        
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Test message
        test_message = f"""🤖 Signal Flow Bot - Test Message
        
✅ WhatsApp integration is working!
📅 Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🚀 Your trading bot notifications are ready!

This is a test message to verify your WhatsApp notifications are working properly."""
        
        # Send message
        message = client.messages.create(
            body=test_message,
            from_=whatsapp_from,
            to=whatsapp_to
        )
        
        print(f"✅ WhatsApp message sent successfully!")
        print(f"   Message SID: {message.sid}")
        print(f"   Status: {message.status}")
        print(f"   To: {whatsapp_to}")
        
        return True
        
    except Exception as e:
        print(f"❌ WhatsApp test failed: {e}")
        logger.error(f"WhatsApp test error: {e}")
        return False

def test_email_notification():
    """Test email notification."""
    print("\n📧 Testing Email Notification")
    print("-" * 50)
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Get email configuration
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        notification_email = os.getenv('NOTIFICATION_EMAIL')
        
        if not all([smtp_username, smtp_password, notification_email]):
            print("❌ Email configuration incomplete")
            print("   Note: Email is optional. Set SMTP_USERNAME and SMTP_PASSWORD to enable.")
            return True  # Not a failure, just not configured
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = notification_email
        msg['Subject'] = "🤖 Signal Flow Bot - Email Test"
        
        body = f"""
Signal Flow Trading Bot - Email Test

✅ Email integration is working!
📅 Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🚀 Your trading bot email notifications are ready!

This is a test email to verify your email notifications are working properly.

Best regards,
Signal Flow Bot
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, notification_email, msg.as_string())
        server.quit()
        
        print(f"✅ Email sent successfully!")
        print(f"   To: {notification_email}")
        print(f"   Server: {smtp_server}:{smtp_port}")
        
        return True
        
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        logger.error(f"Email test error: {e}")
        return False

def test_webhook_notifications():
    """Test webhook notifications."""
    print("\n🔗 Testing Webhook Notifications")
    print("-" * 50)
    
    try:
        import requests
        
        webhook_urls = [
            os.getenv('NOTIFICATION_WEBHOOK_1'),
            os.getenv('NOTIFICATION_WEBHOOK_2')
        ]
        
        # Filter out None values
        webhook_urls = [url for url in webhook_urls if url and url != 'https://hooks.slack.com/your/webhook/url']
        
        if not webhook_urls:
            print("❌ No webhook URLs configured")
            print("   Note: Webhooks are optional. Set NOTIFICATION_WEBHOOK_1 or NOTIFICATION_WEBHOOK_2 to enable.")
            return True  # Not a failure, just not configured
        
        success_count = 0
        for i, url in enumerate(webhook_urls, 1):
            try:
                payload = {
                    "text": f"🤖 Signal Flow Bot - Webhook Test #{i}",
                    "attachments": [
                        {
                            "color": "good",
                            "fields": [
                                {
                                    "title": "Test Status",
                                    "value": "✅ Webhook integration working!",
                                    "short": True
                                },
                                {
                                    "title": "Test Time",
                                    "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    "short": True
                                }
                            ]
                        }
                    ]
                }
                
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ Webhook {i} sent successfully!")
                    print(f"   URL: {url[:50]}...")
                    success_count += 1
                else:
                    print(f"❌ Webhook {i} failed: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Webhook {i} error: {e}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        logger.error(f"Webhook test error: {e}")
        return False

def test_trading_notification_format():
    """Test the format of trading notifications."""
    print("\n📊 Testing Trading Notification Formats")
    print("-" * 50)
    
    # Sample trading notification
    sample_trade = {
        'ticker': 'AAPL',
        'signal': 'BUY',
        'price': 150.25,
        'confidence': 8.5,
        'position_size': 15000,
        'stop_loss': 147.25,
        'take_profit': 156.25,
        'reasoning': 'RSI oversold + VWAP bounce + high volume'
    }
    
    # Format WhatsApp message
    whatsapp_msg = f"""🚀 SIGNAL ALERT 🚀

📈 {sample_trade['ticker']} - {sample_trade['signal']}
💰 Price: ${sample_trade['price']}
🎯 Confidence: {sample_trade['confidence']}/10
💵 Position: ${sample_trade['position_size']:,}

📊 Targets:
   🛡️  Stop Loss: ${sample_trade['stop_loss']}
   🎯 Take Profit: ${sample_trade['take_profit']}

🧠 Reasoning: {sample_trade['reasoning']}

⏰ {datetime.now().strftime('%H:%M:%S EST')}"""
    
    print("📱 WhatsApp Format Preview:")
    print("-" * 30)
    print(whatsapp_msg)
    print()
    
    # Format email subject and body
    email_subject = f"🚀 {sample_trade['ticker']} {sample_trade['signal']} Signal - Confidence {sample_trade['confidence']}/10"
    
    print("📧 Email Format Preview:")
    print("-" * 30)
    print(f"Subject: {email_subject}")
    print()
    
    return True

async def run_all_tests():
    """Run all notification tests."""
    print("🧪 Signal Flow Notification System Test")
    print("=" * 60)
    print()
    
    # Test environment
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n❌ Environment setup incomplete. Please check your .env file.")
        return
    
    # Test each notification system
    results = {}
    
    results['whatsapp'] = test_whatsapp_notification()
    results['email'] = test_email_notification()
    results['webhooks'] = test_webhook_notifications()
    
    # Test format
    test_trading_notification_format()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper():12} {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All notification systems are working correctly!")
        print("Your trading bot is ready to send alerts!")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} notification system(s) need attention.")
        print("Check the configuration and try again.")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    asyncio.run(run_all_tests())
