# Common Issues Troubleshooting Guide

This guide covers the most frequently encountered issues with the MedinovAI Chatbot system and provides step-by-step solutions for resolving them quickly.

## Quick Reference

### Emergency Response
- **API Down**: [API Service Issues](#api-service-issues)
- **Database Connection Failed**: [Database Issues](#database-connectivity-issues)
- **Authentication Failures**: [Authentication Issues](#authentication-and-sms-issues)
- **High Error Rates**: [Performance Issues](#performance-and-scaling-issues)

### Priority Levels
- 🔴 **P0 - Critical**: Service completely down, affects all users
- 🟡 **P1 - High**: Significant functionality impacted, affects many users
- 🟢 **P2 - Medium**: Minor features affected, workarounds available
- 🔵 **P3 - Low**: Enhancement or optimization needed

---

## API Service Issues

### 1. **API Service Not Responding** 🔴

#### Symptoms
- HTTP 503/504 errors
- Timeouts on all endpoints
- Health check endpoint failing

#### Diagnosis
```bash
# Check pod status
kubectl get pods -n medinovai -l app=medinovai-backend

# Check service endpoints
kubectl get endpoints -n medinovai

# View recent logs
kubectl logs -l app=medinovai-backend -n medinovai --tail=50

# Check resource usage
kubectl top pods -n medinovai
```

#### Solutions

**Solution 1: Restart Pods**
```bash
# Restart backend deployment
kubectl rollout restart deployment/medinovai-backend -n medinovai

# Wait for rollout to complete
kubectl rollout status deployment/medinovai-backend -n medinovai

# Verify pods are running
kubectl get pods -n medinovai -l app=medinovai-backend
```

**Solution 2: Scale Up Resources**
```bash
# Increase replica count
kubectl scale deployment medinovai-backend --replicas=5 -n medinovai

# Update resource limits if needed
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "resources": {
              "requests": {"memory": "1Gi", "cpu": "500m"},
              "limits": {"memory": "2Gi", "cpu": "1000m"}
            }
          }
        ]
      }
    }
  }
}'
```

**Solution 3: Check Load Balancer**
```bash
# Check ingress status
kubectl describe ingress medinovai-ingress -n medinovai

# Verify ALB target groups
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --query 'TargetGroups[?contains(TargetGroupName, `medinovai`)].TargetGroupArn' \
    --output text)
```

### 2. **Slow API Response Times** 🟡

#### Symptoms
- Response times > 5 seconds
- Timeouts on complex operations
- High CPU/memory usage

#### Diagnosis
```bash
# Check response times in logs
kubectl logs -l app=medinovai-backend -n medinovai | grep "response_time"

# Monitor resource usage
kubectl top pods -n medinovai

# Check database performance
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import time
from src.utils.database import get_db
db = next(get_db())
start = time.time()
db.execute('SELECT 1')
print(f'DB query time: {time.time() - start:.3f}s')
"
```

#### Solutions

**Solution 1: Optimize Database Queries**
```bash
# Check slow queries
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
result = db.execute('''
  SELECT query, calls, total_time, mean_time 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC 
  LIMIT 10
''')
for row in result:
    print(row)
"
```

**Solution 2: Scale Horizontally**
```bash
# Enable horizontal pod autoscaling
kubectl autoscale deployment medinovai-backend \
  --cpu-percent=70 \
  --min=3 \
  --max=10 \
  -n medinovai
```

**Solution 3: Optimize Caching**
```bash
# Check Redis cache hit rate
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import redis
import os
r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_AUTH_TOKEN'),
    ssl=True
)
info = r.info()
hits = info['keyspace_hits']
misses = info['keyspace_misses']
hit_rate = hits / (hits + misses) * 100 if (hits + misses) > 0 else 0
print(f'Cache hit rate: {hit_rate:.2f}%')
"
```

### 3. **OpenAI API Errors** 🟡

#### Symptoms
- "Rate limit exceeded" errors
- "Invalid API key" errors
- AI responses failing

#### Diagnosis
```bash
# Check OpenAI API key
kubectl get secret medinovai-secrets -n medinovai -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d

# Check recent AI service logs
kubectl logs -l app=medinovai-backend -n medinovai | grep -i openai

# Test OpenAI connectivity
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import openai
import os
openai.api_key = os.getenv('OPENAI_API_KEY')
try:
    response = openai.models.list()
    print('OpenAI API connection: OK')
except Exception as e:
    print(f'OpenAI API error: {e}')
"
```

#### Solutions

**Solution 1: Check API Limits**
```bash
# Monitor OpenAI usage
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/usage
```

**Solution 2: Implement Exponential Backoff**
```python
# Update OpenAI configuration in code
import time
import random

def call_openai_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except openai.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
```

**Solution 3: Use Alternative Models**
```bash
# Update environment variable for fallback model
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "OPENAI_FALLBACK_MODEL", "value": "gpt-3.5-turbo"}
            ]
          }
        ]
      }
    }
  }
}'
```

---

## Database Connectivity Issues

### 1. **Database Connection Pool Exhaustion** 🔴

#### Symptoms
- "Too many connections" errors
- Long connection wait times
- Database connection timeouts

#### Diagnosis
```bash
# Check current connections
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
result = db.execute('SELECT count(*) FROM pg_stat_activity')
print(f'Active connections: {result.fetchone()[0]}')
"

# Check connection pool status
kubectl logs -l app=medinovai-backend -n medinovai | grep -i "connection pool"

# Check RDS connection metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=medinovai-prod-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

#### Solutions

**Solution 1: Optimize Connection Pool**
```bash
# Update database configuration
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "DB_POOL_SIZE", "value": "20"},
              {"name": "DB_MAX_OVERFLOW", "value": "30"},
              {"name": "DB_POOL_TIMEOUT", "value": "30"},
              {"name": "DB_POOL_RECYCLE", "value": "3600"}
            ]
          }
        ]
      }
    }
  }
}'
```

**Solution 2: Use Connection Pooler**
```bash
# Deploy PgBouncer
cat > pgbouncer.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
  namespace: medinovai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pgbouncer
  template:
    metadata:
      labels:
        app: pgbouncer
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:latest
        env:
        - name: DATABASES_HOST
          value: "medinovai-prod-db.amazonaws.com"
        - name: DATABASES_PORT
          value: "5432"
        - name: POOL_MODE
          value: "transaction"
        - name: MAX_CLIENT_CONN
          value: "1000"
        - name: DEFAULT_POOL_SIZE
          value: "100"
        ports:
        - containerPort: 5432
