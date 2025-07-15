# Rate Limiting - MedinovAI API

Comprehensive guide to understanding and implementing rate limiting for the MedinovAI API to ensure fair usage and system stability.

## 🎯 Overview

Rate limiting protects the MedinovAI system from abuse while ensuring fair access for all users. Our rate limiting system uses a combination of **token bucket** and **sliding window** algorithms to provide flexible and robust protection.

### Why Rate Limiting?

- **System Protection**: Prevents system overload and ensures availability
- **Fair Usage**: Ensures equitable access for all users
- **Cost Management**: Controls external API costs (OpenAI, Twilio)
- **Security**: Mitigates abuse and brute force attacks
- **Compliance**: Helps maintain HIPAA performance requirements

---

## 📊 Rate Limit Tiers

### User-Based Limits

| User Type | Requests/Minute | Burst Allowance | Daily Limit | Priority |
|-----------|----------------|-----------------|-------------|----------|
| **Patient** | 30 | 60 | 1,000 | Standard |
| **Healthcare Staff** | 100 | 200 | 5,000 | High |
| **Admin** | 200 | 400 | 10,000 | Highest |
| **API Integration** | 500 | 1,000 | 50,000 | Enterprise |
| **System Service** | 1,000 | 2,000 | Unlimited | Critical |

### Endpoint-Specific Limits

| Endpoint Category | Limit/Minute | Limit/Hour | Limit/Day | Special Rules |
|------------------|--------------|------------|-----------|---------------|
| **Authentication** | 5 | 20 | 100 | Phone number specific |
| **Chat Messages** | 30 | 500 | 2,000 | Conversation context |
| **File Upload** | 3 | 20 | 50 | Size-based throttling |
| **Admin Operations** | 60 | 1,000 | 5,000 | Role verification |
| **Analytics** | 100 | 2,000 | 10,000 | Read-only operations |
| **Health Checks** | 60 | Unlimited | Unlimited | Monitoring exempt |

### Special Considerations

**Healthcare Priority Routing:**
- Emergency-flagged requests bypass rate limits
- Critical patient data operations get priority
- Healthcare staff limits increase during high-demand periods

**Dynamic Scaling:**
- Limits automatically adjust based on system load
- Premium customers get higher limits during off-peak hours
- Geographic load balancing affects regional limits

---

## 🔍 Rate Limit Headers

### Standard Headers

Every API response includes rate limiting information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1642248300
X-RateLimit-Window: 60
X-RateLimit-Retry-After: 35
X-RateLimit-Burst-Limit: 60
X-RateLimit-Burst-Remaining: 55
```

**Header Definitions:**

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Requests allowed per window | `30` |
| `X-RateLimit-Remaining` | Requests remaining in current window | `25` |
| `X-RateLimit-Reset` | Unix timestamp when window resets | `1642248300` |
| `X-RateLimit-Window` | Window duration in seconds | `60` |
| `X-RateLimit-Retry-After` | Seconds until next request allowed | `35` |
| `X-RateLimit-Burst-Limit` | Maximum burst requests allowed | `60` |
| `X-RateLimit-Burst-Remaining` | Burst requests remaining | `55` |

### Enhanced Headers

For authenticated requests, additional context is provided:

```http
X-RateLimit-User-Type: healthcare_staff
X-RateLimit-Tier: premium
X-RateLimit-Global-Limit: 500
X-RateLimit-Global-Remaining: 487
X-RateLimit-Endpoint-Limit: 100
X-RateLimit-Endpoint-Remaining: 95
```

### Rate Limit Error Response

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642248360
X-RateLimit-Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "details": {
      "limit": 30,
      "window": "1 minute",
      "retry_after": 60,
      "burst_available": false,
      "suggested_action": "implement_exponential_backoff"
    },
    "documentation": "https://docs.medinovai.com/api/rate-limits"
  }
}
```

---

## 🛠️ Implementation Guide

### Client-Side Rate Limiting

