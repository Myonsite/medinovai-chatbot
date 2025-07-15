# Error Codes Reference - MedinovAI Chatbot

Comprehensive reference for all error codes in the MedinovAI system with descriptions, causes, and resolution steps.

## 🔍 Quick Error Lookup

**Search by Error Code:** Use Ctrl+F and search for your specific error code (e.g., "AUTH001")

**Error Severity Levels:**
- 🔴 **Critical** - System down or data loss risk
- 🟡 **Warning** - Degraded functionality 
- 🔵 **Info** - Non-blocking notifications
- 🟢 **Success** - Operation completed successfully

---

## 🔐 Authentication Errors (AUTH)

### AUTH001 - Invalid Authentication Token
**Severity:** 🟡 Warning  
**HTTP Status:** 401 Unauthorized

**Description:** The provided JWT token is invalid, expired, or malformed.

**Common Causes:**
- Token has expired (default: 60 minutes)
- Token signature is invalid
- Token was revoked/blacklisted
- Clock skew between client and server

**Resolution Steps:**
1. **Check Token Expiry:**
   ```bash
   # Decode JWT to check expiration
   echo "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." | base64 -d
   ```

2. **Refresh Token:**
   ```javascript
   // JavaScript example
   const response = await fetch('/api/auth/refresh', {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${refreshToken}`
     }
   });
   ```

3. **Re-authenticate:**
   ```bash
   curl -X POST https://api.yourdomain.com/api/auth/sms/request \
     -H "Content-Type: application/json" \
     -d '{"phone_number": "+1234567890"}'
   ```

**Prevention:**
- Implement automatic token refresh
- Set appropriate token expiration times
- Handle 401 responses gracefully

### AUTH002 - Missing Authentication Header
**Severity:** 🟡 Warning  
**HTTP Status:** 401 Unauthorized

**Description:** Request missing required Authorization header.

**Resolution:**
```bash
# Include Authorization header
curl -H "Authorization: Bearer <your-token>" \
  https://api.yourdomain.com/api/protected-endpoint