EOF

kubectl apply -f pgbouncer.yaml
```

### 2. **Database Performance Issues** 🟡

#### Symptoms
- Slow query execution
- High database CPU usage
- Lock contention

#### Diagnosis
```bash
# Check slow queries
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
result = db.execute('''
  SELECT query, calls, total_time, mean_time, rows
  FROM pg_stat_statements 
  ORDER BY total_time DESC 
  LIMIT 10
''')
for row in result:
    print(f'Query: {row[0][:50]}... Time: {row[3]:.2f}ms Calls: {row[1]}')
"

# Check database locks
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
result = db.execute('''
  SELECT blocked_locks.pid AS blocked_pid,
         blocking_locks.pid AS blocking_pid,
         blocked_activity.query AS blocked_statement
  FROM pg_locks blocked_locks
  JOIN pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
  JOIN pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  WHERE NOT blocked_locks.granted
''')
for row in result:
    print(f'Blocked PID: {row[0]}, Blocking PID: {row[1]}')
"
```

#### Solutions

**Solution 1: Optimize Indexes**
```sql
-- Connect to database and create missing indexes
CREATE INDEX CONCURRENTLY idx_conversations_user_id ON conversations(user_id);
CREATE INDEX CONCURRENTLY idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX CONCURRENTLY idx_messages_created_at ON messages(created_at);
```

**Solution 2: Update Statistics**
```bash
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
db.execute('ANALYZE;')
db.commit()
print('Database statistics updated')
"
```

### 3. **Database Connection Failures** 🔴

#### Symptoms
- "Connection refused" errors
- SSL connection errors
- Authentication failures

#### Diagnosis
```bash
# Test database connectivity
kubectl exec -it deployment/medinovai-backend -n medinovai -- pg_isready \
  -h $(echo $DATABASE_URL | cut -d'@' -f2 | cut -d':' -f1) \
  -p 5432

