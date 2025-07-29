# 📱 Notification Setup Guide

## 🚨 IMPORTANT: Follow these steps to enable notifications

### 1. 📱 WhatsApp Setup (Twilio)

#### Step 1: Set up WhatsApp Sandbox
1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Messaging** → **Settings** → **WhatsApp sandbox**
3. Send the sandbox code from your phone to the Twilio number
4. Example: Send "join <your-sandbox-code>" to +1 415 523 8886

#### Step 2: Update your .env
```bash
# Example settings (replace with your actual credentials):
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
WHATSAPP_FROM=whatsapp:+14155238886  # ← Change to Twilio sandbox number
WHATSAPP_TO=whatsapp:+1234567890     # ← Your verified phone number
```

#### Step 3: Alternative - SMS Instead
If WhatsApp is complex, use SMS:
```bash
SMS_FROM=+1234567890   # Your Twilio phone number
SMS_TO=+1987654321     # Your phone number
```

---

### 2. 📧 Email Setup (Gmail)

#### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Enable 2-Factor Authentication if not already enabled

#### Step 2: Generate App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and your device
3. Copy the 16-character password

#### Step 3: Update your .env
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=isaacmineo@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # ← Use App Password (16 chars)
NOTIFICATION_EMAIL=isaacmineo@gmail.com
```

---

### 3. 🔗 Webhook Setup (Optional)

#### For Slack:
1. Go to [Slack API](https://api.slack.com/apps)
2. Create new app → Incoming Webhooks
3. Get webhook URL like: `https://hooks.slack.com/services/T.../B.../xyz`

#### For Discord:
1. In Discord channel: Settings → Integrations → Webhooks
2. Create webhook and copy URL

#### Update .env:
```bash
NOTIFICATION_WEBHOOK_1=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
NOTIFICATION_WEBHOOK_2=https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK
```

---

## 🧪 Quick Test Commands

### Test WhatsApp only:
```python
from twilio.rest import Client

client = Client('your_sid', 'your_token')
message = client.messages.create(
    body='Test from Signal Flow Bot!',
    from_='whatsapp:+14155238886',  # Twilio sandbox
    to='whatsapp:+1234567890'       # Your number
)
print(f"Message sent: {message.sid}")
```

### Test Email only:
```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText('Test from Signal Flow Bot!')
msg['Subject'] = 'Test Email'
msg['From'] = 'isaacmineo@gmail.com'
msg['To'] = 'isaacmineo@gmail.com'

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('isaacmineo@gmail.com', 'your_app_password')
server.send_message(msg)
server.quit()
print("Email sent!")
```

---

## 🎯 Recommended Priority:

1. **WhatsApp** - Most important for real-time trading alerts
2. **Email** - Good for daily summaries and important updates  
3. **Webhooks** - Optional for team notifications

## 🚀 Quick Setup (Just WhatsApp):

If you want to get started quickly, just fix WhatsApp:

1. Text your Twilio sandbox code
2. Change `WHATSAPP_FROM` to the Twilio sandbox number
3. Re-run the test

Let me know which notification method you want to prioritize!