```

### AUTH003 - Invalid SMS Code
**Severity:** 🟡 Warning  
**HTTP Status:** 400 Bad Request

**Description:** The SMS verification code provided is incorrect or expired.

**Common Causes:**
- Code has expired (default: 10 minutes)
- Incorrect code entered
- Code already used
- Rate limiting triggered

**Resolution Steps:**
1. **Request New Code:**
   ```javascript
   await fetch('/api/auth/sms/request', {
     method: 'POST',
     body: JSON.stringify({ phone_number: '+1234567890' })
   });
   ```

2. **Check Rate Limits:**
   - Wait 60 seconds between requests
   - Maximum 5 attempts per hour per phone number

3. **Verify Phone Number Format:**
   ```regex
   # Valid format: +1234567890
   ^\+[1-9]\d{1,14}$
   ```

### AUTH004 - Account Locked
**Severity:** 🔴 Critical  
**HTTP Status:** 423 Locked

**Description:** Account temporarily locked due to multiple failed authentication attempts.

**Resolution:**
- **Automatic Unlock:** 30 minutes after last failed attempt
- **Manual Unlock:** Contact system administrator
- **Admin Unlock:**
  ```bash
  kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
  from src.models.user import User
  from src.utils.database import get_db
  db = next(get_db())
  user = db.query(User).filter(User.phone_number == '+1234567890').first()
  user.failed_attempts = 0
  user.locked_until = None
  db.commit()
  print('Account unlocked')
  "
  ```

### AUTH005 - OAuth Provider Error
**Severity:** 🟡 Warning  
**HTTP Status:** 502 Bad Gateway

**Description:** External OAuth provider (Google, Microsoft) is unavailable or returned an error.

**Resolution:**
1. **Check Provider Status:**
   - Google: https://status.google.com/
   - Microsoft: https://status.office365.com/

2. **Fallback to SMS Authentication:**
   ```javascript
   // Automatically fallback
   if (oauthError) {
     redirectToSMSAuth();
   }
   ```

3. **Retry with Exponential Backoff:**
   ```javascript
   const retryDelays = [1000, 2000, 4000, 8000]; // ms
   ```

---

## 💬 Chat API Errors (CHAT)

### CHAT001 - Conversation Not Found
**Severity:** 🟡 Warning  
**HTTP Status:** 404 Not Found

**Description:** The specified conversation ID does not exist or is not accessible.

**Common Causes:**
- Invalid conversation ID
- Conversation deleted
- User lacks permission to access conversation
- Database connectivity issues

**Resolution:**
1. **Verify Conversation ID Format:**
   ```regex
   # Valid format: conv_[a-zA-Z0-9]{10}
   ^conv_[a-zA-Z0-9]{10}$
   ```

2. **Check User Permissions:**
   ```bash
   # Verify user can access conversation
   curl -H "Authorization: Bearer <token>" \
     https://api.yourdomain.com/api/conversations/<conv_id>
   ```

3. **Create New Conversation:**
   ```javascript
   const newConversation = await fetch('/api/conversations', {
     method: 'POST',
     headers: { 'Authorization': `Bearer ${token}` },
     body: JSON.stringify({
       channel: 'web',
       language: 'en'
     })
   });
   ```

### CHAT002 - Message Too Long
**Severity:** 🟡 Warning  
**HTTP Status:** 413 Payload Too Large

**Description:** Message content exceeds maximum allowed length.

**Limits:**
- **Text Messages:** 10,000 characters
- **File Uploads:** 10MB
- **Voice Messages:** 5 minutes

**Resolution:**
```javascript
// Validate message length before sending
if (messageContent.length > 10000) {
  // Split into multiple messages or show error
  const chunks = messageContent.match(/.{1,9000}/g);
  for (const chunk of chunks) {
    await sendMessage(chunk);
  }
}
```

### CHAT003 - Conversation Ended
**Severity:** 🟡 Warning  
**HTTP Status:** 409 Conflict

**Description:** Attempting to send message to an ended conversation.

**Resolution:**
1. **Start New Conversation:**
   ```javascript
   const response = await fetch('/api/conversations', {
     method: 'POST',
     body: JSON.stringify({
       channel: 'web',
       language: 'en',
       initial_message: messageContent
     })
   });
   ```

2. **Resume Conversation (if allowed):**
   ```javascript
   await fetch(`/api/conversations/${conversationId}/resume`, {
     method: 'POST'
   });
   ```

### CHAT004 - AI Service Unavailable
**Severity:** 🔴 Critical  
**HTTP Status:** 503 Service Unavailable

**Description:** OpenAI or other AI services are temporarily unavailable.

**Resolution:**
1. **Check AI Service Status:**
   ```bash
   curl -I https://api.openai.com/v1/models
   ```

2. **Use Fallback Responses:**
   ```javascript
   const fallbackMessage = "I'm experiencing technical difficulties. Please try again in a moment or contact our support team.";
   ```

3. **Queue Messages for Retry:**
   ```javascript
   // Store messages for retry when service recovers
   const queueMessage = {
     conversationId,
     content,
     timestamp: Date.now(),
     retryCount: 0
   };
   ```

### CHAT005 - Escalation Queue Full
**Severity:** 🟡 Warning  
**HTTP Status:** 503 Service Unavailable

**Description:** Human escalation queue is at capacity.

**Resolution:**
1. **Provide Wait Time Estimate:**
   ```javascript
   const response = {
     message: "All agents are currently busy. Estimated wait time: 15 minutes",
     estimatedWaitTime: 900, // seconds
     queuePosition: 5
   };
   ```

2. **Offer Alternatives:**
   ```javascript
   const alternatives = [
     "Schedule a callback",
     "Send an email",
     "Try AI assistance for common questions"
   ];
   ```

---

## 🗄️ Database Errors (DB)

### DB001 - Connection Failed
**Severity:** 🔴 Critical  
**HTTP Status:** 500 Internal Server Error

**Description:** Unable to establish connection to the database.

**Common Causes:**
- Database server is down
- Network connectivity issues
- Connection pool exhausted
- Invalid connection credentials

**Resolution:**
1. **Check Database Status:**
   ```bash
   # Check RDS instance status
   aws rds describe-db-instances --db-instance-identifier medinovai-prod-db
   
   # Test connection from pod
   kubectl exec -it deployment/medinovai-backend -n medinovai -- \
     pg_isready -h $DB_HOST -p $DB_PORT
   ```

2. **Restart Connection Pool:**
   ```bash
   # Restart backend pods to reset connections
   kubectl rollout restart deployment/medinovai-backend -n medinovai
   ```

3. **Scale Database if Needed:**
   ```bash
   # Increase RDS instance size
   aws rds modify-db-instance \
     --db-instance-identifier medinovai-prod-db \
     --db-instance-class db.r5.xlarge \
     --apply-immediately
   ```

### DB002 - Query Timeout
**Severity:** 🟡 Warning  
**HTTP Status:** 504 Gateway Timeout

**Description:** Database query exceeded maximum execution time.

**Resolution:**
1. **Optimize Query:**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_conversations_user_created 
   ON conversations(user_id, created_at);
   
   -- Update statistics
   ANALYZE conversations;
   ```