# Check SSL configuration
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('Database connection: OK')
    print(f'SSL Mode: {conn.get_dsn_parameters().get(\"sslmode\", \"not set\")}')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"

# Check RDS instance status
aws rds describe-db-instances \
  --db-instance-identifier medinovai-prod-db \
  --query 'DBInstances[0].DBInstanceStatus'
```

#### Solutions

**Solution 1: Restart Database Connection**
```bash
# Restart backend pods to reset connections
kubectl rollout restart deployment/medinovai-backend -n medinovai

# Wait for restart
kubectl rollout status deployment/medinovai-backend -n medinovai
```

**Solution 2: Check Network Connectivity**
```bash
# Test network connectivity from pod
kubectl exec -it deployment/medinovai-backend -n medinovai -- nslookup medinovai-prod-db.amazonaws.com

# Check security groups
aws ec2 describe-security-groups \
  --group-ids $(aws rds describe-db-instances \
    --db-instance-identifier medinovai-prod-db \
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
    --output text)
```

---

## Authentication and SMS Issues

### 1. **SMS Delivery Failures** 🟡

#### Symptoms
- Users not receiving SMS codes
- Twilio webhook errors
- SMS delivery delays

#### Diagnosis
```bash
# Check Twilio service status
curl -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN \
  "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json"

# Check recent SMS logs
kubectl logs -l app=medinovai-backend -n medinovai | grep -i sms

# Check webhook configuration
curl -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN \
  "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Messages.json?Limit=10"
```

#### Solutions

**Solution 1: Verify Twilio Configuration**
```bash
# Test Twilio credentials
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from twilio.rest import Client
import os
client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
try:
    account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
    print(f'Twilio account status: {account.status}')
except Exception as e:
    print(f'Twilio error: {e}')
"
```

**Solution 2: Check Rate Limits**
```bash
# Check SMS rate limits in logs
kubectl logs -l app=medinovai-backend -n medinovai | grep -i "rate limit"

# Implement exponential backoff for SMS
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "SMS_RETRY_ATTEMPTS", "value": "3"},
              {"name": "SMS_RETRY_DELAY", "value": "5"}
            ]
          }
        ]
      }
    }
  }
}'
```

### 2. **JWT Token Issues** 🟡

#### Symptoms
- "Invalid token" errors
- Token expiration issues
- Authentication bypass attempts

#### Diagnosis
```bash
# Check JWT configuration
kubectl get secret medinovai-secrets -n medinovai -o jsonpath='{.data.JWT_SECRET_KEY}' | base64 -d | wc -c

# Validate JWT token format
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import jwt
import os
try:
    # Test token generation
    token = jwt.encode({'test': 'data'}, os.getenv('JWT_SECRET_KEY'), algorithm='HS256')
    decoded = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
    print('JWT configuration: OK')
except Exception as e:
    print(f'JWT error: {e}')
"
```

#### Solutions

**Solution 1: Regenerate JWT Secret**
```bash
# Generate new JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 64)

# Update secret
kubectl patch secret medinovai-secrets -n medinovai -p "{
  \"data\": {
    \"JWT_SECRET_KEY\": \"$(echo -n $NEW_JWT_SECRET | base64)\"
  }
}"

# Restart pods to use new secret
kubectl rollout restart deployment/medinovai-backend -n medinovai
```

**Solution 2: Adjust Token Expiration**
```bash
# Update token expiration times
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "value": "30"},
              {"name": "JWT_REFRESH_TOKEN_EXPIRE_DAYS", "value": "7"}
            ]
          }
        ]
      }
    }
  }
}'
```

### 3. **OAuth2 Integration Issues** 🟡

#### Symptoms
- OAuth redirect failures
- "Invalid client" errors
- Authorization code issues

#### Diagnosis
```bash
# Check OAuth configuration
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import os
print(f'OAuth Client ID: {os.getenv(\"OAUTH_CLIENT_ID\", \"Not set\")}')
print(f'OAuth Redirect URI: {os.getenv(\"OAUTH_REDIRECT_URI\", \"Not set\")}')
"