**JavaScript/TypeScript Implementation**
```javascript
class RateLimitHandler {
  constructor() {
    this.limits = new Map();
    this.retryQueue = [];
  }

  async makeRequest(url, options = {}) {
    const endpoint = this.getEndpointKey(url);
    
    // Check client-side rate limit
    if (!this.canMakeRequest(endpoint)) {
      const waitTime = this.getWaitTime(endpoint);
      await this.delay(waitTime);
    }

    try {
      const response = await fetch(url, options);
      this.updateLimits(endpoint, response.headers);
      
      if (response.status === 429) {
        return this.handleRateLimit(response, url, options);
      }
      
      return response;
    } catch (error) {
      throw new Error(`Request failed: ${error.message}`);
    }
  }

  updateLimits(endpoint, headers) {
    const limit = parseInt(headers.get('X-RateLimit-Limit'));
    const remaining = parseInt(headers.get('X-RateLimit-Remaining'));
    const reset = parseInt(headers.get('X-RateLimit-Reset'));
    
    this.limits.set(endpoint, {
      limit,
      remaining,
      reset,
      lastUpdate: Date.now()
    });
  }

  canMakeRequest(endpoint) {
    const limits = this.limits.get(endpoint);
    if (!limits) return true;
    
    const now = Date.now() / 1000;
    if (now > limits.reset) return true;
    
    return limits.remaining > 0;
  }

  async handleRateLimit(response, url, options) {
    const retryAfter = parseInt(response.headers.get('X-RateLimit-Retry-After')) || 60;
    
    // Exponential backoff with jitter
    const backoffTime = retryAfter * 1000 + Math.random() * 1000;
    
    console.warn(`Rate limited. Retrying after ${backoffTime}ms`);
    await this.delay(backoffTime);
    
    return this.makeRequest(url, options);
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  getEndpointKey(url) {
    // Extract endpoint pattern from URL
    const path = new URL(url).pathname;
    return path.replace(/\/\d+/g, '/:id'); // Normalize IDs
  }
}

// Usage example
const rateLimitHandler = new RateLimitHandler();

async function sendMessage(conversationId, content) {
  try {
    const response = await rateLimitHandler.makeRequest(
      `/api/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content, sender_type: 'user' })
      }
    );
    
    return await response.json();
  } catch (error) {
    console.error('Failed to send message:', error);
    throw error;
  }
}
```

**Python Implementation**
```python
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx

class RateLimitHandler:
    def __init__(self):
        self.limits: Dict[str, Dict] = {}
        self.retry_queue = []
    
    async def make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        endpoint = self._get_endpoint_key(url)
        
        # Check client-side rate limit
        if not self._can_make_request(endpoint):
            wait_time = self._get_wait_time(endpoint)
            await asyncio.sleep(wait_time)
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            self._update_limits(endpoint, response.headers)
            
            if response.status_code == 429:
                return await self._handle_rate_limit(response, method, url, **kwargs)
            
            return response
    
    def _update_limits(self, endpoint: str, headers: httpx.Headers):
        try:
            limit = int(headers.get('x-ratelimit-limit', 0))
            remaining = int(headers.get('x-ratelimit-remaining', 0))
            reset = int(headers.get('x-ratelimit-reset', 0))
            
            self.limits[endpoint] = {
                'limit': limit,
                'remaining': remaining,
                'reset': reset,
                'last_update': time.time()
            }
        except (ValueError, TypeError):
            pass
    
    def _can_make_request(self, endpoint: str) -> bool:
        limits = self.limits.get(endpoint)
        if not limits:
            return True
        
        now = time.time()
        if now > limits['reset']:
            return True
        
        return limits['remaining'] > 0
    
    def _get_wait_time(self, endpoint: str) -> float:
        limits = self.limits.get(endpoint)
        if not limits:
            return 0
        
        return max(0, limits['reset'] - time.time())
    
    async def _handle_rate_limit(self, response: httpx.Response, method: str, url: str, **kwargs) -> httpx.Response:
        retry_after = int(response.headers.get('x-ratelimit-retry-after', 60))
        
        # Exponential backoff with jitter
        backoff_time = retry_after + (time.time() % 1)  # Add jitter
        
        print(f"Rate limited. Retrying after {backoff_time}s")
        await asyncio.sleep(backoff_time)
        
        return await self.make_request(method, url, **kwargs)
    
    def _get_endpoint_key(self, url: str) -> str:
        # Extract endpoint pattern from URL
        from urllib.parse import urlparse
        path = urlparse(url).path
        
        # Normalize numeric IDs
        import re
        return re.sub(r'/\d+', '/:id', path)

# Usage example
rate_limiter = RateLimitHandler()

async def send_message(conversation_id: str, content: str, token: str):
    response = await rate_limiter.make_request(
        'POST',
        f'https://api.medinovai.com/api/conversations/{conversation_id}/messages',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        },
        json={
            'content': content,
            'sender_type': 'user'
        }
    )
    
    return response.json()
