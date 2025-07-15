# Chat API Documentation

The MedinovAI Chat API provides real-time messaging capabilities through both REST endpoints and WebSocket connections, enabling seamless patient-AI conversations across multiple channels.

## Overview

The Chat API supports:
- **Real-time Messaging**: WebSocket connections for instant communication
- **Multi-Channel Support**: Web, SMS, and voice integration
- **Conversation Management**: Context preservation and history tracking
- **AI Integration**: Seamless integration with RAG pipeline and LLM models
- **Human Escalation**: Automatic and manual escalation to healthcare staff

## Base URL

```
Production: https://api.myonsitehealthcare.com
Staging: https://staging-api.myonsitehealthcare.com
Development: http://localhost:8000
```

## Authentication

All chat API endpoints require authentication. Include the JWT token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

---

## WebSocket Connection

### 1. **Establish WebSocket Connection**

```javascript
const ws = new WebSocket('wss://api.myonsitehealthcare.com/ws/chat');
// Development: ws://localhost:8000/ws/chat

// Include authentication in connection
const wsAuth = new WebSocket(`wss://api.myonsitehealthcare.com/ws/chat?token=${accessToken}`);
```

### 2. **WebSocket Events**

#### Connection Events
```javascript
ws.onopen = function(event) {
    console.log('Connected to chat');
    // Send authentication if not included in URL
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your-jwt-token'
    }));
};

ws.onclose = function(event) {
    console.log('Disconnected from chat');
    // Implement reconnection logic
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

#### Message Events
```javascript
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'message':
            handleNewMessage(message);
            break;
        case 'typing':
            handleTypingIndicator(message);
            break;
        case 'escalation':
            handleEscalation(message);
            break;
        case 'error':
            handleError(message);
            break;
    }
};
```

### 3. **Message Format**

#### Send Message
```json
{
    "type": "message",
    "content": "Hello, I have a question about my symptoms",
    "message_type": "text",
    "metadata": {
        "channel": "web",
        "language": "en",
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

#### Receive Message
```json
{
    "type": "message",
    "message_id": "msg_123456789",
    "conversation_id": "conv_987654321",
    "sender": "ai",
    "content": "Hello! I'm here to help with your health questions. What symptoms are you experiencing?",
    "message_type": "text",
    "timestamp": "2024-01-15T10:30:01Z",
    "metadata": {
        "confidence": 0.95,
        "response_time": 1.2,
        "model_used": "gpt-4-turbo"
    }
}
```

---

## REST API Endpoints

### 1. **Conversation Management**

#### Start New Conversation

```http
POST /api/chat/conversations
Content-Type: application/json
Authorization: Bearer <access_token>

{
    "channel": "web",
    "language": "en",
    "initial_message": "Hello, I need help with my symptoms",
    "metadata": {
        "user_agent": "Mozilla/5.0...",
        "source": "patient_portal"
    }
}
```

**Response:**
```json
{
    "conversation_id": "conv_987654321",
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z",
    "channel": "web",
    "language": "en",
    "ai_response": {
        "message_id": "msg_123456789",
        "content": "Hello! I'm here to help with your health questions. What symptoms are you experiencing?",
        "timestamp": "2024-01-15T10:30:01Z"
    }
}
```

#### Get Conversation History

```http
GET /api/chat/conversations/{conversation_id}/messages?limit=50&offset=0
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "conversation_id": "conv_987654321",
    "total_messages": 10,
    "messages": [
        {
            "message_id": "msg_123456789",
            "sender": "user",
            "content": "Hello, I have a question about my symptoms",
            "message_type": "text",
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "message_id": "msg_123456790",
            "sender": "ai",
            "content": "Hello! I'm here to help with your health questions. What symptoms are you experiencing?",
            "message_type": "text",
            "timestamp": "2024-01-15T10:30:01Z",
            "metadata": {
                "confidence": 0.95,
                "sources": ["knowledge_base", "medical_guidelines"]
            }
        }
    ],
    "pagination": {
        "limit": 50,
        "offset": 0,
        "has_more": false
    }
}
```

#### End Conversation

```http
POST /api/chat/conversations/{conversation_id}/end
Authorization: Bearer <access_token>