# Test OAuth endpoints
curl -I "https://accounts.google.com/o/oauth2/auth?client_id=$OAUTH_CLIENT_ID&redirect_uri=$OAUTH_REDIRECT_URI&response_type=code&scope=openid email profile"
```

#### Solutions

**Solution 1: Verify OAuth Configuration**
```bash
# Update OAuth configuration
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "OAUTH_REDIRECT_URI", "value": "https://admin.yourdomain.com/auth/callback"},
              {"name": "OAUTH_SCOPES", "value": "openid email profile"}
            ]
          }
        ]
      }
    }
  }
}'
```

---

## Performance and Scaling Issues

### 1. **High Memory Usage** 🟡

#### Symptoms
- Pods getting OOMKilled
- Memory usage consistently > 80%
- Slow garbage collection

#### Diagnosis
```bash
# Check memory usage
kubectl top pods -n medinovai

# Check memory limits
kubectl describe pod $(kubectl get pods -n medinovai -l app=medinovai-backend -o jsonpath='{.items[0].metadata.name}') -n medinovai | grep -A 3 -B 3 memory

# Check for memory leaks
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import psutil
import os
process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f'RSS Memory: {memory_info.rss / 1024 / 1024:.2f} MB')
print(f'VMS Memory: {memory_info.vms / 1024 / 1024:.2f} MB')
"
```

#### Solutions

**Solution 1: Increase Memory Limits**
```bash
# Update memory limits
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "resources": {
              "requests": {"memory": "1Gi"},
              "limits": {"memory": "2Gi"}
            }
          }
        ]
      }
    }
  }
}'
```

**Solution 2: Optimize Memory Usage**
```bash
# Configure garbage collection
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "PYTHONOPTIMIZE", "value": "1"},
              {"name": "PYTHONDONTWRITEBYTECODE", "value": "1"}
            ]
          }
        ]
      }
    }
  }
}'
```

### 2. **Auto-scaling Not Working** 🟡

#### Symptoms
- Pods not scaling under load
- HPA showing unknown metrics
- Scaling events not triggered

#### Diagnosis
```bash
# Check HPA status
kubectl get hpa -n medinovai

# Describe HPA for details
kubectl describe hpa medinovai-backend -n medinovai

# Check metrics server
kubectl get pods -n kube-system | grep metrics-server

# Test metrics collection
kubectl top pods -n medinovai
```

#### Solutions

**Solution 1: Fix Metrics Server**
```bash
# Restart metrics server
kubectl rollout restart deployment/metrics-server -n kube-system

# Verify metrics server logs
kubectl logs -l k8s-app=metrics-server -n kube-system
```

**Solution 2: Update HPA Configuration**
```bash
# Create or update HPA
kubectl apply -f - << EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: medinovai-backend
  namespace: medinovai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: medinovai-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF
```

---

## Network and Connectivity Issues

### 1. **Load Balancer Issues** 🔴

#### Symptoms
- 502/503 errors from load balancer
- Health checks failing
- Uneven traffic distribution

#### Diagnosis
```bash
# Check ingress status
kubectl describe ingress medinovai-ingress -n medinovai

# Check service endpoints
kubectl get endpoints -n medinovai

# Check ALB target group health
ALB_ARN=$(kubectl get ingress medinovai-ingress -n medinovai -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
aws elbv2 describe-target-groups --query "TargetGroups[?contains(LoadBalancerArns, '$ALB_ARN')]"
```

#### Solutions

**Solution 1: Fix Health Check Configuration**
```bash
# Update health check path
kubectl patch ingress medinovai-ingress -n medinovai -p '{
  "metadata": {
    "annotations": {
      "alb.ingress.kubernetes.io/healthcheck-path": "/health",
      "alb.ingress.kubernetes.io/healthcheck-interval-seconds": "15",
      "alb.ingress.kubernetes.io/healthcheck-timeout-seconds": "5",
      "alb.ingress.kubernetes.io/healthy-threshold-count": "2",
      "alb.ingress.kubernetes.io/unhealthy-threshold-count": "2"
    }
  }
}'
```

**Solution 2: Check Pod Readiness**
```bash
# Ensure pods are ready
kubectl get pods -n medinovai -o wide