2. **Increase Timeout:**
   ```python
   # In application configuration
   DATABASE_QUERY_TIMEOUT = 30  # seconds
   ```

### DB003 - Constraint Violation
**Severity:** 🟡 Warning  
**HTTP Status:** 400 Bad Request

**Description:** Database constraint violation (unique, foreign key, check constraint).

**Common Violations:**
- Duplicate phone number registration
- Invalid foreign key reference
- Data validation failure

**Resolution:**
```python
try:
    db.add(new_user)
    db.commit()
except IntegrityError as e:
    if "unique constraint" in str(e):
        return {"error": "Phone number already registered"}
    elif "foreign key constraint" in str(e):
        return {"error": "Invalid reference"}
    else:
        return {"error": "Data validation failed"}
```

---

## 🔌 External Service Errors (EXT)

### EXT001 - Twilio API Error
**Severity:** 🟡 Warning  
**HTTP Status:** 502 Bad Gateway

**Description:** Twilio SMS service returned an error.

**Common Twilio Error Codes:**
- **21211:** Invalid phone number
- **21614:** Number cannot receive SMS
- **30001:** Queue overflow (rate limit)

**Resolution:**
1. **Validate Phone Number:**
   ```python
   from twilio.rest import Client
   
   client = Client(account_sid, auth_token)
   try:
       number_info = client.lookups.phone_numbers(phone_number).fetch()
       if number_info.carrier['type'] == 'mobile':
           # Can receive SMS
           return True
   except Exception:
       return False
   ```

2. **Handle Rate Limits:**
   ```python
   import time
   from random import uniform
   
   def send_sms_with_retry(phone, message, max_retries=3):
       for attempt in range(max_retries):
           try:
               return client.messages.create(to=phone, body=message)
           except TwilioRestException as e:
               if e.code == 30001:  # Rate limit
                   wait_time = (2 ** attempt) + uniform(0, 1)
                   time.sleep(wait_time)
               else:
                   raise
   ```

### EXT002 - OpenAI Rate Limit
**Severity:** 🟡 Warning  
**HTTP Status:** 429 Too Many Requests

**Description:** OpenAI API rate limit exceeded.

**Resolution:**
1. **Implement Exponential Backoff:**
   ```python
   import openai
   import time
   from random import uniform
   
   def call_openai_with_backoff(messages, max_retries=3):
       for attempt in range(max_retries):
           try:
               return openai.ChatCompletion.create(
                   model="gpt-4",
                   messages=messages
               )
           except openai.error.RateLimitError:
               if attempt == max_retries - 1:
                   raise
               wait_time = (2 ** attempt) + uniform(0, 1)
               time.sleep(wait_time)
   ```

2. **Use Token Bucket:**
   ```python
   class TokenBucket:
       def __init__(self, capacity, refill_rate):
           self.capacity = capacity
           self.tokens = capacity
           self.refill_rate = refill_rate
           self.last_refill = time.time()
       
       def consume(self, tokens=1):
           self._refill()
           if self.tokens >= tokens:
               self.tokens -= tokens
               return True
           return False
   ```