{
    "reason": "resolved",
    "satisfaction_rating": 5,
    "feedback": "Very helpful, got the information I needed"
}
```

### 2. **Send Message**

#### Send Text Message

```http
POST /api/chat/conversations/{conversation_id}/messages
Content-Type: application/json
Authorization: Bearer <access_token>

{
    "content": "I've been having headaches for the past 2 days",
    "message_type": "text",
    "metadata": {
        "urgency": "normal",
        "language": "en"
    }
}
```

**Response:**
```json
{
    "message_id": "msg_123456791",
    "ai_response": {
        "message_id": "msg_123456792",
        "content": "I understand you're experiencing headaches for 2 days. To better assist you, can you tell me:\n\n1. How would you rate the pain (1-10)?\n2. Where exactly is the headache located?\n3. Have you taken any medication for it?",
        "message_type": "text",
        "timestamp": "2024-01-15T10:35:01Z",
        "suggested_actions": [
            {
                "type": "quick_reply",
                "text": "Pain is 6/10",
                "value": "pain_6"
            },
            {
                "type": "quick_reply", 
                "text": "Pain is 8/10",
                "value": "pain_8"
            }
        ]
    },
    "conversation_status": "active"
}
```

#### Send Voice Message

```http
POST /api/chat/conversations/{conversation_id}/messages
Content-Type: multipart/form-data
Authorization: Bearer <access_token>

Content-Disposition: form-data; name="audio"; filename="voice_message.wav"
Content-Type: audio/wav

[audio file data]

Content-Disposition: form-data; name="metadata"
Content-Type: application/json

{
    "message_type": "voice",
    "duration": 5.2,
    "language": "en"
}
```

#### Send File/Image

```http
POST /api/chat/conversations/{conversation_id}/messages
Content-Type: multipart/form-data
Authorization: Bearer <access_token>

Content-Disposition: form-data; name="file"; filename="symptom_photo.jpg"
Content-Type: image/jpeg

[image file data]

Content-Disposition: form-data; name="metadata"
Content-Type: application/json

{
    "message_type": "image",
    "description": "Photo of skin rash on arm",
    "analysis_requested": true
}
```

### 3. **Escalation Management**

#### Request Human Escalation

```http
POST /api/chat/conversations/{conversation_id}/escalate
Authorization: Bearer <access_token>

{
    "reason": "complex_medical_question",
    "urgency": "normal",
    "notes": "Patient needs detailed medication interaction advice"
}
```

**Response:**
```json
{
    "escalation_id": "esc_456789123",
    "status": "pending",
    "estimated_wait_time": 300,
    "queue_position": 2,
    "escalated_at": "2024-01-15T10:40:00Z",
    "message": "You've been connected to our healthcare team. A staff member will join this conversation shortly."
}
```

#### Check Escalation Status

```http
GET /api/chat/escalations/{escalation_id}
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "escalation_id": "esc_456789123",
    "status": "assigned",
    "assigned_staff": {
        "name": "Sarah Johnson, RN",
        "role": "Registered Nurse",
        "specialties": ["General Medicine", "Patient Education"]
    },
    "estimated_response_time": 60,
    "created_at": "2024-01-15T10:40:00Z",
    "assigned_at": "2024-01-15T10:42:00Z"
}
```

### 4. **Message Actions**

#### Mark as Read

```http
POST /api/chat/conversations/{conversation_id}/messages/{message_id}/read
Authorization: Bearer <access_token>
```

#### Provide Feedback

```http
POST /api/chat/conversations/{conversation_id}/messages/{message_id}/feedback
Authorization: Bearer <access_token>

{
    "rating": "helpful",
    "feedback": "This response answered my question completely",
    "categories": ["accuracy", "helpfulness"]
}
```

#### Request Clarification

```http
POST /api/chat/conversations/{conversation_id}/messages/{message_id}/clarify
Authorization: Bearer <access_token>