# Check readiness probe logs
kubectl describe pod $(kubectl get pods -n medinovai -l app=medinovai-backend -o jsonpath='{.items[0].metadata.name}') -n medinovai | grep -A 10 "Readiness"
```

### 2. **DNS Resolution Issues** 🟡

#### Symptoms
- Service discovery failures
- External API timeouts
- Intermittent connection issues

#### Diagnosis
```bash
# Test DNS resolution from pod
kubectl exec -it deployment/medinovai-backend -n medinovai -- nslookup kubernetes.default.svc.cluster.local

# Test external DNS
kubectl exec -it deployment/medinovai-backend -n medinovai -- nslookup google.com

# Check CoreDNS
kubectl get pods -n kube-system | grep coredns
kubectl logs -l k8s-app=kube-dns -n kube-system
```

#### Solutions

**Solution 1: Restart CoreDNS**
```bash
# Restart CoreDNS pods
kubectl rollout restart deployment/coredns -n kube-system

# Wait for restart
kubectl rollout status deployment/coredns -n kube-system
```

**Solution 2: Update DNS Configuration**
```bash
# Check DNS configuration
kubectl get configmap coredns -n kube-system -o yaml

# Update if needed (example)
kubectl patch configmap coredns -n kube-system -p '{
  "data": {
    "Corefile": ".:53 {\n    errors\n    health {\n       lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n       pods insecure\n       fallthrough in-addr.arpa ip6.arpa\n       ttl 30\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf {\n       max_concurrent 1000\n    }\n    cache 30\n    loop\n    reload\n    loadbalance\n}\n"
  }
}'
```

---

## Monitoring and Alerting Issues

### 1. **Metrics Not Collecting** 🟡

#### Symptoms
- Grafana dashboards empty
- Prometheus targets down
- Missing metrics data

#### Diagnosis
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring &
curl http://localhost:9090/api/v1/targets

# Check service monitors
kubectl get servicemonitor -n monitoring

# Check pod metrics endpoint
kubectl exec -it deployment/medinovai-backend -n medinovai -- curl http://localhost:9090/metrics
```

#### Solutions

**Solution 1: Create Service Monitor**
```bash
# Create service monitor for application
kubectl apply -f - << EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: medinovai-backend
  namespace: monitoring
  labels:
    app: medinovai-backend
spec:
  selector:
    matchLabels:
      app: medinovai-backend
  namespaceSelector:
    matchNames:
    - medinovai
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF
```

**Solution 2: Fix Metrics Endpoint**
```bash
# Ensure metrics port is exposed in service
kubectl patch service medinovai-backend-service -n medinovai -p '{
  "spec": {
    "ports": [
      {"name": "http", "port": 80, "targetPort": 8000},
      {"name": "metrics", "port": 9090, "targetPort": 9090}
    ]
  }
}'
```

### 2. **Alerts Not Firing** 🟡

#### Symptoms
- No alert notifications
- AlertManager showing no alerts
- Missing alert rules

#### Diagnosis
```bash
# Check AlertManager status
kubectl get pods -n monitoring | grep alertmanager

# Check alert rules
kubectl get prometheusrule -n monitoring

# Check AlertManager configuration
kubectl get secret alertmanager-prometheus-kube-prometheus-alertmanager -n monitoring -o yaml
```

#### Solutions

**Solution 1: Create Alert Rules**
```bash
# Create application-specific alert rules
kubectl apply -f - << EOF
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: medinovai-alerts
  namespace: monitoring
spec:
  groups:
  - name: medinovai.rules
    rules:
    - alert: MedinovAIBackendDown
      expr: up{job="medinovai-backend"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "MedinovAI Backend is down"
        description: "MedinovAI Backend has been down for more than 5 minutes"
    
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ \$value }} errors per second"
EOF
```

---

## Security Issues

### 1. **Unauthorized Access Attempts** 🔴

#### Symptoms
- Multiple failed login attempts
- Suspicious API calls
- WAF blocking requests