```

### Server-Side Rate Limiting

**Custom Rate Limiter Middleware**
```python
# middleware/rate_limiter.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import redis
import time
import json
from typing import Optional

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_limits = {
            'patient': {'requests': 30, 'window': 60, 'burst': 60},
            'healthcare_staff': {'requests': 100, 'window': 60, 'burst': 200},
            'admin': {'requests': 200, 'window': 60, 'burst': 400},
            'api_integration': {'requests': 500, 'window': 60, 'burst': 1000},
        }
    
    async def check_rate_limit(self, request: Request) -> Optional[JSONResponse]:
        # Get user identifier
        user_id = self._get_user_id(request)
        user_type = self._get_user_type(request)
        endpoint = self._get_endpoint_pattern(request.url.path)
        
        # Get applicable limits
        limits = self._get_limits(user_type, endpoint)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_limit(
            user_id, endpoint, limits
        )
        
        if not is_allowed:
            return self._create_rate_limit_response(limits, remaining, reset_time)
        
        return None
    
    async def _check_limit(self, user_id: str, endpoint: str, limits: dict) -> tuple:
        current_time = int(time.time())
        window_start = current_time - limits['window']
        
        # Sliding window key
        key = f"rate_limit:{user_id}:{endpoint}"
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, limits['window'])
        
        results = pipe.execute()
        current_count = results[1]
        
        # Check if within limits
        is_allowed = current_count < limits['requests']
        remaining = max(0, limits['requests'] - current_count)
        reset_time = current_time + limits['window']
        
        return is_allowed, remaining, reset_time
    
    def _get_limits(self, user_type: str, endpoint: str) -> dict:
        # Base limits by user type
        base_limits = self.default_limits.get(user_type, self.default_limits['patient'])
        
        # Endpoint-specific overrides
        endpoint_overrides = {
            '/api/auth/sms/request': {'requests': 5, 'window': 300},  # 5 per 5 minutes
            '/api/conversations/:id/upload': {'requests': 3, 'window': 60},
            '/api/admin/users': {'requests': 100, 'window': 60},
        }
        
        if endpoint in endpoint_overrides:
            return {**base_limits, **endpoint_overrides[endpoint]}
        
        return base_limits
    
    def _create_rate_limit_response(self, limits: dict, remaining: int, reset_time: int) -> JSONResponse:
        retry_after = reset_time - int(time.time())
        
        response = JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded. Try again later.",
                    "details": {
                        "limit": limits['requests'],
                        "window": f"{limits['window']} seconds",
                        "retry_after": retry_after,
                        "burst_available": False
                    }
                }
            }
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limits['requests'])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["X-RateLimit-Retry-After"] = str(retry_after)
        
        return response

# FastAPI dependency
async def rate_limit_dependency(request: Request):
    rate_limiter = get_rate_limiter()  # Get from dependency injection
    result = await rate_limiter.check_rate_limit(request)
    if result:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

---

## 📈 Monitoring and Analytics

### Rate Limit Metrics

**Key Metrics to Monitor:**

1. **Request Patterns**
   - Requests per minute/hour/day by endpoint
   - Peak usage times and patterns
   - Geographic distribution of requests

2. **Rate Limit Events**
   - Number of rate limit hits by user/endpoint
   - Rate limit bypass attempts
   - Escalation of limits during high demand

3. **Performance Impact**
   - Response time correlation with request volume
   - System resource usage during peak loads
   - Cache hit rates for rate limit checks

4. **User Experience**
   - Rate limit error rates by user type
   - Retry success rates
   - Time to retry distribution

### Monitoring Dashboard

**Grafana Queries**
```promql
# Rate limit hits per minute
sum(rate(rate_limit_hits_total[1m])) by (endpoint, user_type)

# Rate limit error percentage
sum(rate(http_requests_total{status="429"}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Top users hitting rate limits
topk(10, sum(rate(rate_limit_hits_total[1h])) by (user_id))

# Average retry delay
histogram_quantile(0.95, sum(rate(rate_limit_retry_delay_seconds_bucket[5m])) by (le))
```

**CloudWatch Metrics**
```json
{
  "metrics": [
    {
      "metricName": "RateLimitHits",
      "dimensions": {
        "Endpoint": "/api/conversations",
        "UserType": "patient"
      },
      "unit": "Count"
    },
    {
      "metricName": "RateLimitBypass",
      "dimensions": {
        "Reason": "emergency_priority"
      },
      "unit": "Count"
    }
  ]
}
```

### Alerting Rules

**Critical Alerts**
```yaml
# High rate limit error rate
- alert: HighRateLimitErrorRate
  expr: rate(http_requests_total{status="429"}[5m]) / rate(http_requests_total[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: High rate limit error rate detected
    description: "Rate limit error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

# Rate limit system failure
- alert: RateLimitSystemDown
  expr: up{job="rate-limiter"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: Rate limiting system is down
    description: Rate limiting system has been down for more than 1 minute

# Unusual rate limit bypass
- alert: UnusualRateLimitBypass
  expr: increase(rate_limit_bypass_total[1h]) > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: Unusual number of rate limit bypasses
    description: "{{ $value }} rate limit bypasses in the last hour"
```

