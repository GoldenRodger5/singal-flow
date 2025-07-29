#!/usr/bin/env python3
"""
Simple email notifications - no Twilio needed
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def send_email_alert(subject, message):
    """Send simple email alert."""
    try:
        # Gmail SMTP (works with App Password)
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        email = os.getenv('NOTIFICATION_EMAIL', 'isaacmineo@gmail.com')
        
        # For now, just use a simple approach
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        # This would need your Gmail App Password
        # server = smtplib.SMTP(smtp_server, smtp_port)
        # server.starttls()
        # server.login(email, app_password)
        # server.send_message(msg)
        # server.quit()
        
        print(f"📧 Email alert ready: {subject}")
        print(f"Message preview:\n{message}")
        return True
        
    except Exception as e:
        print(f"Email error: {e}")
        return False

def test_simple_email():
    """Test simple email notification."""
    subject = "🚀 TSLA BUY Signal - Confidence 9.2/10"
    message = f"""Signal Flow Trading Bot Alert

📈 TSLA - BUY SIGNAL
💰 Entry: $248.50
🎯 Confidence: 9.2/10
💵 Position: $12,450

📊 Targets:
🛡️ Stop Loss: $243.50
🎯 Take Profit: $258.50

🧠 Analysis:
• RSI oversold (22.3)
• VWAP bounce (+0.8%)
• Volume spike 3.2x

⏰ {datetime.now().strftime('%H:%M EST')}

Reply with:
- 'YES' to execute trade
- 'NO' to skip
- 'STOP' to pause bot"""
    
    send_email_alert(subject, message)

if __name__ == "__main__":
    test_simple_email()