{
    "question": "Can you explain what you mean by 'moderate exercise'?"
}
```

---

## Message Types

### 1. **Text Messages**

Standard text-based communication:

```json
{
    "message_type": "text",
    "content": "I have been experiencing chest pain",
    "formatting": {
        "markdown": false,
        "rich_text": false
    }
}
```

### 2. **Rich Text Messages**

Formatted text with markdown support:

```json
{
    "message_type": "rich_text",
    "content": "## Medication Instructions\n\n**Take with food:**\n- Metformin: 500mg twice daily\n- Lisinopril: 10mg once daily\n\n*Always follow your doctor's instructions*",
    "formatting": {
        "markdown": true
    }
}
```

### 3. **Quick Reply Messages**

Messages with predefined response options:

```json
{
    "message_type": "quick_reply",
    "content": "How would you rate your pain level?",
    "quick_replies": [
        {"text": "Mild (1-3)", "value": "pain_mild"},
        {"text": "Moderate (4-6)", "value": "pain_moderate"},
        {"text": "Severe (7-10)", "value": "pain_severe"}
    ]
}
```

### 4. **Card Messages**

Structured information cards:

```json
{
    "message_type": "card",
    "content": "Medication Information",
    "cards": [
        {
            "title": "Ibuprofen",
            "subtitle": "Pain Relief",
            "image_url": "https://example.com/ibuprofen.jpg",
            "description": "Take 400mg every 6-8 hours as needed",
            "actions": [
                {"type": "url", "title": "More Info", "url": "https://example.com/ibuprofen"}
            ]
        }
    ]
}
```

### 5. **Voice Messages**

Audio message handling:

```json
{
    "message_type": "voice",
    "audio_url": "https://storage.example.com/audio/msg_123.wav",
    "transcript": "I have been feeling dizzy for the past hour",
    "duration": 4.5,
    "language": "en"
}
```

### 6. **File Messages**

File and image sharing:

```json
{
    "message_type": "file",
    "file_url": "https://storage.example.com/files/test_results.pdf",
    "file_name": "lab_results_2024.pdf",
    "file_type": "application/pdf",
    "file_size": 245760,
    "description": "Latest blood test results"
}
```

---

## AI Response Features

### 1. **Context Awareness**

The AI maintains conversation context and can reference previous messages:

```json
{
    "content": "Based on the headache symptoms you mentioned earlier, and now that you've indicated the pain is 8/10, I recommend seeking immediate medical attention.",
    "context_references": [
        {
            "message_id": "msg_123456791",
            "reference": "headache symptoms you mentioned earlier"
        }
    ]
}
```

### 2. **Source Attribution**

AI responses include sources when providing medical information:

```json
{
    "content": "According to medical guidelines, chest pain lasting more than 15 minutes should be evaluated immediately.",
    "sources": [
        {
            "type": "medical_guideline",
            "title": "AHA Chest Pain Guidelines",
            "url": "https://guidelines.example.com/chest-pain",
            "confidence": 0.92
        }
    ]
}
```

### 3. **Confidence Indicators**

All AI responses include confidence scoring:

```json
{
    "content": "This sounds like it could be a tension headache.",
    "confidence": 0.78,
    "confidence_factors": {
        "symptom_match": 0.85,
        "context_relevance": 0.75,
        "knowledge_base_coverage": 0.90
    }
}
```

### 4. **Safety Checks**

Automatic safety validation for medical advice:

```json
{
    "content": "I understand you're experiencing severe chest pain. This requires immediate medical attention.",
    "safety_flags": [
        {
            "type": "emergency_symptom",
            "severity": "high",
            "action": "recommend_emergency_care"
        }
    ],
    "escalation_triggered": true
}
```

---

## Error Handling

### Error Response Format

```json
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many messages sent in a short period",
        "details": {
            "limit": 10,
            "window": 60,
            "retry_after": 30
        },
        "request_id": "req_789123456"
    }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_MESSAGE_FORMAT` | 400 | Message format is invalid |
| `CONVERSATION_NOT_FOUND` | 404 | Conversation ID does not exist |
| `CONVERSATION_ENDED` | 409 | Cannot send message to ended conversation |
| `MESSAGE_TOO_LONG` | 413 | Message exceeds maximum length |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `AI_SERVICE_UNAVAILABLE` | 503 | AI service is temporarily unavailable |

---

## Rate Limiting

### Request Limits

| Action | Limit | Window |
|--------|-------|--------|
| Send Message | 30 requests | 1 minute |
| Start Conversation | 5 requests | 1 hour |
| File Upload | 3 requests | 1 minute |
| WebSocket Connection | 1 connection | per user |

### Rate Limit Headers

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1642248300
```