---

## 🔧 Advanced Configuration

### Dynamic Rate Limiting

**Load-Based Adjustment**
```python
class DynamicRateLimiter:
    def __init__(self):
        self.base_limits = {}
        self.load_multipliers = {
            'low': 1.5,      # Increase limits during low load
            'normal': 1.0,   # Standard limits
            'high': 0.8,     # Reduce limits during high load
            'critical': 0.5  # Severe reduction during critical load
        }
    
    def get_adjusted_limits(self, user_type: str, endpoint: str) -> dict:
        base_limits = self.base_limits[user_type]
        current_load = self.get_system_load()
        multiplier = self.load_multipliers[current_load]
        
        return {
            'requests': int(base_limits['requests'] * multiplier),
            'window': base_limits['window'],
            'burst': int(base_limits['burst'] * multiplier)
        }
    
    def get_system_load(self) -> str:
        # Check system metrics
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()
        active_connections = self.get_active_connections()
        
        if cpu_usage > 80 or memory_usage > 85:
            return 'critical'
        elif cpu_usage > 60 or memory_usage > 70:
            return 'high'
        elif cpu_usage < 30 and memory_usage < 50:
            return 'low'
        else:
            return 'normal'
```

**Time-Based Adjustment**
```python
import pytz
from datetime import datetime

class TimeBasedRateLimiter:
    def __init__(self):
        self.business_hours = {
            'start': 8,  # 8 AM
            'end': 18,   # 6 PM
        }
        self.timezone = pytz.timezone('US/Eastern')
    
    def get_time_adjusted_limits(self, base_limits: dict) -> dict:
        now = datetime.now(self.timezone)
        current_hour = now.hour
        is_business_hours = self.business_hours['start'] <= current_hour < self.business_hours['end']
        is_weekend = now.weekday() >= 5
        
        if is_business_hours and not is_weekend:
            # Higher limits during business hours
            multiplier = 1.5
        elif is_weekend:
            # Lower limits on weekends
            multiplier = 0.7
        else:
            # Standard limits off-hours
            multiplier = 1.0
        
        return {
            'requests': int(base_limits['requests'] * multiplier),
            'window': base_limits['window'],
            'burst': int(base_limits['burst'] * multiplier)
        }
```

### Emergency Override System

**Priority Request Handling**
```python
class EmergencyOverride:
    def __init__(self):
        self.emergency_keywords = [
            'emergency', 'urgent', 'critical', 'chest pain',
            'difficulty breathing', 'unconscious', 'bleeding',
            'heart attack', 'stroke', 'suicide'
        ]
    
    def should_bypass_rate_limit(self, request_data: dict, user_context: dict) -> bool:
        # Emergency content detection
        if self.contains_emergency_keywords(request_data.get('content', '')):
            self.log_emergency_bypass(user_context['user_id'], 'emergency_content')
            return True
        
        # Healthcare provider during high-priority operations
        if user_context.get('user_type') == 'healthcare_staff':
            if user_context.get('current_operation') == 'emergency_response':
                self.log_emergency_bypass(user_context['user_id'], 'healthcare_emergency')
                return True
        
        # System-level emergency
        if self.is_system_emergency():
            return True
        
        return False
    
    def contains_emergency_keywords(self, content: str) -> bool:
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.emergency_keywords)
    
    def log_emergency_bypass(self, user_id: str, reason: str):
        logger.warning(f"Rate limit bypassed for user {user_id}, reason: {reason}")
        # Send to monitoring system
        metrics.increment('rate_limit.emergency_bypass', tags={'reason': reason})
```

---

## 🧪 Testing Rate Limits

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from src.middleware.rate_limiter import RateLimiter

class TestRateLimiter:
    
    @pytest.fixture
    def rate_limiter(self):
        mock_redis = Mock()
        return RateLimiter(mock_redis)
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_request_within_limit(self, rate_limiter):
        # Mock Redis responses
        rate_limiter.redis.pipeline.return_value.execute.return_value = [None, 5, None, None]
        
        is_allowed, remaining, reset_time = await rate_limiter._check_limit(
            "user123", "/api/messages", {"requests": 30, "window": 60}
        )
        
        assert is_allowed is True
        assert remaining == 25
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_request_over_limit(self, rate_limiter):
        # Mock Redis responses - user over limit
        rate_limiter.redis.pipeline.return_value.execute.return_value = [None, 30, None, None]
        
        is_allowed, remaining, reset_time = await rate_limiter._check_limit(
            "user123", "/api/messages", {"requests": 30, "window": 60}
        )
        
        assert is_allowed is False
        assert remaining == 0
    
    def test_emergency_bypass(self, rate_limiter):
        emergency_override = EmergencyOverride()
        
        request_data = {"content": "I'm having chest pain and can't breathe"}
        user_context = {"user_id": "patient123", "user_type": "patient"}
        
        should_bypass = emergency_override.should_bypass_rate_limit(request_data, user_context)
        
        assert should_bypass is True
