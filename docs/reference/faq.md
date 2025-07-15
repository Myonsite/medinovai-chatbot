# Frequently Asked Questions (FAQ) - MedinovAI Chatbot

Quick answers to the most commonly asked questions about the MedinovAI Chatbot system.

## 🔍 Quick Navigation

- [General Questions](#-general-questions)
- [Setup & Installation](#️-setup--installation)
- [Authentication & Security](#-authentication--security)
- [Chat Features](#-chat-features)
- [Integration](#-integration)
- [Compliance & Legal](#️-compliance--legal)
- [Troubleshooting](#-troubleshooting)
- [Billing & Pricing](#-billing--pricing)
- [Technical Specifications](#️-technical-specifications)

---

## 🌟 General Questions

### What is MedinovAI Chatbot?

MedinovAI is a HIPAA-compliant AI-powered healthcare chatbot that provides 24/7 patient support through multiple channels (web, SMS, voice). It uses advanced natural language processing to understand patient inquiries and provide accurate, contextual healthcare information while maintaining strict compliance with healthcare regulations.

**Key Features:**
- 🤖 AI-powered medical responses using GPT-4
- 📱 Multi-channel support (web, SMS, voice)
- 🔒 HIPAA/GDPR compliant architecture
- 🌍 Multi-language support (English, Spanish, Chinese, Hindi)
- 👨‍⚕️ Seamless human escalation to healthcare staff
- 📊 Advanced analytics and reporting

### Who should use MedinovAI?

**Primary Users:**
- 🏥 Healthcare providers and clinics
- 🏢 Healthcare organizations
- 💼 Medical practice management companies
- 🏫 Healthcare educational institutions
- 🏛️ Government healthcare agencies

**Typical Use Cases:**
- Patient triage and symptom assessment
- Appointment scheduling and reminders
- Medication reminders and information
- Post-treatment follow-up
- General health education
- Emergency guidance and escalation

### How does MedinovAI ensure accuracy?

**Multi-layered Accuracy Approach:**
1. **Knowledge Base**: Curated medical content from verified sources
2. **RAG Pipeline**: Retrieval-Augmented Generation for contextual accuracy
3. **Source Attribution**: All responses include source references
4. **Confidence Scoring**: AI responses include confidence levels
5. **Human Escalation**: Automatic escalation for complex or low-confidence queries
6. **Continuous Learning**: Regular updates based on healthcare professional feedback

**Safety Measures:**
- Emergency symptom detection with immediate escalation
- Disclaimer statements for all medical advice
- Clear boundaries on diagnostic capabilities
- Regular content review by medical professionals

### What languages does MedinovAI support?

**Currently Supported:**
- 🇺🇸 **English** - Full feature support
- 🇪🇸 **Spanish** - Full feature support
- 🇨🇳 **Simplified Chinese** - Full feature support
- 🇮🇳 **Hindi** - Full feature support

**Coming Soon:**
- 🇵🇹 Portuguese (Q2 2024)
- 🇫🇷 French (Q3 2024)
- 🇩🇪 German (Q4 2024)

**Language Features:**
- Real-time translation during conversations
- Language detection and automatic switching
- Culturally appropriate responses
- Localized medical terminology

---

## ⚙️ Setup & Installation

### How long does deployment take?

**Deployment Timeframes:**

| Environment | Time Required | Complexity |
|-------------|---------------|------------|
| **Demo/Evaluation** | 5-10 minutes | 🟢 Easy |
| **Development** | 1-2 hours | 🟡 Medium |
| **Staging** | 2-4 hours | 🟡 Medium |
| **Production** | 4-8 hours | 🔴 Complex |

**Factors Affecting Deployment Time:**
- AWS infrastructure setup
- SSL certificate provisioning
- DNS propagation
- Security configuration
- Compliance validation
- Staff training requirements

### What are the system requirements?

**Production Requirements:**

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **CPU** | 4 vCPUs | 8 vCPUs | Auto-scaling capable |
| **Memory** | 8 GB RAM | 16 GB RAM | For AI processing |
| **Storage** | 100 GB | 500 GB | Includes backups |
| **Database** | db.t3.medium | db.r5.large | PostgreSQL 13+ |
| **Network** | 1 Gbps | 10 Gbps | High availability |

**Cloud Provider Support:**
- ✅ **AWS** (Primary, fully tested)
- 🔄 **Azure** (In development)
- 📋 **Google Cloud** (Planned)
- 🏢 **On-premises** (Enterprise only)

### Do I need technical expertise to set up MedinovAI?

**Setup Options:**

1. **Managed Setup** (Recommended)
   - Our team handles complete deployment
   - 4-6 week implementation timeline
   - Includes staff training and support
   - HIPAA compliance certification included

2. **Guided Self-Setup**
   - Step-by-step documentation provided
   - Technical support during setup
   - 2-3 week implementation timeline
   - Basic technical knowledge required

3. **Independent Setup**
   - Complete documentation access
   - Community support
   - 1-2 week implementation timeline
   - Advanced technical knowledge required

**Required Skills for Self-Setup:**
- AWS/Cloud platform experience
- Docker and Kubernetes knowledge
- Database management
- SSL certificate management
- Basic networking understanding

### Can I try MedinovAI before purchasing?

**Trial Options:**

1. **Online Demo** (Immediate)
   - Live demo at https://demo.medinovai.com
   - Pre-loaded sample conversations
   - No registration required
   - Full feature exploration

2. **Docker Demo** (5 minutes)
   - Complete local environment
   - Your own data and configuration
   - No external dependencies
   - See [Quick Start Guide](../deployment/quick-start.md)

3. **30-Day Free Trial** (Full Production)
   - Complete production environment
   - Up to 1,000 conversations
   - Full support included
   - HIPAA compliance enabled

**Contact for Trial:**
- 📧 Email: trial@myonsitehealthcare.com
- 📞 Phone: +1-XXX-XXX-XXXX
- 💬 Live Chat: https://myonsitehealthcare.com/chat

---

## 🔐 Authentication & Security

### How does SMS authentication work?

**SMS Authentication Flow:**

1. **Phone Number Entry**
   - User enters phone number in international format
   - System validates number format and carrier capability
   - Rate limiting applied (5 attempts per hour)

2. **Code Delivery**
   - 6-digit verification code sent via Twilio
   - Code expires in 10 minutes
   - Delivery typically takes 5-30 seconds

3. **Code Verification**
   - User enters received code
   - System validates code and creates session
   - JWT token issued for API access

**Security Features:**
- 🔒 Encrypted code storage
- ⏰ Time-based expiration
- 🚫 Single-use codes
- 📊 Rate limiting and abuse prevention
- 🕵️ Fraud detection

### Is my data secure with MedinovAI?

**Security Measures:**

| Layer | Protection | Standard |
|-------|------------|----------|
| **Encryption in Transit** | TLS 1.3 | Industry Standard |
| **Encryption at Rest** | AES-256 | FIPS 140-2 |
| **Database Encryption** | Field-level encryption | PHI Protection |
| **Backup Encryption** | Client-side encryption | Zero-knowledge |
| **Network Security** | VPC, WAF, DDoS protection | AWS Shield |

**Compliance Certifications:**
- ✅ HIPAA Compliant (BAA available)
- ✅ SOC 2 Type II (In progress)
- ✅ GDPR Compliant
- 🔄 ISO 27001 (Planned 2024)
- 🔄 FedRAMP (Under evaluation)

**Data Handling:**
- PHI automatically detected and protected
- Data residency controls available
- Right to be forgotten implementation
- Audit trails for all data access
- Regular security assessments

### What OAuth providers are supported?

**Supported Providers:**

| Provider | Status | Use Case |
|----------|--------|----------|
| **Google** | ✅ Active | Gmail integration, calendar sync |
| **Microsoft** | ✅ Active | Office 365, Azure AD |
| **Apple** | 🔄 Beta | iOS native apps |
| **Facebook** | 📋 Planned | Patient engagement |
| **Custom OIDC** | ✅ Active | Enterprise SSO |

**Enterprise SSO:**
- SAML 2.0 support
- Active Directory integration
- Custom attribute mapping
- Just-in-time provisioning
- Multi-factor authentication

### How do you handle PHI (Protected Health Information)?

**PHI Protection Strategy:**

1. **Detection and Classification**
   ```
   - Automatic PHI detection using ML models
   - Pattern matching for SSN, DOB, addresses
   - Medical terminology identification
   - Real-time classification during conversations
   ```

2. **Encryption and Storage**
   ```
   - Field-level encryption for PHI fields
   - Separate encryption keys per organization
   - Hardware security modules (HSM) for key management
   - Encrypted database columns and backups
   ```

3. **Access Controls**
   ```
   - Role-based access control (RBAC)
   - Principle of least privilege
   - Audit logging for all PHI access
   - Time-limited access tokens
   ```

4. **Data Lifecycle Management**
   ```
   - Automatic data retention policies
   - Secure data deletion procedures
   - Backup encryption and rotation
   - Geographic data residency controls
   ```

---

## 💬 Chat Features

### What types of conversations can MedinovAI handle?

**Primary Conversation Types:**

1. **Symptom Assessment**
   - General symptom evaluation
   - Severity assessment
   - Triage recommendations
   - Emergency detection

2. **Appointment Management**
   - Scheduling assistance
   - Rescheduling and cancellations
   - Reminder notifications
   - Wait time estimates

3. **Medication Support**
   - Medication information
   - Dosage reminders
   - Side effect guidance
   - Drug interaction checks

4. **Health Education**
   - Disease information
   - Prevention guidance
   - Lifestyle recommendations
   - Follow-up care instructions

5. **Administrative Support**
   - Insurance inquiries
   - Billing questions
   - Document requests
   - Contact information

**Conversation Capabilities:**
- Context awareness across messages
- Multi-turn conversations
- File and image sharing
- Voice message support
- Real-time language translation

### When does the system escalate to human agents?

**Automatic Escalation Triggers:**

1. **Emergency Situations**
   - Severe symptoms (chest pain, difficulty breathing)
   - Mental health crises
   - Medication emergencies
   - Urgent care requirements

2. **Confidence Thresholds**
   - AI confidence below 70%
   - Complex medical questions
   - Conflicting information
   - Unclear user intent

3. **User Requests**
   - Explicit request for human agent
   - Dissatisfaction with AI responses
   - Complex scheduling needs
   - Sensitive topics

4. **System Limitations**
   - Technical issues
   - Service unavailability
   - Data access restrictions
   - Compliance requirements

**Escalation Process:**
1. User notified of escalation
2. Queue position and wait time provided
3. Conversation context transferred to agent
4. Seamless handoff with full history
5. Option to return to AI after human interaction

### Can patients upload images or documents?

**Supported File Types:**

| Category | Formats | Max Size | Use Cases |
|----------|---------|----------|-----------|
| **Images** | JPG, PNG, WEBP | 10 MB | Symptoms, rashes, wounds |
| **Documents** | PDF, DOC, DOCX | 10 MB | Lab results, prescriptions |
| **Medical Scans** | DICOM, JPG | 25 MB | X-rays, MRIs, CT scans |
| **Voice** | MP3, WAV, M4A | 25 MB | Voice messages |

**Image Analysis Features:**
- Automatic image quality assessment
- Basic visual symptom recognition
- Privacy-preserving processing
- Secure encrypted storage
- Automatic PHI redaction in metadata

**Security Considerations:**
- Virus scanning for all uploads
- Metadata stripping for privacy
- Encrypted storage with expiration
- Access logging and audit trails
- HIPAA-compliant handling

### How accurate is the medical information provided?

**Accuracy Metrics:**

| Measure | Current Performance | Target |
|---------|-------------------|--------|
| **Medical Accuracy** | 92% | >90% |
| **Source Attribution** | 98% | >95% |
| **Appropriate Escalation** | 94% | >90% |
| **User Satisfaction** | 4.3/5 | >4.0/5 |
| **Healthcare Provider Approval** | 87% | >85% |

**Quality Assurance Process:**
1. **Content Review**
   - Board-certified physicians review responses
   - Regular content audits and updates
   - Evidence-based medical guidelines
   - Peer review process

2. **Continuous Monitoring**
   - Real-time response quality scoring
   - Healthcare provider feedback integration
   - Patient outcome tracking
   - Regular model retraining

3. **Safety Measures**
   - Conservative recommendations
   - Clear limitations statements
   - Emergency escalation protocols
   - Medical disclaimer requirements

---

## 🔌 Integration

### How does MedinovAI integrate with existing systems?

**Integration Options:**

1. **EHR Systems**
   - HL7 FHIR R4 standard support
   - Epic, Cerner, Allscripts connectors
   - Patient data synchronization
   - Appointment scheduling integration

2. **Practice Management Systems**
   - Billing system integration
   - Patient scheduling sync
   - Insurance verification
   - Revenue cycle management

3. **Communication Platforms**
   - Twilio SMS/Voice integration
   - 3CX phone system support
   - Mattermost team chat
   - Email notification systems

4. **Analytics and BI**
   - PowerBI dashboard integration
   - Tableau reporting connectors
   - Custom API endpoints
   - Real-time data streaming

**API Integration:**
```javascript
// Example integration
const medinovai = new MedinovAIClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.yourdomain.com'
});

// Start conversation
const conversation = await medinovai.conversations.create({
  channel: 'web',
  patientId: 'patient-123',
  initialMessage: 'I have a question about my symptoms'
});
```

### Can MedinovAI integrate with my EHR system?

**Supported EHR Systems:**

| EHR System | Integration Level | Features |
|------------|------------------|----------|
| **Epic** | ✅ Full | FHIR, MyChart integration |
| **Cerner** | ✅ Full | PowerChart integration |
| **Allscripts** | 🔄 Beta | Basic FHIR support |
| **athenahealth** | 📋 Planned | Q2 2024 release |
| **NextGen** | 📋 Planned | Q3 2024 release |
| **Custom FHIR** | ✅ Full | Any FHIR-compliant system |

**Integration Capabilities:**
- Patient demographics sync
- Appointment scheduling
- Medical history access
- Medication reconciliation
- Care plan integration
- Clinical decision support

**Implementation Process:**
1. **Assessment** (1-2 weeks)
   - EHR version compatibility check
   - Data mapping requirements
   - Security and compliance review

2. **Development** (2-4 weeks)
   - Custom connector development
   - API endpoint configuration
   - Data transformation setup

3. **Testing** (1-2 weeks)
   - Integration testing
   - Data validation
   - Security verification

4. **Deployment** (1 week)
   - Production deployment
   - User training
   - Go-live support

### What APIs are available for custom integrations?

**Available APIs:**

| API Category | Endpoints | Authentication | Rate Limit |
|--------------|-----------|----------------|------------|
| **Chat API** | 15+ endpoints | JWT | 1000/hour |
| **User Management** | 8 endpoints | OAuth2 | 500/hour |
| **Analytics** | 12 endpoints | API Key | 200/hour |
| **Admin** | 20+ endpoints | Admin token | 100/hour |
| **Webhooks** | Event-driven | Signature | Unlimited |

**Key API Features:**
- RESTful design with JSON responses
- Comprehensive OpenAPI/Swagger documentation
- SDKs for Python, JavaScript, Java
- Real-time WebSocket support
- Webhook event notifications

**Sample Integration Scenarios:**
```python
# Python SDK example
from medinovai import MedinovAIClient

client = MedinovAIClient(api_key='your-key')

# Create patient and start conversation
patient = client.patients.create({
    'phone': '+1234567890',
    'name': 'John Doe',
    'date_of_birth': '1980-01-01'
})

conversation = client.conversations.create({
    'patient_id': patient.id,
    'channel': 'api',
    'initial_message': 'Patient needs medication refill'
})

# Monitor conversation
for message in conversation.messages():
    print(f"{message.sender}: {message.content}")
```

---

## ⚖️ Compliance & Legal

### Is MedinovAI HIPAA compliant?

**HIPAA Compliance Status: ✅ FULLY COMPLIANT**

**Compliance Measures:**

1. **Administrative Safeguards**
   - Designated Privacy Officer
   - Workforce training programs
   - Access management procedures
   - Incident response protocols

2. **Physical Safeguards**
   - Secure data centers (AWS)
   - Restricted facility access
   - Workstation security controls
   - Media disposal procedures

3. **Technical Safeguards**
   - Access control systems
   - Audit controls and logging
   - Integrity controls
   - Transmission security

**Business Associate Agreement (BAA):**
- BAA provided with all contracts
- Covers all data processing activities
- Includes breach notification procedures
- Regular compliance audits

**Audit and Monitoring:**
- Continuous compliance monitoring
- Regular third-party assessments
- Automated compliance reporting
- Breach detection and response

### Do you sign Business Associate Agreements (BAAs)?

**Yes, we provide comprehensive BAAs with all healthcare clients.**

**BAA Coverage:**
- All PHI processing activities
- Subcontractor management
- Data breach notification procedures
- Security incident reporting
- Compliance monitoring requirements

**BAA Process:**
1. **Initial Review** (3-5 days)
   - Legal team review
   - Custom clause negotiations
   - Compliance verification

2. **Execution** (1-2 days)
   - Digital signature process
   - Contract finalization
   - Compliance activation

3. **Ongoing Management**
   - Annual compliance reviews
   - Quarterly reporting
   - Incident notifications

### What happens to data if I cancel my subscription?

**Data Retention Policy:**

| Timeframe | Actions | Data Status |
|-----------|---------|-------------|
| **0-30 days** | Full access maintained | ✅ Active |
| **30-90 days** | Read-only access | 🔒 Archived |
| **90-365 days** | Export available on request | 📦 Backup |
| **365+ days** | Secure deletion | ❌ Destroyed |

**Data Export Options:**
- Complete conversation history
- User account information
- Analytics and reporting data
- Configuration settings
- Knowledge base content

**Export Formats:**
- JSON for API integration
- CSV for analytics
- PDF for documentation
- HL7 FHIR for EHR import

**Secure Deletion Process:**
- Cryptographic key destruction
- Multi-pass data overwriting
- Certificate of destruction provided
- Compliance with HIPAA requirements

---

## 🔧 Troubleshooting

### Why am I not receiving SMS codes?

**Common Causes and Solutions:**

1. **Phone Number Issues**
   ```
   ❌ Problem: Invalid format
   ✅ Solution: Use international format (+1234567890)
   
   ❌ Problem: Landline number
   ✅ Solution: Use mobile number only
   
   ❌ Problem: VoIP number
   ✅ Solution: Some VoIP services may not receive SMS
   ```

2. **Carrier Issues**
   ```
   ❌ Problem: Carrier blocking
   ✅ Solution: Contact carrier to whitelist shortcode
   
   ❌ Problem: International restrictions
   ✅ Solution: Verify international SMS is enabled
   ```

3. **Rate Limiting**
   ```
   ❌ Problem: Too many requests
   ✅ Solution: Wait 60 seconds between requests
   
   ❌ Problem: Daily limit exceeded
   ✅ Solution: Try again after 24 hours
   ```

4. **System Issues**
   ```
   ❌ Problem: Twilio service disruption
   ✅ Solution: Check status at status.twilio.com
   
   ❌ Problem: Network delays
   ✅ Solution: Wait up to 5 minutes for delivery
   ```

**Troubleshooting Steps:**
1. Verify phone number format
2. Check carrier compatibility
3. Review rate limiting status
4. Contact support if issues persist

### The chatbot isn't responding correctly

**Response Quality Issues:**

1. **Unclear Responses**
   ```
   Problem: AI provides vague answers
   Solutions:
   - Be more specific in your questions
   - Provide additional context
   - Ask follow-up questions for clarification
   ```

2. **Inappropriate Responses**
   ```
   Problem: AI response seems incorrect
   Solutions:
   - Use the feedback feature to report
   - Request human escalation
   - Rephrase your question differently
   ```

3. **Language Issues**
   ```
   Problem: Response in wrong language
   Solutions:
   - Specify preferred language
   - Check browser language settings
   - Use language selection feature
   ```

4. **Technical Errors**
   ```
   Problem: Error messages or no response
   Solutions:
   - Refresh browser/restart app
   - Check internet connection
   - Try again in a few minutes
   - Contact technical support
   ```

**Performance Optimization:**
- Clear browser cache regularly
- Use supported browsers (Chrome, Firefox, Safari)
- Ensure stable internet connection
- Update to latest app version

### How do I report a bug or issue?

**Reporting Channels:**

1. **In-App Reporting** (Preferred)
   - Use feedback button in chat interface
   - Include conversation ID for context
   - Automatic log collection included

2. **Email Support**
   - 📧 support@myonsitehealthcare.com
   - Include detailed description
   - Attach screenshots if helpful
   - Mention your organization name

3. **Phone Support**
   - 📞 +1-XXX-XXX-XXXX
   - Available 24/7 for critical issues
   - Business hours for general support

4. **Emergency Issues**
   - 🚨 critical@myonsitehealthcare.com
   - For system outages or security concerns
   - Immediate response guarantee

**Information to Include:**
- Error message or unexpected behavior
- Steps to reproduce the issue
- Browser/device information
- Conversation ID (if applicable)
- Organization name and contact info

**Response Times:**
- 🔴 Critical: 15 minutes
- 🟡 High: 4 hours
- 🟢 Medium: 24 hours
- 🔵 Low: 72 hours

---

## 💰 Billing & Pricing

### How does pricing work?

**Pricing Model:**

| Tier | Monthly Conversations | Price/Month | Price/Conversation |
|------|----------------------|-------------|-------------------|
| **Starter** | Up to 1,000 | $299 | $0.30 |
| **Professional** | Up to 5,000 | $999 | $0.20 |
| **Enterprise** | Up to 25,000 | $2,999 | $0.12 |
| **Scale** | Unlimited | Custom | $0.08+ |

**What's Included:**
- ✅ AI-powered conversations
- ✅ Multi-channel support (web, SMS, voice)
- ✅ HIPAA compliance and BAA
- ✅ Basic analytics and reporting
- ✅ Email support
- ✅ Knowledge base access

**Add-On Services:**
- 📊 Advanced analytics: $99/month
- 🔌 EHR integration: $199/month
- 📞 Phone support: $299/month
- 🎓 Staff training: $499/month
- 🛡️ Enhanced security: $199/month

### What counts as a conversation?

**Conversation Definition:**
A conversation is defined as a complete interaction session between a patient and the system, regardless of the number of messages exchanged.

**Conversation Starts:**
- New patient initiates contact
- Returning patient after 24-hour inactivity
- Explicit new conversation request
- Channel switch (web to SMS)

**Conversation Ends:**
- Patient explicitly ends conversation
- 24 hours of inactivity
- Successful issue resolution
- Escalation to human agent (conversation continues under human billing)

**Examples:**
```
✅ Counts as 1 conversation:
Patient: "I have a headache"
AI: "Can you describe the pain?"
Patient: "Sharp, behind my eyes"
AI: "When did it start?"
Patient: "This morning"
AI: "Here are some recommendations..."

✅ Counts as 2 conversations:
Day 1: Patient asks about headache
Day 3: Same patient asks about medication
(24+ hour gap = new conversation)
```

### Are there setup fees?

**Setup Fee Structure:**

| Setup Type | Fee | Timeline | Includes |
|------------|-----|----------|----------|
| **Self-Service** | $0 | Immediate | Documentation access |
| **Guided Setup** | $499 | 1-2 weeks | Technical support |
| **Managed Setup** | $2,999 | 4-6 weeks | Full implementation |
| **Enterprise Setup** | Custom | 6-12 weeks | Custom development |

**Managed Setup Includes:**
- Complete AWS infrastructure deployment
- SSL certificate setup and configuration
- DNS configuration and testing
- Security hardening and compliance setup
- Staff training (up to 10 users)
- 30 days of premium support
- Knowledge base customization
- Integration with existing systems

**Payment Options:**
- One-time setup fee
- Spread over 6 months (no interest)
- Included in annual contracts
- Custom enterprise terms available

### Do you offer discounts for nonprofits?

**Nonprofit Discounts:**

| Organization Type | Discount | Requirements |
|------------------|----------|--------------|
| **501(c)(3) Nonprofits** | 25% | Valid tax-exempt certificate |
| **Community Health Centers** | 30% | FQHC designation |
| **Educational Institutions** | 20% | .edu domain verification |
| **Government Agencies** | 15% | Government contract terms |
| **Startups** | 50% (first year) | <2 years old, <$1M revenue |

**Application Process:**
1. Submit nonprofit application form
2. Provide verification documents
3. Review and approval (3-5 business days)
4. Custom pricing agreement
5. Ongoing compliance verification

**Additional Benefits:**
- Extended payment terms (Net 60)
- Priority support escalation
- Free staff training sessions
- Complimentary setup assistance
- Access to nonprofit community forum

---

## 🛠️ Technical Specifications

### What are the system architecture details?

**High-Level Architecture:**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Core Services │
│                 │    │                 │    │                 │
│ • Web Portal    │ -> │ • Load Balancer │ -> │ • Chat API      │
│ • Admin UI      │    │ • WAF/Security  │    │ • AI Service    │
│ • Mobile App    │    │ • Rate Limiting │    │ • RAG Pipeline  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   Data Layer    │ <-----------┘
                       │                 │
                       │ • PostgreSQL    │
                       │ • Redis Cache   │
                       │ • Vector DB     │
                       │ • S3 Storage    │
                       └─────────────────┘
```

**Technology Stack:**

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend** | Next.js | 14.x | Web interface |
| **API** | FastAPI | 0.104+ | REST API |
| **Database** | PostgreSQL | 15+ | Primary data |
| **Cache** | Redis | 7.x | Session/cache |
| **AI/ML** | OpenAI GPT-4 | Latest | Language model |
| **Vector DB** | Chroma | 0.4+ | RAG pipeline |
| **Queue** | Celery | 5.3+ | Background tasks |
| **Monitoring** | Prometheus | 2.45+ | Metrics |
| **Orchestration** | Kubernetes | 1.28+ | Container management |

### What are the API rate limits?

**Rate Limit Tiers:**

| API Category | Requests/Minute | Burst Limit | Window |
|--------------|----------------|-------------|--------|
| **Authentication** | 5 | 10 | 1 minute |
| **Chat Messages** | 30 | 60 | 1 minute |
| **File Upload** | 3 | 5 | 1 minute |
| **Analytics** | 60 | 120 | 1 minute |
| **Admin Operations** | 20 | 40 | 1 minute |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1642248300
X-RateLimit-Retry-After: 60
```

**Handling Rate Limits:**
```javascript
// Example retry logic
async function apiCallWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      
      if (response.status === 429) {
        const retryAfter = response.headers.get('X-RateLimit-Retry-After');
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        continue;
      }
      
      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
}
```

### What browsers and devices are supported?

**Supported Browsers:**

| Browser | Minimum Version | Features | Support Level |
|---------|----------------|----------|---------------|
| **Chrome** | 90+ | Full | ✅ Primary |
| **Firefox** | 88+ | Full | ✅ Primary |
| **Safari** | 14+ | Full | ✅ Primary |
| **Edge** | 90+ | Full | ✅ Primary |
| **Opera** | 76+ | Limited | 🟡 Secondary |
| **Internet Explorer** | N/A | Not supported | ❌ None |

**Mobile Support:**

| Platform | App Type | Features |
|----------|----------|----------|
| **iOS** | PWA + Native SDK | Full feature support |
| **Android** | PWA + Native SDK | Full feature support |
| **Responsive Web** | All mobile browsers | Optimized experience |

**Device Requirements:**
- **Minimum Screen**: 320px width
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 100MB for offline capabilities
- **Network**: 3G minimum, WiFi/4G+ recommended

**Accessibility Features:**
- WCAG 2.1 AA compliance
- Screen reader support
- Keyboard navigation
- High contrast mode
- Font size adjustment
- Voice input support

---

## 📞 Still Need Help?

**Contact Information:**

| Support Type | Contact Method | Hours |
|--------------|----------------|-------|
| **General Support** | support@myonsitehealthcare.com | 24/7 |
| **Technical Issues** | technical@myonsitehealthcare.com | 24/7 |
| **Sales Inquiries** | sales@myonsitehealthcare.com | Business hours |
| **Emergency Support** | +1-XXX-XXX-XXXX | 24/7 |

**Self-Service Resources:**
- 📚 [Complete Documentation](../index.md)
- 🎥 [Video Tutorials](https://youtube.com/medinovai)
- 💬 [Community Forum](https://community.medinovai.com)
- 📖 [Knowledge Base](https://help.medinovai.com)

**Response Times:**
- 🔴 **Critical**: 15 minutes
- 🟡 **High**: 4 hours  
- 🟢 **Medium**: 24 hours
- 🔵 **Low**: 72 hours

---

*Last updated: January 15, 2024 | Version: 2.1.0*

*Can't find what you're looking for? [Contact our support team](mailto:support@myonsitehealthcare.com) or check our [complete documentation](../index.md).* 