---

## Security Considerations

### 1. **Data Encryption**

- All WebSocket connections use WSS (WebSocket Secure)
- Message content encrypted in transit with TLS 1.3
- Stored messages encrypted at rest with AES-256

### 2. **Input Validation**

- All user input sanitized and validated
- File uploads scanned for malware
- Maximum message length enforced (10,000 characters)

### 3. **Authentication Checks**

- JWT token validated on every request
- WebSocket connections require authentication
- Session timeout after 30 minutes of inactivity

### 4. **PHI Protection**

- Automatic PHI detection and masking in logs
- No PHI stored in browser localStorage
- Conversation data encrypted with user-specific keys

---

## Testing

### Development Environment

```javascript
// Connect to development WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/chat?token=dev_token');

// Test message sending
ws.send(JSON.stringify({
    type: 'message',
    content: 'Test message for development',
    message_type: 'text'
}));
```

### Sample Test Conversations

#### Basic Health Question
```bash
curl -X POST http://localhost:8000/api/chat/conversations \
  -H "Authorization: Bearer dev_token" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "language": "en",
    "initial_message": "What should I do for a mild headache?"
  }'
```

#### Emergency Scenario Testing
```bash
curl -X POST http://localhost:8000/api/chat/conversations \
  -H "Authorization: Bearer dev_token" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "language": "en",
    "initial_message": "I am having severe chest pain"
  }'
```

---

## SDK Examples

### JavaScript/TypeScript SDK

```typescript
import { MedinovAIChat } from '@medinovai/chat-sdk';

const chat = new MedinovAIChat({
    baseURL: 'https://api.myonsitehealthcare.com',
    authToken: 'your-jwt-token',
    reconnect: true
});

// Start conversation
const conversation = await chat.startConversation({
    channel: 'web',
    language: 'en',
    initialMessage: 'Hello, I have a health question'
});

// Listen for messages
chat.onMessage((message) => {
    console.log('Received:', message.content);
});

// Send message
await chat.sendMessage(conversation.id, {
    content: 'I have been having headaches',
    type: 'text'
});
```

### Python SDK

```python
from medinovai_chat import ChatClient

client = ChatClient(
    base_url='https://api.myonsitehealthcare.com',
    auth_token='your-jwt-token'
)

# Start conversation
conversation = client.start_conversation(
    channel='web',
    language='en',
    initial_message='Hello, I need medical advice'
)

# Send message
response = client.send_message(
    conversation_id=conversation.id,
    content='I have been feeling dizzy',
    message_type='text'
)

print(f"AI Response: {response.ai_response.content}")
```

---

## Monitoring and Analytics

### Conversation Metrics

Monitor chat performance with these key metrics:

- **Response Time**: Average AI response time
- **Resolution Rate**: Percentage of conversations resolved by AI
- **Escalation Rate**: Percentage requiring human intervention
- **User Satisfaction**: Conversation rating scores
- **Message Volume**: Total messages per hour/day

### Health Monitoring

```http
GET /api/chat/health
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "status": "healthy",
    "services": {
        "websocket": "healthy",
        "ai_service": "healthy",
        "database": "healthy",
        "message_queue": "healthy"
    },
    "metrics": {
        "active_conversations": 47,
        "average_response_time": 1.8,
        "messages_per_minute": 23
    }
}
```

---

## Support

For Chat API specific issues:
- **Documentation**: [Chat API Troubleshooting](../troubleshooting/chat-api.md)
- **SDK Issues**: [GitHub Repository](https://github.com/myonsite-healthcare/medinovai-sdks)
- **Technical Support**: chat-api-support@myonsitehealthcare.com
- **Emergency Issues**: +1-XXX-XXX-XXXX (24/7 for production issues) 