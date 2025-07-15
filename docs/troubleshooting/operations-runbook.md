# Operations Runbook - MedinovAI Chatbot

This runbook provides step-by-step procedures for operating and maintaining the MedinovAI Chatbot system in production. It serves as the primary reference for on-call engineers, system administrators, and support staff.

## Table of Contents

1. [Emergency Procedures](#emergency-procedures)
2. [Daily Operations](#daily-operations)
3. [Incident Response](#incident-response)
4. [Backup and Recovery](#backup-and-recovery)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Escalation Matrix](#escalation-matrix)
7. [Common Scenarios](#common-scenarios)

---

## Emergency Procedures

### 🚨 CRITICAL - System Down (P0)

**Immediate Actions (0-5 minutes)**

1. **Assess Impact**
   ```bash
   # Check overall system status
   curl -I https://api.yourdomain.com/health
   curl -I https://admin.yourdomain.com
   
   # Check pod status
   kubectl get pods -n medinovai
   
   # Check recent deployments
   kubectl rollout history deployment/medinovai-backend -n medinovai
   ```

2. **Immediate Response**
   ```bash
   # If recent deployment caused issue - rollback
   kubectl rollout undo deployment/medinovai-backend -n medinovai
   
   # If pods are failing - restart
   kubectl rollout restart deployment/medinovai-backend -n medinovai
   
   # Scale up if needed
   kubectl scale deployment medinovai-backend --replicas=5 -n medinovai
   ```

3. **Escalation**
   - **Immediately**: Notify #critical-alerts Slack channel
   - **Within 2 minutes**: Page on-call engineer if not resolved
   - **Within 5 minutes**: Notify Engineering Manager
   - **Within 10 minutes**: Engage senior escalation if not resolved

### 🔒 SECURITY BREACH (P0)

**Immediate Actions (0-2 minutes)**

1. **Isolate the System**
   ```bash
   # Block all external traffic immediately
   kubectl patch ingress medinovai-ingress -n medinovai -p '{
     "metadata": {
       "annotations": {
         "alb.ingress.kubernetes.io/actions.block-all": "{\"Type\": \"fixed-response\", \"FixedResponseConfig\": {\"StatusCode\": \"503\", \"ContentType\": \"text/plain\", \"MessageBody\": \"Service temporarily unavailable\"}}"
       }
     }
   }'
   
   # Scale down to minimum
   kubectl scale deployment medinovai-backend --replicas=1 -n medinovai
   ```

2. **Preserve Evidence**
   ```bash
   # Capture current state
   kubectl get events --sort-by='.lastTimestamp' -n medinovai > /tmp/security-incident-events.log
   kubectl logs -l app=medinovai-backend -n medinovai --tail=1000 > /tmp/security-incident-logs.log
   
   # Create database snapshot
   aws rds create-db-snapshot \
     --db-instance-identifier medinovai-prod-db \
     --db-snapshot-identifier security-incident-$(date +%Y%m%d-%H%M%S)
   ```

3. **Immediate Escalation**
   - **Immediately**: Notify CISO and Security Team
   - **Within 5 minutes**: Notify Legal and Compliance
   - **Within 15 minutes**: Prepare for potential breach notification procedures

### 💾 DATA LOSS/CORRUPTION (P0)

**Immediate Actions (0-10 minutes)**

1. **Stop Write Operations**
   ```bash
   # Put system in read-only mode
   kubectl patch deployment medinovai-backend -n medinovai -p '{
     "spec": {
       "template": {
         "spec": {
           "containers": [
             {
               "name": "medinovai-backend",
               "env": [
                 {"name": "READ_ONLY_MODE", "value": "true"}
               ]
             }
           ]
         }
       }
     }
   }'
   ```

2. **Assess Scope**
   ```bash
   # Check database integrity
   kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
   from src.utils.database import get_db
   db = next(get_db())
   
   # Check recent records
   result = db.execute('SELECT COUNT(*) FROM conversations WHERE created_at >= NOW() - INTERVAL \"1 hour\"')
   print(f'Recent conversations: {result.fetchone()[0]}')
   
   # Check for corruption indicators
   result = db.execute('SELECT COUNT(*) FROM messages WHERE content IS NULL OR content = \"\"')
   print(f'Potentially corrupted messages: {result.fetchone()[0]}')
   "
   ```

3. **Begin Recovery**
   - Identify last known good backup
   - Coordinate with Database Administrator
   - Prepare for potential data restoration

---

## Daily Operations

### Morning Checklist (8:00 AM)

#### 1. **System Health Check**
```bash
#!/bin/bash
# Daily health check script

echo "=== MedinovAI Daily Health Check $(date) ==="

# Check API endpoints
echo "Checking API health..."
curl -s https://api.yourdomain.com/health | jq '.status' || echo "❌ API health check failed"

# Check admin interface
echo "Checking admin interface..."
curl -s -I https://admin.yourdomain.com | head -1 || echo "❌ Admin interface check failed"

# Check pod status
echo "Checking pod status..."
kubectl get pods -n medinovai | grep -v Running | grep -v Completed && echo "⚠️  Some pods not running" || echo "✅ All pods running"

# Check resource usage
echo "Checking resource usage..."
kubectl top pods -n medinovai | awk 'NR>1 && ($3+0) > 80 {print "⚠️ High CPU:", $1, $3}'
kubectl top pods -n medinovai | awk 'NR>1 && ($4+0) > 80 {print "⚠️ High Memory:", $1, $4}'

# Check database connectivity
echo "Checking database..."
kubectl exec deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
try:
    db = next(get_db())
    result = db.execute('SELECT version()')
    print('✅ Database connectivity OK')
except Exception as e:
    print('❌ Database connectivity failed:', str(e))
"

# Check recent errors
echo "Checking recent errors..."
ERROR_COUNT=$(kubectl logs -l app=medinovai-backend -n medinovai --since=24h | grep -i error | wc -l)
if [ $ERROR_COUNT -gt 100 ]; then
    echo "⚠️  High error count in last 24h: $ERROR_COUNT"
else
    echo "✅ Error count acceptable: $ERROR_COUNT"
fi

# Check certificate expiry
echo "Checking SSL certificates..."
EXPIRY_DAYS=$(echo | openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2 | xargs date -d | awk '{print int((mktime()-systime())/86400)}')
if [ $EXPIRY_DAYS -lt 30 ]; then
    echo "⚠️  SSL certificate expires in $EXPIRY_DAYS days"
else
    echo "✅ SSL certificate valid for $EXPIRY_DAYS days"
fi

echo "=== Health check completed ==="
```

#### 2. **Backup Verification**
```bash
# Check last backup status
echo "Checking backup status..."

# RDS backup
LATEST_BACKUP=$(aws rds describe-db-snapshots \
  --db-instance-identifier medinovai-prod-db \
  --snapshot-type automated \
  --max-items 1 \
  --query 'DBSnapshots[0].SnapshotCreateTime' \
  --output text)

if [ -n "$LATEST_BACKUP" ]; then
    echo "✅ Latest RDS backup: $LATEST_BACKUP"
else
    echo "❌ No recent RDS backup found"
fi

# Kubernetes backup
LATEST_K8S_BACKUP=$(velero backup get --output json | jq -r '.items[0].metadata.creationTimestamp')
if [ "$LATEST_K8S_BACKUP" != "null" ]; then
    echo "✅ Latest K8s backup: $LATEST_K8S_BACKUP"
else
    echo "❌ No recent Kubernetes backup found"
fi
```

#### 3. **Metrics Review**
```bash
# Check key metrics from last 24 hours
echo "Reviewing key metrics..."

# Query Prometheus for key metrics
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring &
PROMETHEUS_PID=$!
sleep 5

# Average response time
AVG_RESPONSE_TIME=$(curl -s 'http://localhost:9090/api/v1/query?query=avg_over_time(histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))[24h:1h])' | jq -r '.data.result[0].value[1]')
echo "24h Average Response Time: ${AVG_RESPONSE_TIME}s"

# Error rate
ERROR_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=avg_over_time(rate(http_requests_total{status=~"5.."}[5m])[24h:1h])' | jq -r '.data.result[0].value[1]')
echo "24h Error Rate: ${ERROR_RATE}"

# Conversation success rate
SUCCESS_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=avg_over_time((sum(conversations_success_total)/sum(conversations_total)*100)[24h:1h])' | jq -r '.data.result[0].value[1]')
echo "24h Conversation Success Rate: ${SUCCESS_RATE}%"

kill $PROMETHEUS_PID
```

### Evening Checklist (6:00 PM)

#### 1. **Capacity Planning Review**
```bash
# Check resource trends
echo "=== Daily Capacity Review ==="

# Check if auto-scaling triggered
HPA_EVENTS=$(kubectl get events --field-selector reason=SuccessfulRescale -n medinovai --sort-by='.lastTimestamp' | tail -5)
if [ -n "$HPA_EVENTS" ]; then
    echo "⚠️  Auto-scaling events today:"
    echo "$HPA_EVENTS"
else
    echo "✅ No auto-scaling events"
fi

# Check resource requests vs limits
kubectl describe nodes | grep -A 5 "Allocated resources"
```

#### 2. **Security Review**
```bash
# Check for security alerts
echo "Checking security events..."

# Check failed login attempts
FAILED_LOGINS=$(kubectl logs -l app=medinovai-backend -n medinovai --since=24h | grep "authentication failed" | wc -l)
if [ $FAILED_LOGINS -gt 50 ]; then
    echo "⚠️  High number of failed login attempts: $FAILED_LOGINS"
else
    echo "✅ Failed login attempts within normal range: $FAILED_LOGINS"
fi

# Check WAF blocks
aws wafv2 get-sampled-requests \
  --web-acl-arn $(aws wafv2 list-web-acls --scope CLOUDFRONT --query 'WebACLs[?Name==`medinovai-waf`].ARN' --output text) \
  --rule-metric-name blocked-requests \
  --scope CLOUDFRONT \
  --time-window StartTime=$(date -d '24 hours ago' +%s),EndTime=$(date +%s) \
  --max-items 10
```

---

## Incident Response

### Incident Classifications

| Priority | Response Time | Description | Examples |
|----------|---------------|-------------|----------|
| P0 - Critical | 15 minutes | Complete service outage | API down, security breach, data loss |
| P1 - High | 1 hour | Significant functionality impacted | Slow response times, partial outage |
| P2 - Medium | 4 hours | Minor functionality affected | Non-critical feature broken |
| P3 - Low | Next business day | Enhancement or optimization | UI improvements, documentation |

### P0 Incident Response Procedure

#### Phase 1: Initial Response (0-15 minutes)

1. **Acknowledge and Assess**
   ```bash
   # Immediately acknowledge in #incidents channel
   # Run initial assessment
   ./scripts/incident-assessment.sh
   
   # Gather initial information
   kubectl get pods -n medinovai -o wide
   kubectl get events --sort-by='.lastTimestamp' -n medinovai | tail -20
   curl -I https://api.yourdomain.com/health
   ```

2. **Establish Communication**
   - Create incident channel: `#incident-YYYYMMDD-HHMM`
   - Update status page: https://status.yourdomain.com
   - Notify stakeholders via incident notification system

3. **Begin Immediate Mitigation**
   ```bash
   # If recent deployment, consider rollback
   kubectl rollout undo deployment/medinovai-backend -n medinovai
   
   # If resource issues, scale up
   kubectl scale deployment medinovai-backend --replicas=5 -n medinovai
   
   # If database issues, check connections
   kubectl exec deployment/medinovai-backend -n medinovai -- python -c "
   from src.utils.database import get_db
   try:
       db = next(get_db())
       print('Database accessible')
   except Exception as e:
       print(f'Database error: {e}')
   "
   ```

#### Phase 2: Investigation and Resolution (15 minutes - 4 hours)

1. **Deep Dive Investigation**
   ```bash
   # Collect comprehensive logs
   kubectl logs -l app=medinovai-backend -n medinovai --since=1h > incident-logs.txt
   
   # Check metrics around incident time
   # Query Prometheus for anomalies
   
   # Check infrastructure
   aws rds describe-db-instances --db-instance-identifier medinovai-prod-db
   kubectl describe nodes
   ```

2. **Implement Fix**
   - Apply permanent solution
   - Verify fix effectiveness
   - Monitor for regression

3. **Validation**
   ```bash
   # Comprehensive system test
   ./scripts/smoke-test.sh
   
   # Monitor key metrics for 30 minutes
   watch -n 30 'curl -s https://api.yourdomain.com/health | jq .'
   ```

#### Phase 3: Post-Incident (0-48 hours after resolution)

1. **Immediate Post-Incident**
   - Update status page with resolution
   - Notify stakeholders of resolution
   - Begin collecting timeline and evidence

2. **Post-Incident Review (Within 24 hours)**
   - Schedule post-incident review meeting
   - Document timeline
   - Identify root cause
   - Create action items for prevention

### Incident Communication Templates

#### Initial Notification
```
🚨 INCIDENT ALERT - P0

Service: MedinovAI Chatbot
Impact: [Brief description of impact]
Start Time: [ISO timestamp]
Current Status: Investigating

Incident Commander: @[name]
Communication Channel: #incident-YYYYMMDD-HHMM

Next Update: In 15 minutes
Status Page: https://status.yourdomain.com
```

#### Update Notification
```
📊 INCIDENT UPDATE - P0

Service: MedinovAI Chatbot
Duration: [X minutes]
Status: [Investigating/Mitigating/Resolved]

Progress:
- [Action taken]
- [Current investigation]
- [Next steps]

Impact: [Current impact description]
ETA: [If known]

Next Update: In [X minutes]
```

#### Resolution Notification
```
✅ INCIDENT RESOLVED - P0

Service: MedinovAI Chatbot
Total Duration: [X hours Y minutes]
Resolution Time: [ISO timestamp]

Resolution:
[Brief description of what was done]

Impact Summary:
- Affected Users: [Estimate]
- Functionality Impacted: [Description]
- Data Impact: [If any]

Next Steps:
- Post-incident review scheduled for [date/time]
- Prevention measures to be implemented

Thank you for your patience during this incident.
```

---

## Backup and Recovery

### Daily Backup Procedures

#### 1. **Database Backup Verification**
```bash
#!/bin/bash
# Verify daily RDS backup completed

echo "Checking RDS backup status..."

LATEST_BACKUP=$(aws rds describe-db-snapshots \
  --db-instance-identifier medinovai-prod-db \
  --snapshot-type automated \
  --max-items 1 \
  --query 'DBSnapshots[0].[SnapshotCreateTime,Status]' \
  --output text)

BACKUP_TIME=$(echo $LATEST_BACKUP | cut -f1)
BACKUP_STATUS=$(echo $LATEST_BACKUP | cut -f2)

if [ "$BACKUP_STATUS" = "available" ]; then
    echo "✅ Latest backup completed: $BACKUP_TIME"
else
    echo "❌ Backup issue detected. Status: $BACKUP_STATUS"
    # Alert on-call team
fi

# Verify backup encryption
BACKUP_ID=$(aws rds describe-db-snapshots \
  --db-instance-identifier medinovai-prod-db \
  --snapshot-type automated \
  --max-items 1 \
  --query 'DBSnapshots[0].DBSnapshotIdentifier' \
  --output text)

ENCRYPTED=$(aws rds describe-db-snapshots \
  --db-snapshot-identifier $BACKUP_ID \
  --query 'DBSnapshots[0].Encrypted' \
  --output text)

if [ "$ENCRYPTED" = "true" ]; then
    echo "✅ Backup is encrypted"
else
    echo "❌ Backup encryption issue"
fi
```

#### 2. **Application Data Backup**
```bash
# Kubernetes resources backup with Velero
echo "Checking Velero backup status..."

# Get latest backup
LATEST_VELERO=$(velero backup get --output json | jq -r '.items[0] | "\(.metadata.name) \(.status.phase)"')
BACKUP_NAME=$(echo $LATEST_VELERO | cut -d' ' -f1)
BACKUP_STATUS=$(echo $LATEST_VELERO | cut -d' ' -f2)

if [ "$BACKUP_STATUS" = "Completed" ]; then
    echo "✅ Kubernetes backup completed: $BACKUP_NAME"
else
    echo "❌ Kubernetes backup issue: $BACKUP_STATUS"
fi

# Verify backup contents
velero backup describe $BACKUP_NAME --details
```

#### 3. **Configuration Backup**
```bash
# Backup critical configurations
echo "Backing up configurations..."

mkdir -p /backup/configs/$(date +%Y%m%d)
cd /backup/configs/$(date +%Y%m%d)

# Export secrets (encrypted)
kubectl get secrets -n medinovai -o yaml > secrets.yaml

# Export configmaps
kubectl get configmaps -n medinovai -o yaml > configmaps.yaml

# Export ingress configurations
kubectl get ingress -n medinovai -o yaml > ingress.yaml

# Export service configurations  
kubectl get services -n medinovai -o yaml > services.yaml

# Encrypt and upload to S3
tar -czf medinovai-config-$(date +%Y%m%d).tar.gz *.yaml
aws s3 cp medinovai-config-$(date +%Y%m%d).tar.gz s3://medinovai-backups/configs/
```

### Recovery Procedures

#### Database Point-in-Time Recovery
```bash
#!/bin/bash
# Database point-in-time recovery procedure

echo "Starting database point-in-time recovery..."
echo "WARNING: This will create a new database instance"

# Get the parameters
read -p "Enter target restore time (YYYY-MM-DDTHH:MM:SS): " RESTORE_TIME
read -p "Enter new instance identifier: " NEW_INSTANCE_ID
read -p "Confirm recovery (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Recovery cancelled"
    exit 1
fi

# Perform point-in-time recovery
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier medinovai-prod-db \
  --target-db-instance-identifier $NEW_INSTANCE_ID \
  --restore-time $RESTORE_TIME \
  --db-subnet-group-name medinovai-db-subnet-group \
  --vpc-security-group-ids $(aws rds describe-db-instances \
    --db-instance-identifier medinovai-prod-db \
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
    --output text)

echo "Recovery initiated. Monitor progress with:"
echo "aws rds describe-db-instances --db-instance-identifier $NEW_INSTANCE_ID"

# Wait for recovery to complete
echo "Waiting for instance to become available..."
aws rds wait db-instance-available --db-instance-identifier $NEW_INSTANCE_ID

echo "Recovery completed. Update connection strings to use new instance."
```

#### Application Recovery
```bash
#!/bin/bash
# Full application recovery procedure

echo "Starting full application recovery..."

# 1. Restore Kubernetes resources
read -p "Enter Velero backup name to restore from: " BACKUP_NAME

# Create new namespace for recovery
kubectl create namespace medinovai-recovery

# Restore from backup
velero restore create medinovai-recovery-$(date +%Y%m%d%H%M) \
  --from-backup $BACKUP_NAME \
  --namespace-mappings medinovai:medinovai-recovery

# 2. Wait for restore to complete
echo "Waiting for restore to complete..."
velero restore get medinovai-recovery-$(date +%Y%m%d%H%M) --watch

# 3. Update database connection strings if needed
echo "Update database connections if using recovered database"

# 4. Validate restored application
echo "Validating restored application..."
kubectl get pods -n medinovai-recovery
kubectl logs -l app=medinovai-backend -n medinovai-recovery --tail=50

# 5. Test basic functionality
kubectl port-forward svc/medinovai-backend-service 8080:80 -n medinovai-recovery &
sleep 5
curl http://localhost:8080/health
```

---

## Maintenance Procedures

### Weekly Maintenance (Sunday 2:00 AM EST)

#### 1. **Security Updates**
```bash
#!/bin/bash
# Weekly security maintenance

echo "Starting weekly security maintenance..."

# Check for critical CVEs
trivy image medinovai/backend:latest --severity CRITICAL,HIGH

# Update base images if needed
docker pull medinovai/backend:latest
docker pull medinovai/frontend:latest

# Check certificate expiration
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com 2>/dev/null | openssl x509 -noout -enddate

# Rotate access keys if scheduled
if [ $(date +%d) -eq 01 ]; then
    echo "Monthly key rotation due"
    # Implement key rotation procedure
fi
```

#### 2. **Database Maintenance**
```bash
# Database maintenance tasks
echo "Starting database maintenance..."

kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())

# Update statistics
db.execute('ANALYZE;')

# Check for dead tuples
result = db.execute('''
  SELECT schemaname, tablename, n_dead_tup, n_live_tup,
         round(n_dead_tup::float / (n_live_tup + n_dead_tup) * 100, 2) as dead_percentage
  FROM pg_stat_user_tables 
  WHERE n_dead_tup > 1000
  ORDER BY dead_percentage DESC;
''')

print('Tables needing VACUUM:')
for row in result:
    if row[4] > 10:  # More than 10% dead tuples
        print(f'  {row[1]}: {row[4]}% dead tuples')
        db.execute(f'VACUUM ANALYZE {row[1]};')

db.commit()
print('Database maintenance completed')
"
```

#### 3. **Log Cleanup**
```bash
# Clean up old logs and data
echo "Cleaning up old logs..."

# Archive logs older than 90 days
find /var/log/medinovai -name "*.log" -mtime +90 -exec gzip {} \;
find /var/log/medinovai -name "*.log.gz" -mtime +180 -delete

# Clean up old Prometheus data beyond retention
kubectl exec prometheus-kube-prometheus-prometheus-0 -n monitoring -- \
  promtool tsdb delete-series --match-all

# Clean up old audit logs (keep 7 years for HIPAA)
aws s3 ls s3://medinovai-audit-logs/ --recursive | \
  awk '$1 <= "'$(date -d '7 years ago' '+%Y-%m-%d')'" {print $4}' | \
  xargs -I {} aws s3 rm s3://medinovai-audit-logs/{}
```

### Monthly Maintenance (First Sunday 1:00 AM EST)

#### 1. **Capacity Planning Review**
```bash
# Monthly capacity planning
echo "Generating monthly capacity report..."

# Resource utilization trends
kubectl top nodes > monthly-capacity-$(date +%Y%m).txt
kubectl top pods -n medinovai >> monthly-capacity-$(date +%Y%m).txt

# Database growth analysis
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())

result = db.execute('''
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
  FROM pg_tables 
  WHERE schemaname = 'public'
  ORDER BY size_bytes DESC;
''')

print('Database size by table:')
for row in result:
    print(f'  {row[1]}: {row[2]}')
"

# Cost analysis
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '1 month ago' +%Y-%m-01),End=$(date +%Y-%m-01) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

#### 2. **Security Audit**
```bash
# Monthly security audit
echo "Performing monthly security audit..."

# Check for unused access keys
aws iam list-access-keys --output table

# Review security groups
aws ec2 describe-security-groups --query 'SecurityGroups[?GroupName==`medinovai-*`]'

# Check SSL configurations
curl -I https://api.yourdomain.com | grep -i security
curl -I https://admin.yourdomain.com | grep -i security

# Review audit logs for anomalies
aws logs filter-log-events \
  --log-group-name /medinovai/audit \
  --start-time $(date -d '1 month ago' +%s)000 \
  --filter-pattern "{ $.event_type = \"PERMISSION_CHANGE\" || $.event_type = \"EXPORT_DATA\" }"
```

---

## Escalation Matrix

### On-Call Rotation

| Role | Primary | Secondary | Hours |
|------|---------|-----------|-------|
| L1 Support | on-call-l1@yourdomain.com | backup-l1@yourdomain.com | 24x7 |
| L2 Engineering | on-call-l2@yourdomain.com | backup-l2@yourdomain.com | 24x7 |
| L3 Senior | on-call-l3@yourdomain.com | backup-l3@yourdomain.com | Business hours + escalation |

### Escalation Triggers

#### Automatic Escalation
- P0 incidents not acknowledged within 5 minutes
- P0 incidents not resolved within 30 minutes
- P1 incidents not resolved within 2 hours
- Multiple P2 incidents in 24 hours

#### Manual Escalation
- Complex technical issues requiring specialized knowledge
- Security incidents requiring legal/compliance involvement
- Customer-facing incidents affecting SLA
- Resource or budget approval needed for resolution

### Contact Information

#### Internal Teams
```
L1 Support (24x7):
- Phone: +1-XXX-XXX-XXXX
- Slack: #l1-support
- Email: on-call-l1@yourdomain.com

L2 Engineering (24x7):
- Phone: +1-XXX-XXX-XXXX
- Slack: #l2-engineering  
- Email: on-call-l2@yourdomain.com

Security Team:
- Phone: +1-XXX-XXX-XXXX (emergencies only)
- Slack: #security-incident
- Email: security@yourdomain.com

Management:
- Engineering Manager: eng-manager@yourdomain.com
- Product Manager: product@yourdomain.com
- CTO: cto@yourdomain.com
```

#### External Vendors
```
AWS Support:
- Enterprise Support: Open case in AWS Console
- Phone: 1-800-xxx-xxxx
- Severity 1 (Production Down): Immediate response

Twilio Support:
- Support Console: https://support.twilio.com
- Phone: 1-855-xxx-xxxx
- Email: help@twilio.com

OpenAI Support:
- Support: https://help.openai.com/en/
- Email: support@openai.com
- Status: https://status.openai.com/
```

---

## Common Scenarios

### Scenario 1: High CPU Usage

**Symptoms:** Pods showing high CPU usage, slow response times

**Investigation:**
```bash
# Check current CPU usage
kubectl top pods -n medinovai

# Check recent CPU trends
kubectl exec prometheus-kube-prometheus-prometheus-0 -n monitoring -- \
  promtool query instant 'rate(container_cpu_usage_seconds_total{pod=~"medinovai-.*"}[5m]) * 100'

# Check for runaway processes
kubectl exec -it deployment/medinovai-backend -n medinovai -- top
```

**Resolution:**
1. Horizontal scaling if temporary spike
2. Optimize code if sustained high usage
3. Increase resource limits if consistently hitting limits

### Scenario 2: Database Connection Pool Exhaustion

**Symptoms:** "Too many connections" errors, connection timeouts

**Investigation:**
```bash
# Check current connections
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
result = db.execute('SELECT count(*), state FROM pg_stat_activity GROUP BY state')
for row in result:
    print(f'{row[1]}: {row[0]} connections')
"
```

**Resolution:**
1. Restart backend pods to reset connections
2. Implement connection pooling if not present
3. Scale database instance if consistently hitting limits

### Scenario 3: SSL Certificate Expiration

**Symptoms:** SSL warnings, certificate validation errors

**Investigation:**
```bash
# Check certificate expiration
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# Check ACM certificate status
aws acm list-certificates --query 'CertificateSummaryList[?DomainName==`*.yourdomain.com`]'
```

**Resolution:**
1. For ACM certificates: Usually auto-renewed, verify DNS validation
2. For Let's Encrypt: Trigger cert-manager renewal
3. Update ingress configuration with new certificate

### Scenario 4: Failed Deployment

**Symptoms:** New pods failing to start, rollout stuck

**Investigation:**
```bash
# Check rollout status
kubectl rollout status deployment/medinovai-backend -n medinovai

# Check pod events
kubectl describe pod $(kubectl get pods -n medinovai -l app=medinovai-backend -o jsonpath='{.items[0].metadata.name}') -n medinovai

# Check image pull issues
kubectl get events --field-selector type=Warning -n medinovai
```

**Resolution:**
1. Rollback to previous version
2. Fix configuration issues
3. Re-deploy with corrected configuration

### Scenario 5: External API Failures

**Symptoms:** OpenAI API errors, Twilio delivery failures

**Investigation:**
```bash
# Check external service status
curl -I https://api.openai.com/
curl -I https://api.twilio.com/

# Check service-specific error rates
kubectl logs -l app=medinovai-backend -n medinovai | grep -i "openai\|twilio" | tail -50
```

**Resolution:**
1. Implement exponential backoff
2. Use fallback services if available
3. Notify users of external service issues

---

## Post-Incident Procedures

### Post-Incident Review Template

```markdown
# Post-Incident Review - [Incident ID]

## Incident Summary
- **Date/Time**: [Start] - [End]
- **Duration**: [Total time]
- **Severity**: P[0-3]
- **Impact**: [Brief description]

## Timeline
| Time | Event | Action Taken |
|------|-------|--------------|
| HH:MM | Incident detected | [Action] |
| HH:MM | Initial response | [Action] |
| HH:MM | Root cause identified | [Action] |
| HH:MM | Fix implemented | [Action] |
| HH:MM | Incident resolved | [Action] |

## Root Cause Analysis
### What Happened
[Detailed explanation]

### Why It Happened
[Root cause analysis]

### Contributing Factors
- [Factor 1]
- [Factor 2]

## Resolution
### Immediate Fix
[What was done to resolve]

### Verification
[How resolution was verified]

## Impact Assessment
- **Users Affected**: [Number/percentage]
- **Revenue Impact**: [If applicable]
- **Reputation Impact**: [If applicable]
- **SLA Impact**: [If applicable]

## Action Items
| Item | Owner | Due Date | Status |
|------|-------|----------|--------|
| [Preventive action 1] | [Name] | [Date] | Open |
| [Preventive action 2] | [Name] | [Date] | Open |

## Lessons Learned
### What Went Well
- [Success 1]
- [Success 2]

### What Could Be Improved
- [Improvement 1]
- [Improvement 2]

## Follow-up
- Post-incident review meeting: [Date/Time]
- Follow-up review: [Date for checking action items]
```

---

This operations runbook should be reviewed and updated quarterly to ensure it remains current with system changes and lessons learned from incidents. All team members should be familiar with these procedures and practice them regularly. 