### EXT003 - S3 Storage Error
**Severity:** 🟡 Warning  
**HTTP Status:** 502 Bad Gateway

**Description:** Amazon S3 storage operation failed.

**Common S3 Errors:**
- **NoSuchBucket:** Bucket doesn't exist
- **AccessDenied:** Insufficient permissions
- **SlowDown:** Rate limiting

**Resolution:**
```python
import boto3
from botocore.exceptions import ClientError

def upload_file_with_retry(file_data, bucket, key):
    s3_client = boto3.client('s3')
    
    try:
        response = s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_data,
            ServerSideEncryption='AES256'
        )
        return response
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            # Create bucket if it doesn't exist
            s3_client.create_bucket(Bucket=bucket)
            return upload_file_with_retry(file_data, bucket, key)
        elif error_code == 'SlowDown':
            time.sleep(1)
            return upload_file_with_retry(file_data, bucket, key)
        else:
            raise
```

---

## ⚙️ System Errors (SYS)

### SYS001 - Service Unavailable
**Severity:** 🔴 Critical  
**HTTP Status:** 503 Service Unavailable

**Description:** One or more critical services are unavailable.

**Resolution:**
1. **Check Service Health:**
   ```bash
   kubectl get pods -n medinovai
   kubectl describe pod <failing-pod> -n medinovai
   ```

2. **Restart Services:**
   ```bash
   kubectl rollout restart deployment/medinovai-backend -n medinovai
   ```

3. **Scale Up:**
   ```bash
   kubectl scale deployment medinovai-backend --replicas=5 -n medinovai
   ```

### SYS002 - Resource Exhausted
**Severity:** 🟡 Warning  
**HTTP Status:** 507 Insufficient Storage

**Description:** System resources (CPU, memory, disk) are exhausted.

**Resolution:**
1. **Check Resource Usage:**
   ```bash
   kubectl top pods -n medinovai
   kubectl top nodes
   ```

2. **Increase Resource Limits:**
   ```yaml
   resources:
     requests:
       memory: "1Gi"
       cpu: "500m"
     limits:
       memory: "2Gi"
       cpu: "1000m"
   ```

### SYS003 - Configuration Error
**Severity:** 🔴 Critical  
**HTTP Status:** 500 Internal Server Error

**Description:** Invalid system configuration detected.

**Resolution:**
1. **Validate Configuration:**
   ```bash
   # Check environment variables
   kubectl exec deployment/medinovai-backend -n medinovai -- env | grep -E "(DB_|REDIS_|OPENAI_)"
   
   # Validate configuration format
   kubectl exec deployment/medinovai-backend -n medinovai -- python -c "
   from src.utils.config import settings
   print('Configuration valid:', settings.validate())
   "
   ```

2. **Update Configuration:**
   ```bash
   kubectl patch deployment medinovai-backend -n medinovai -p '{
     "spec": {
       "template": {
         "spec": {
           "containers": [{
             "name": "medinovai-backend",
             "env": [{"name": "CORRECTED_CONFIG", "value": "new_value"}]
           }]
         }
       }
     }
   }'
   ```

---

## 🔐 Security Errors (SEC)

### SEC001 - Suspicious Activity Detected
**Severity:** 🔴 Critical  
**HTTP Status:** 403 Forbidden

**Description:** Potential security threat detected and blocked.

**Triggers:**
- Multiple failed login attempts
- Unusual access patterns
- Known malicious IP addresses
- SQL injection attempts

**Resolution:**
1. **Review Security Logs:**
   ```bash
   kubectl logs -l app=medinovai-backend -n medinovai | grep "SECURITY"
   ```

2. **Whitelist Legitimate IPs:**
   ```bash
   # Add to WAF whitelist
   aws wafv2 update-ip-set \
     --scope CLOUDFRONT \
     --id <ip-set-id> \
     --addresses 192.168.1.100/32
   ```