#### Diagnosis
```bash
# Check authentication logs
kubectl logs -l app=medinovai-backend -n medinovai | grep -i "authentication failed"

# Check WAF logs
aws wafv2 get-sampled-requests \
  --web-acl-arn $(aws wafv2 list-web-acls --scope CLOUDFRONT --query 'WebACLs[?Name==`medinovai-waf`].ARN' --output text) \
  --rule-metric-name medinovai-waf \
  --scope CLOUDFRONT \
  --time-window StartTime=$(date -d '1 hour ago' +%s),EndTime=$(date +%s) \
  --max-items 100

# Check security alerts
kubectl logs -l app=medinovai-backend -n medinovai | grep -i "security"
```

#### Solutions

**Solution 1: Implement Rate Limiting**
```bash
# Update rate limiting configuration
kubectl patch deployment medinovai-backend -n medinovai -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "medinovai-backend",
            "env": [
              {"name": "RATE_LIMIT_REQUESTS_PER_MINUTE", "value": "30"},
              {"name": "RATE_LIMIT_BURST", "value": "50"},
              {"name": "RATE_LIMIT_BLOCK_DURATION", "value": "300"}
            ]
          }
        ]
      }
    }
  }
}'
```

**Solution 2: Update WAF Rules**
```bash
# Block suspicious IPs
aws wafv2 update-web-acl \
  --scope CLOUDFRONT \
  --id $(aws wafv2 list-web-acls --scope CLOUDFRONT --query 'WebACLs[?Name==`medinovai-waf`].Id' --output text) \
  --name medinovai-waf \
  --default-action Allow={} \
  --rules file://updated-waf-rules.json
```

### 2. **SSL Certificate Issues** 🟡

#### Symptoms
- SSL certificate expired warnings
- HTTPS connection failures
- Certificate validation errors

#### Diagnosis
```bash
# Check certificate expiration
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# Check certificate in ACM
aws acm list-certificates --query 'CertificateSummaryList[?DomainName==`*.yourdomain.com`]'

# Verify certificate chain
curl -I https://api.yourdomain.com
```

#### Solutions

**Solution 1: Renew Certificate**
```bash
# For ACM certificates, renewal is automatic, but check status
aws acm describe-certificate \
  --certificate-arn $(aws acm list-certificates --query 'CertificateSummaryList[?DomainName==`*.yourdomain.com`].CertificateArn' --output text)

# For Let's Encrypt certificates
kubectl get certificate -n medinovai
kubectl describe certificate api-yourdomain-com -n medinovai
```

**Solution 2: Update Certificate Configuration**
```bash
# Update ingress with new certificate
kubectl patch ingress medinovai-ingress -n medinovai -p '{
  "metadata": {
    "annotations": {
      "alb.ingress.kubernetes.io/certificate-arn": "arn:aws:acm:us-east-1:ACCOUNT-ID:certificate/NEW-CERTIFICATE-ID"
    }
  }
}'
```

---

## Quick Recovery Procedures

### 1. **Complete System Restore** 🔴

#### When to Use
- Multiple critical systems down
- Data corruption detected
- Security breach requiring rollback

#### Procedure
```bash
# 1. Stop all traffic
kubectl scale deployment medinovai-backend --replicas=0 -n medinovai
kubectl scale deployment medinovai-frontend --replicas=0 -n medinovai

# 2. Restore database from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier medinovai-prod-db-restore \
  --db-snapshot-identifier medinovai-prod-$(date -d '1 day ago' +%Y%m%d)

# 3. Restore Kubernetes resources
velero restore create medinovai-restore --from-backup medinovai-$(date -d '1 day ago' +%Y%m%d)

# 4. Verify restoration
kubectl wait --for=condition=available deployment/medinovai-backend -n medinovai --timeout=600s

# 5. Resume traffic gradually
kubectl scale deployment medinovai-backend --replicas=1 -n medinovai
# Monitor and gradually increase replicas
```

### 2. **Emergency Maintenance Mode** 🔴

#### When to Use
- Critical security updates
- Major system issues
- Database maintenance

