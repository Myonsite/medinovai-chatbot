# Twilio Setup Guide for MedinovAI Chatbot

This guide provides step-by-step instructions for setting up Twilio integration with the MedinovAI Chatbot for SMS and voice functionality.

## 📋 Prerequisites

- Active Twilio account (sign up at https://www.twilio.com/try-twilio)
- MedinovAI Chatbot deployed and running
- Public domain/URL for webhook endpoints
- Administrative access to your deployment environment

## 🚀 Step 1: Create Twilio Account and Get Credentials

### 1.1 Sign Up for Twilio

1. Go to [Twilio Console](https://console.twilio.com)
2. Sign up for a new account or log in to existing account
3. Complete phone verification process

### 1.2 Get Account Credentials

1. Navigate to **Console Dashboard**
2. Copy the following credentials:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: Click "Show" to reveal token
   - **Test credentials** are available for development

```bash
# Example credentials format
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

## 📱 Step 2: Purchase Phone Number

### 2.1 Buy a Phone Number

1. In Twilio Console, go to **Phone Numbers > Manage > Buy a number**
2. Select your country (United States recommended for US customers)
3. Choose capabilities needed:
   - ✅ **Voice** (for voice calls)
   - ✅ **SMS** (for text messaging)
   - ✅ **MMS** (for multimedia messaging - optional)

### 2.2 Configure Phone Number

1. Select a phone number that supports both Voice and SMS
2. Click **Buy** (costs typically $1/month + usage)
3. Note down your purchased number: `+1234567890`

```bash
# Add to your environment
TWILIO_PHONE_NUMBER=+1234567890
```

## 🔗 Step 3: Configure Webhooks

### 3.1 Set SMS Webhook

1. In Twilio Console, go to **Phone Numbers > Manage > Active numbers**
2. Click on your purchased phone number
3. In the **Messaging** section:
   - **Webhook URL**: `https://your-domain.com/api/webhooks/twilio/sms`
   - **HTTP Method**: `POST`
   - **Primary Handler** (recommended)

### 3.2 Set Voice Webhook

1. In the same phone number configuration
2. In the **Voice & Fax** section:
   - **Webhook URL**: `https://your-domain.com/api/webhooks/twilio/voice`
   - **HTTP Method**: `POST`
   - **Primary Handler** (recommended)

### 3.3 Configure Status Callbacks (Optional)

For delivery tracking and advanced monitoring:

```
Messaging Status Callback URL: https://your-domain.com/api/webhooks/twilio/sms/status
Voice Status Callback URL: https://your-domain.com/api/webhooks/twilio/voice/status
```

## ⚙️ Step 4: Environment Configuration

### 4.1 Update Environment Variables

Add the following to your `.env` file:

```bash
# =============================================================================
# TWILIO CONFIGURATION
# =============================================================================
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_URL=https://your-domain.com/api/webhooks/twilio

# Voice Configuration
TWILIO_VOICE_ENABLED=true
TWILIO_TTS_VOICE=Polly.Joanna
TWILIO_SPEECH_TIMEOUT=5
TWILIO_SPEECH_MODEL=default

# SMS Configuration
TWILIO_SMS_ENABLED=true
SMS_OTP_EXPIRY=300
SMS_MAX_RETRY=3
```

### 4.2 Voice Configuration Options

Available TTS voices:
- `Polly.Joanna` (Female, US English) - **Recommended**
- `Polly.Matthew` (Male, US English)
- `Polly.Amy` (Female, British English)
- `Polly.Brian` (Male, British English)
- `Polly.Conchita` (Female, Spanish)
- `Polly.Enrique` (Male, Spanish)

Speech recognition models:
- `default` - Standard speech recognition
- `phone_call` - Optimized for phone calls
- `enhanced` - Higher accuracy (additional cost)

## 🧪 Step 5: Testing the Integration

### 5.1 Test SMS Integration

Send a test SMS to your Twilio number:

```bash
# Send SMS to your Twilio number
# Text message: "Hello, I need help with my appointment"
```

Expected response from MedinovAI:
```
👋 Hello! I'm MedinovAI, your virtual healthcare assistant. 

I can help you with:
• Schedule appointments
• Check appointment status  
• General health questions
• Connect you with our team

How can I assist you today?
```

### 5.2 Test Voice Integration

Call your Twilio number and speak:

```
You: "Hello, I need to schedule an appointment"
```

Expected response:
```
MedinovAI: "Hello! I'm MedinovAI, your virtual healthcare assistant. 
I heard you'd like to schedule an appointment. I can help you with that. 
What type of appointment are you looking for?"
```

### 5.3 Webhook Testing Tool

Use the Twilio Console webhook testing tool:

1. Go to **Console > Runtime > TwiML Bins**
2. Create a test TwiML response
3. Test webhook endpoints manually

## 🔐 Step 6: Security Configuration

### 6.1 Webhook Validation

Enable webhook signature validation for security:

```bash
# Add to environment
TWILIO_WEBHOOK_VALIDATION=true
WEBHOOK_SECRET=your-webhook-secret-key
```

### 6.2 IP Whitelisting (Optional)

For additional security, whitelist Twilio IP addresses:

```
# Twilio IP ranges (as of 2024)
54.172.60.0/23
54.244.51.0/24
54.171.127.192/27
# Check Twilio docs for latest IPs
```

## 📊 Step 7: Monitoring and Analytics

### 7.1 Twilio Console Monitoring

Monitor usage in Twilio Console:
- **Monitor > Logs > Messaging** (SMS logs)
- **Monitor > Logs > Voice** (Call logs)
- **Monitor > Usage** (Billing and usage)

### 7.2 Custom Analytics

MedinovAI provides built-in analytics:
- SMS conversation metrics
- Voice call duration and outcomes
- User satisfaction scores
- Escalation rates

Access via: `https://your-domain.com/admin/analytics`

## 💰 Step 8: Billing and Usage

### 8.1 Understanding Costs

**SMS Pricing (US)**:
- Outbound SMS: ~$0.0075 per message
- Inbound SMS: ~$0.0075 per message

**Voice Pricing (US)**:
- Inbound calls: ~$0.0085 per minute
- Outbound calls: ~$0.013 per minute
- TTS usage: ~$0.0004 per character

**Phone Number**:
- ~$1.00 per month

### 8.2 Set Billing Alerts

1. Go to **Console > Settings > Billing**
2. Set usage alerts at appropriate thresholds:
   - $50 for small practices
   - $200 for medium practices
   - $500+ for large practices

## 🚨 Step 9: Troubleshooting

### 9.1 Common Issues

**SMS not receiving responses:**
```bash
# Check webhook URL in Twilio Console
# Verify server is accessible publicly
curl -X POST https://your-domain.com/api/webhooks/twilio/sms
```

**Voice calls failing:**
```bash
# Check TwiML response format
# Verify voice webhook configuration
# Test with simple TwiML first
```

**Webhook validation errors:**
```bash
# Disable validation temporarily for testing
TWILIO_WEBHOOK_VALIDATION=false

# Check signature validation in logs
```

### 9.2 Debug Endpoints

Test your webhook endpoints:

```bash
# Test SMS webhook
curl -X POST https://your-domain.com/api/webhooks/twilio/sms \
  -d "From=+1234567890" \
  -d "To=+0987654321" \
  -d "Body=Test message"

# Test voice webhook  
curl -X POST https://your-domain.com/api/webhooks/twilio/voice \
  -d "From=+1234567890" \
  -d "To=+0987654321"
```

### 9.3 Logs and Monitoring

Check application logs for Twilio integration:

```bash
# View logs
docker-compose logs -f chatbot-api

# Filter for Twilio logs
docker-compose logs chatbot-api | grep -i twilio
```

## 📈 Step 10: Advanced Configuration

### 10.1 Multi-Language Support

Configure different TTS voices for different languages:

```bash
# Environment variables for multi-language
TWILIO_TTS_VOICE_EN=Polly.Joanna     # English
TWILIO_TTS_VOICE_ES=Polly.Conchita   # Spanish  
TWILIO_TTS_VOICE_ZH=Polly.Zhiyu     # Chinese
```

### 10.2 Business Hours

Configure different responses for business hours:

```bash
# Business hours configuration
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=17:00
BUSINESS_TIMEZONE=America/New_York
AFTER_HOURS_MESSAGE="Thanks for calling! We're currently closed but will respond during business hours."
```

### 10.3 Call Routing

Set up intelligent call routing:

```bash
# Routing configuration
ENABLE_CALL_ROUTING=true
EMERGENCY_KEYWORDS=emergency,urgent,chest pain,difficulty breathing
EMERGENCY_ESCALATION_NUMBER=+1234567890
```

## ✅ Step 11: Go-Live Checklist

Before going live with patients:

- [ ] Test SMS functionality thoroughly
- [ ] Test voice calls with various scenarios
- [ ] Verify webhook security is enabled
- [ ] Set up monitoring and alerting
- [ ] Configure billing alerts
- [ ] Test emergency escalation scenarios
- [ ] Train staff on the system
- [ ] Prepare patient communication about the new feature

## 📞 Support and Next Steps

### Twilio Support
- **Twilio Help Center**: https://help.twilio.com
- **Twilio Support**: Available in console
- **Community Forum**: https://community.twilio.com

### MedinovAI Support
- **Technical Issues**: Create GitHub issue
- **Emergency Support**: Contact myOnsite Healthcare
- **Feature Requests**: Submit via admin panel

---

**🎉 Congratulations!** Your Twilio integration is now complete. Patients can now interact with MedinovAI via SMS and voice calls, providing 24/7 automated healthcare assistance with intelligent escalation to human agents when needed.

For advanced customization and enterprise features, please contact the myOnsite Healthcare team. 