### SEC002 - Rate Limit Exceeded
**Severity:** 🟡 Warning  
**HTTP Status:** 429 Too Many Requests

**Description:** Request rate limit exceeded for API endpoint.

**Rate Limits:**
- **Authentication:** 5 requests/minute
- **Chat Messages:** 30 requests/minute
- **File Upload:** 3 requests/minute

**Response Headers:**
```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642248300
Retry-After: 60
```

**Resolution:**
```javascript
// Implement client-side rate limiting
class RateLimiter {
  constructor(limit, window) {
    this.limit = limit;
    this.window = window;
    this.requests = [];
  }
  
  canMakeRequest() {
    const now = Date.now();
    const windowStart = now - this.window;
    this.requests = this.requests.filter(time => time > windowStart);
    
    if (this.requests.length < this.limit) {
      this.requests.push(now);
      return true;
    }
    return false;
  }
}
```

---

## 📊 Monitoring and Diagnostics

### Error Monitoring Commands

**Real-time Error Monitoring:**
```bash
# Monitor error logs in real-time
kubectl logs -f -l app=medinovai-backend -n medinovai | grep ERROR

# Count errors by type
kubectl logs -l app=medinovai-backend -n medinovai --since=1h | \
  grep -o 'ERROR.*' | sort | uniq -c | sort -nr

# Monitor HTTP error rates
kubectl logs -l app=medinovai-backend -n medinovai --since=1h | \
  grep -o '"status":[0-9]*' | sort | uniq -c
```

**Error Rate Analysis:**
```bash
# Get error rate from Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])' | \
  jq '.data.result[0].value[1]'

# Check error patterns
kubectl logs -l app=medinovai-backend -n medinovai --since=24h | \
  grep -E "(AUTH|CHAT|DB|EXT|SYS|SEC)[0-9]{3}" | \
  cut -d' ' -f1 | sort | uniq -c | sort -nr
```

### Automated Error Response

**Auto-Remediation Scripts:**
```bash
#!/bin/bash
# auto-remediate.sh - Automatic error response

ERROR_CODE=$1
SEVERITY=$2

case $ERROR_CODE in
  "DB001")
    echo "Database connection failed - restarting backend pods"
    kubectl rollout restart deployment/medinovai-backend -n medinovai
    ;;
  "CHAT004") 
    echo "AI service unavailable - enabling fallback mode"
    kubectl patch configmap medinovai-config -n medinovai -p '{"data":{"AI_FALLBACK_ENABLED":"true"}}'
    ;;
  "SYS001")
    echo "Service unavailable - scaling up"
    kubectl scale deployment medinovai-backend --replicas=5 -n medinovai
    ;;
esac
```

### Error Reporting Dashboard

**Grafana Query Examples:**
```promql
# Error rate by service
rate(http_requests_total{status=~"4..|5.."}[5m])

# Top error codes
topk(10, sum by (error_code) (rate(application_errors_total[5m])))

# Error count by severity
sum by (severity) (rate(application_errors_total[5m]))
```

---

## 📞 Support Escalation

### When to Escalate

| Error Severity | Auto-Escalate | Manual Escalate | Contact |
|----------------|---------------|-----------------|---------|
| 🔴 Critical | Immediately | Any occurrence | On-call engineer |
| 🟡 Warning | After 3 occurrences | Persistent issues | L2 support |
| 🔵 Info | Never | If impacting users | L1 support |

### Escalation Contacts

**24/7 Emergency:**
- 📞 Phone: +1-XXX-XXX-XXXX
- 📧 Email: critical@myonsitehealthcare.com
- 💬 Slack: #critical-alerts

**Business Hours:**
- 📧 Email: support@myonsitehealthcare.com
- 💬 Slack: #technical-support
- 🎫 Ticket: https://support.myonsitehealthcare.com

---

**Last Updated:** January 15, 2024  
**Version:** 2.1.0  
**Next Review:** February 15, 2024

*For additional troubleshooting, see [Common Issues Guide](../troubleshooting/common-issues.md) or [Operations Runbook](../troubleshooting/operations-runbook.md).* 