```

### Load Testing Rate Limits

```javascript
// k6 rate limit test
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 50 }, // Ramp up beyond rate limit
  ],
};

export default function () {
  let response = http.post('http://localhost:8000/api/auth/sms/request', 
    JSON.stringify({
      phone_number: '+1234567890'
    }), 
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );
  
  // Check that rate limiting works
  if (response.status === 429) {
    check(response, {
      'rate limit header present': (r) => r.headers['X-RateLimit-Limit'] !== undefined,
      'retry after header present': (r) => r.headers['X-RateLimit-Retry-After'] !== undefined,
    });
    
    let retryAfter = parseInt(response.headers['X-RateLimit-Retry-After']);
    sleep(retryAfter);
  } else {
    check(response, {
      'status is 200': (r) => r.status === 200,
    });
  }
  
  sleep(1);
}
```

---

## 🔄 Best Practices

### Development Guidelines

1. **Always Include Rate Limit Headers**
   ```python
   # Always add headers to responses
   response.headers["X-RateLimit-Limit"] = str(limit)
   response.headers["X-RateLimit-Remaining"] = str(remaining)
   response.headers["X-RateLimit-Reset"] = str(reset_time)
   ```

2. **Implement Graceful Degradation**
   ```python
   # Graceful handling when rate limiter is unavailable
   try:
       is_allowed = await rate_limiter.check_limit(user_id, endpoint)
   except RedisConnectionError:
       logger.warning("Rate limiter unavailable, allowing request")
       is_allowed = True  # Fail open for availability
   ```

3. **Use Consistent Key Patterns**
   ```python
   # Consistent Redis key naming
   def get_rate_limit_key(user_id: str, endpoint: str) -> str:
       return f"rl:{user_id}:{endpoint.replace('/', ':')}"
   ```

4. **Monitor and Alert**
   ```python
   # Always instrument rate limiting
   if not is_allowed:
       metrics.increment('rate_limit.blocked', tags={
           'endpoint': endpoint,
           'user_type': user_type
       })
   ```

### Production Considerations

1. **Redis High Availability**
   - Use Redis Cluster or Sentinel for redundancy
   - Implement circuit breaker pattern for Redis failures
   - Consider local fallback cache for critical operations

2. **Performance Optimization**
   - Use Redis pipelines for atomic operations
   - Cache rate limit configurations
   - Implement sliding window vs fixed window trade-offs

3. **Security Considerations**
   - Rate limit by IP address for unauthenticated requests
   - Implement progressive delays for repeated violations
   - Monitor for distributed attacks across multiple IPs

4. **Compliance Requirements**
   - Log all rate limit decisions for audit trails
   - Ensure emergency medical requests are never blocked
   - Maintain performance SLAs for healthcare operations

---

## 📞 Support and Troubleshooting

### Common Issues

**Rate Limits Too Restrictive**
```bash
# Check current rate limit configuration
redis-cli GET rate_limit:config:patient

# Temporarily increase limits
redis-cli SET rate_limit:override:user123 '{"requests": 100, "window": 60}'
```

**Rate Limiter Not Working**
```bash
# Check Redis connectivity
redis-cli PING

# Verify rate limit keys
redis-cli KEYS "rate_limit:*"

# Check rate limit middleware logs
kubectl logs -l app=medinovai-backend | grep "rate_limit"
```

**Emergency Bypass Not Working**
```python
# Test emergency bypass
emergency_override = EmergencyOverride()
result = emergency_override.should_bypass_rate_limit(
    {"content": "chest pain"},
    {"user_type": "patient"}
)
print(f"Emergency bypass: {result}")
```

### Contact Information

- **Rate Limit Issues**: ratelimit-support@myonsitehealthcare.com
- **Emergency Bypass**: emergency-tech@myonsitehealthcare.com
- **Performance Issues**: performance@myonsitehealthcare.com

---

*Last updated: January 15, 2024 | Version: 2.1.0 | Next review: February 15, 2024*

*For additional API documentation, see [Authentication Guide](authentication.md) or [Chat API Reference](chat.md).* 