#### Procedure
```bash
# 1. Enable maintenance mode
kubectl apply -f - << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: maintenance-page
  namespace: medinovai
data:
  index.html: |
    <!DOCTYPE html>
    <html>
    <head>
        <title>Maintenance - MedinovAI</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .container { max-width: 600px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Scheduled Maintenance</h1>
            <p>MedinovAI is currently undergoing scheduled maintenance.</p>
            <p>We'll be back shortly. Thank you for your patience.</p>
            <p>For urgent medical issues, please contact your healthcare provider directly.</p>
        </div>
    </body>
    </html>
EOF

# 2. Deploy maintenance page
kubectl apply -f - << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maintenance-page
  namespace: medinovai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: maintenance-page
  template:
    metadata:
      labels:
        app: maintenance-page
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: maintenance-content
          mountPath: /usr/share/nginx/html
      volumes:
      - name: maintenance-content
        configMap:
          name: maintenance-page
---
apiVersion: v1
kind: Service
metadata:
  name: maintenance-page-service
  namespace: medinovai
spec:
  selector:
    app: maintenance-page
  ports:
  - port: 80
    targetPort: 80
EOF

# 3. Redirect traffic to maintenance page
kubectl patch ingress medinovai-ingress -n medinovai -p '{
  "spec": {
    "rules": [
      {
        "host": "api.yourdomain.com",
        "http": {
          "paths": [
            {
              "path": "/",
              "pathType": "Prefix",
              "backend": {
                "service": {
                  "name": "maintenance-page-service",
                  "port": {"number": 80}
                }
              }
            }
          ]
        }
      }
    ]
  }
}'

# 4. When maintenance is complete, restore normal service
kubectl patch ingress medinovai-ingress -n medinovai -p '{
  "spec": {
    "rules": [
      {
        "host": "api.yourdomain.com",
        "http": {
          "paths": [
            {
              "path": "/",
              "pathType": "Prefix",
              "backend": {
                "service": {
                  "name": "medinovai-backend-service",
                  "port": {"number": 80}
                }
              }
            }
          ]
        }
      }
    ]
  }
}'

# 5. Clean up maintenance resources
kubectl delete deployment maintenance-page -n medinovai
kubectl delete service maintenance-page-service -n medinovai
kubectl delete configmap maintenance-page -n medinovai
```

---

## Escalation Procedures

### Level 1 Support (First Response)
- Basic troubleshooting steps
- Restart services if necessary
- Check logs for obvious errors
- **Escalate after**: 30 minutes or if issue is P0

### Level 2 Support (Advanced)
- Deep technical investigation
- Database and infrastructure issues
- Security incident response
- **Escalate after**: 2 hours or if requires vendor support

### Level 3 Support (Expert)
- Vendor escalation
- Code changes required
- Infrastructure redesign
- **Escalate after**: When resolution requires development

### Emergency Contacts
- **Level 1**: on-call-l1@yourdomain.com
- **Level 2**: on-call-l2@yourdomain.com  
- **Level 3**: engineering-lead@yourdomain.com
- **Security**: security-incident@yourdomain.com

---

## Preventive Measures

### 1. **Regular Health Checks**

```bash
# Daily automated health check script
#!/bin/bash
echo "=== MedinovAI Health Check $(date) ==="

# Check API health
curl -f https://api.yourdomain.com/health || echo "❌ API Health Check Failed"

# Check database connectivity
kubectl exec deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
try:
    next(get_db()).execute('SELECT 1')
    print('✅ Database connectivity OK')
except Exception as e:
    print(f'❌ Database connectivity failed: {e}')
"

# Check certificate expiration
EXPIRY=$(openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
    echo "⚠️  SSL certificate expires in $DAYS_UNTIL_EXPIRY days"
else
    echo "✅ SSL certificate valid for $DAYS_UNTIL_EXPIRY days"
fi
```

### 2. **Monitoring Best Practices**

- Set up alerts for all P0/P1 scenarios
- Monitor key business metrics (conversation success rate, response time)
- Regular security scans
- Performance baseline monitoring
- Capacity planning based on growth trends

### 3. **Documentation Maintenance**

- Keep runbooks updated with latest procedures
- Document all incident resolutions
- Regular review of common issues
- Update contact information quarterly

---

This troubleshooting guide should be reviewed and updated regularly based on new issues encountered and lessons learned from incidents. For additional support, contact the technical team or refer to the specific component documentation. 