# MedinovAI Chatbot - AI-Powered Healthcare Assistant

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![HIPAA](https://img.shields.io/badge/HIPAA-compliant-green.svg)
![GDPR](https://img.shields.io/badge/GDPR-compliant-green.svg)

## 🏥 Project Overview

MedinovAI Chatbot is an AI-powered, HIPAA-compliant healthcare assistant for myOnsite Healthcare. It provides omnichannel support through web chat, SMS, and voice calls with intelligent escalation to human agents and comprehensive audit logging.

### Key Features

- **🤖 AI-Powered RAG**: Retrieval-Augmented Generation for accurate, document-grounded responses
- **📱 Multi-Channel**: Web chat, SMS (Twilio), Voice calls (3CX), Mattermost integration
- **🔒 HIPAA/GDPR Compliant**: End-to-end encryption, PHI protection, audit logging
- **🌍 Multilingual**: English, Spanish, Chinese, Hindi (configurable for more)
- **🔄 Smart Escalation**: Automatic routing to available CSRs with presence detection
- **⚡ Real-time**: Live chat handoffs, voice biometrics, SMS verification
- **📊 Analytics**: Comprehensive dashboards and reporting for management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Widget   │    │   SMS Gateway   │    │   Voice (3CX)   │
│   (WordPress)   │    │   (Twilio)      │    │   Integration   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    AI Orchestrator       │
                    │  (FastAPI + WebSocket)   │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
    ┌─────┴─────┐        ┌────────┴────────┐        ┌─────┴─────┐
    │    RAG    │        │   Mattermost    │        │   MCP     │
    │  Engine   │        │   Integration   │        │   API     │
    │ (Vector   │        │  (Escalation)   │        │(Order/    │
    │   DB)     │        │                 │        │Schedule)  │
    └───────────┘        └─────────────────┘        └───────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- AWS CLI configured
- Terraform (for infrastructure)

### Local Development

1. **Clone and Setup**
   ```bash
   git clone https://github.com/myonsite-healthcare/MedinovAI-Chatbot.git
   cd MedinovAI-Chatbot
   cp .env.example .env
   # Edit .env with your configurations
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Install Dependencies**
   ```bash
   # Backend
   cd src && pip install -r requirements.txt
   
   # Frontend
   cd admin-ui && npm install
   ```

4. **Run Development Servers**
   ```bash
   # Backend API
   cd src && python main.py
   
   # Admin UI
   cd admin-ui && npm run dev
   ```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# AI Configuration
OPENAI_API_KEY=your-openai-key
AI_MODEL=gpt-4
DEFAULT_LANGUAGE=en

# Twilio (SMS/Voice)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Mattermost
MATTERMOST_URL=https://chat.myonsitehealthcare.com
MATTERMOST_TOKEN=your-bot-token
MATTERMOST_TEAM_ID=your-team-id

# Database & Vector Store
VECTOR_DB_URL=your-vector-db-url
DATABASE_URL=postgresql://user:pass@localhost/medinovai

# AWS Services
AWS_REGION=us-east-1
AWS_KMS_KEY_ID=your-kms-key
AWS_SECRETS_MANAGER_ARN=your-secrets-arn

# 3CX Integration
CX3_SERVER_URL=your-3cx-server
CX3_USERNAME=your-username
CX3_PASSWORD=your-password

# Security & Compliance
ENCRYPTION_KEY=your-encryption-key
PHI_REDACTION_ENABLED=true
AUDIT_LOGGING_ENABLED=true
```

### Multi-Modal Language Configuration

The chatbot supports multiple languages and can be configured in several ways:

1. **System-wide default**: Set `DEFAULT_LANGUAGE=en|es|zh|hi`
2. **User preference**: Store language preference in user session
3. **Auto-detection**: Automatically detect language from user input

To add new languages:
```python
# In src/utils/language_config.py
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish', 
    'zh': 'Chinese',
    'hi': 'Hindi',
    'fr': 'French',  # Add new language
}
```

### Authentication Options

The system supports dual authentication methods (configurable):

1. **SMS Verification** (via Twilio)
   - Phone number + OTP verification
   - Fallback to voice call for OTP

2. **OAuth2 Login** 
   - Integration with myOnsite patient portal
   - Google, Microsoft, or custom OAuth providers

Configure in Admin UI or via environment:
```bash
AUTH_PRIMARY_METHOD=sms|oauth2
AUTH_FALLBACK_ENABLED=true
SMS_OTP_EXPIRY=300  # 5 minutes
OAUTH2_PROVIDER=google|microsoft|custom
```

## 📚 Integration Guides

### Twilio Setup

1. **Account Configuration**
   - Create Twilio account at https://console.twilio.com
   - Get Account SID and Auth Token from console
   - Purchase phone number for SMS/Voice

2. **Webhook Configuration**
   ```bash
   # SMS Webhook URL
   https://your-domain.com/api/webhooks/twilio/sms
   
   # Voice Webhook URL  
   https://your-domain.com/api/webhooks/twilio/voice
   ```

3. **TwiML Configuration**
   ```xml
   <!-- Voice response example -->
   <Response>
       <Say voice="Polly.Joanna">
           Hello, you've reached myOnsite's virtual assistant.
       </Say>
       <Gather input="speech" action="/api/voice/process">
           <Say>How can I help you today?</Say>
       </Gather>
   </Response>
   ```

### Mattermost Integration

1. **Bot Account Setup**
   - Login to Mattermost as admin
   - Go to Integrations > Bot Accounts
   - Create new bot: `medinovai-assistant`
   - Copy access token

2. **Channel Configuration**
   ```bash
   # Add bot to channels
   /invite @medinovai-assistant
   
   # Set up escalation channels
   #support-escalation
   #ai-console
   #csr-ops
   ```

3. **Presence Detection**
   ```python
   # Auto-configured in mattermost-bot/presence_monitor.py
   # Monitors user status and reassigns tickets
   ```

### 3CX Phone System Integration

1. **SIP Configuration**
   - Create SIP extension for AI bot
   - Configure trunk settings
   - Set up call routing rules

2. **API Integration**
   ```python
   # 3CX REST API calls for call management
   # Configured in src/adapters/cx3_adapter.py
   ```

## 🧪 Testing

### Run Test Suite

```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# All tests with coverage
pytest --cov=src tests/
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: API and service integration  
- **E2E Tests**: Full conversation flows
- **Security Tests**: HIPAA compliance validation
- **Performance Tests**: Load and stress testing

## 🚢 Deployment

### Infrastructure Provisioning

```bash
cd infra/
terraform init
terraform plan -var-file="environments/prod.tfvars"
terraform apply
```

### Docker Deployment

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

### AWS ECS Deployment

```bash
# Using GitHub Actions workflow
git push origin main  # Triggers auto-deployment
```

## 🔒 Security & Compliance

### HIPAA Compliance

- **Encryption**: All data encrypted in transit (TLS 1.3) and at rest (AES-256)
- **Access Control**: Role-based access with multi-factor authentication
- **Audit Logging**: Complete audit trail of all PHI access
- **Data Minimization**: Only necessary PHI collected and stored
- **Incident Response**: Automated breach detection and notification

### GDPR Compliance

- **Consent Management**: Explicit consent collection and management
- **Data Subject Rights**: Automated tools for access, rectification, erasure
- **Privacy by Design**: Built-in privacy protections
- **Data Processing Records**: Complete processing activity logs
- **Breach Notification**: 72-hour breach notification system

### Security Features

- **Secret Management**: AWS Secrets Manager integration
- **PHI Redaction**: Automatic PII/PHI detection and masking
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: API and conversation rate limits
- **Vulnerability Scanning**: Continuous dependency and code scanning

## 📊 Monitoring & Analytics

### Dashboards

- **Real-time Metrics**: Active conversations, response times, escalation rates
- **Daily Reports**: Volume, resolution rates, user satisfaction
- **Weekly Trends**: Usage patterns, popular queries, performance metrics  
- **Monthly Executive Summary**: ROI metrics, compliance status, growth trends

### Key Metrics

- **Resolution Rate**: Target ≥80% automated resolution
- **Response Time**: Target <3 seconds for chat/SMS, <2 seconds for voice
- **Escalation Accuracy**: Target ≥95% correct escalation decisions
- **User Satisfaction**: Target ≥90% CSAT scores
- **Uptime**: Target 99.9% availability

## 🤝 Development Guidelines

### AI-First Development

This project follows AI-first development principles:

- **Cursor Integration**: Optimized for Cursor AI pair programming
- **Automated Testing**: AI-generated test cases and validation
- **Code Generation**: Template-driven component generation
- **Documentation**: Auto-updated documentation from code changes

### Contributing

1. Create feature branch from `chatbot` branch
2. Implement changes with comprehensive tests
3. Ensure all CI checks pass (security, tests, linting)
4. Create pull request with detailed description
5. Require at least 1 code review approval
6. Automated deployment after merge

### Code Standards

- **Python**: Black formatting, flake8 linting, type hints
- **TypeScript**: ESLint, Prettier, strict type checking
- **Documentation**: Comprehensive docstrings and API docs
- **Testing**: Minimum 80% code coverage required

## 📋 API Documentation

### REST API Endpoints

```
POST /api/chat/message          # Send chat message
GET  /api/chat/history         # Get conversation history  
POST /api/auth/sms-verify      # SMS verification
POST /api/auth/oauth2          # OAuth2 login
GET  /api/health               # Health check
POST /api/webhooks/twilio/sms  # Twilio SMS webhook
POST /api/webhooks/twilio/voice # Twilio voice webhook
```

### WebSocket Events

```
connect                        # Initial connection
message                       # Send/receive messages
typing                        # Typing indicators
agent_join                    # Human agent joins
disconnect                    # Clean disconnection
```

Complete API documentation available at `/docs/api/`

## 🆘 Support & Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check Twilio credentials
   - Verify phone number format
   - Confirm SMS delivery status

2. **Voice Integration Issues**  
   - Verify 3CX SIP configuration
   - Check network connectivity
   - Review call routing rules

3. **Mattermost Connection**
   - Validate bot token permissions
   - Check channel access rights
   - Verify webhook URLs

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check service health
curl http://localhost:8000/api/health

# View real-time logs  
docker-compose logs -f chatbot-api
```

### Support Channels

- **Technical Issues**: Create GitHub issue
- **Security Concerns**: security@myonsitehealthcare.com  
- **Compliance Questions**: compliance@myonsitehealthcare.com
- **Emergency Support**: +1-XXX-XXX-XXXX (24/7)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- OpenAI for GPT model integration
- Twilio for communications infrastructure  
- Mattermost for team collaboration platform
- AWS for cloud infrastructure and security services
- The myOnsite Healthcare team for domain expertise and testing

---

**Built with ❤️ by the MedinovAI Team**

For more information, visit: https://myonsitehealthcare.com
