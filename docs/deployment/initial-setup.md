# Initial Setup Guide - MedinovAI Chatbot

This guide provides step-by-step instructions for setting up a production-ready MedinovAI Chatbot system on AWS infrastructure with full HIPAA compliance and security controls.

## Prerequisites

### Technical Requirements

#### AWS Account Setup
- **AWS Account**: With administrative access
- **AWS CLI**: Version 2.0+ installed and configured
- **AWS IAM**: Appropriate permissions for EKS, RDS, S3, etc.
- **Domain**: Registered domain for production deployment
- **SSL Certificate**: Valid SSL certificate (ACM recommended)

#### Local Development Tools
- **Terraform**: Version 1.5+ for infrastructure as code
- **kubectl**: Kubernetes command-line tool
- **Helm**: Kubernetes package manager
- **Docker**: For container building and testing
- **Git**: Version control system

#### Required Credentials
- **OpenAI API Key**: For language model access
- **Twilio Account**: For SMS and voice services (optional for initial setup)
- **GitHub Token**: For CI/CD integration
- **Domain Registrar Access**: For DNS configuration

### Compliance Requirements

#### HIPAA Compliance Preparation
- **Business Associate Agreements**: Ready for vendor execution
- **Risk Assessment**: Completed security risk assessment
- **Policies & Procedures**: HIPAA policies documented
- **Staff Training**: HIPAA training completed for all staff

#### Security Infrastructure
- **AWS KMS**: Key management service setup
- **AWS CloudTrail**: Audit logging enabled
- **AWS Config**: Compliance monitoring configured
- **AWS Inspector**: Vulnerability scanning enabled

---

## Phase 1: AWS Infrastructure Setup

### 1. **Initial AWS Configuration**

#### Configure AWS CLI
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
# AWS Access Key ID: [Enter your access key]
# AWS Secret Access Key: [Enter your secret key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

#### Set Environment Variables
```bash
# Create environment configuration
cat > deployment.env << EOF
# Deployment Configuration
AWS_REGION=us-east-1
ENVIRONMENT=production
CLUSTER_NAME=medinovai-prod
DOMAIN_NAME=yourdomain.com
SUBDOMAIN_API=api.yourdomain.com
SUBDOMAIN_ADMIN=admin.yourdomain.com

# Database Configuration
DB_INSTANCE_CLASS=db.r5.large
DB_STORAGE_SIZE=100
DB_BACKUP_RETENTION=30

# Security Configuration
ENABLE_WAF=true
ENABLE_CLOUDTRAIL=true
ENABLE_GUARDDUTY=true
ENABLE_INSPECTOR=true

# Compliance Configuration
HIPAA_COMPLIANCE=true
ENCRYPTION_AT_REST=true
BACKUP_ENCRYPTION=true
EOF

# Load environment variables
source deployment.env
```

### 2. **Infrastructure as Code Setup**

#### Initialize Terraform
```bash
# Clone infrastructure repository
git clone https://github.com/myonsite-healthcare/medinovai-infrastructure
cd medinovai-infrastructure

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars << EOF
# Basic Configuration
aws_region = "us-east-1"
environment = "production"
project_name = "medinovai"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Domain Configuration
domain_name = "yourdomain.com"
create_hosted_zone = true

# EKS Configuration
cluster_name = "medinovai-prod"
cluster_version = "1.28"
node_group_instance_types = ["t3.large"]
node_group_scaling_config = {
  desired_size = 3
  max_size     = 10
  min_size     = 1
}

# Database Configuration
rds_instance_class = "db.r5.large"
rds_allocated_storage = 100
rds_backup_retention_period = 30
rds_backup_window = "03:00-04:00"
rds_maintenance_window = "sun:04:00-sun:05:00"

# Security Configuration
enable_waf = true
enable_guardduty = true
enable_cloudtrail = true
enable_config = true

# HIPAA Compliance
hipaa_compliance = true
enable_encryption = true
enable_backup_encryption = true
log_retention_days = 2555  # 7 years
EOF
```

#### Deploy Core Infrastructure
```bash
# Plan the deployment
terraform plan -var-file=terraform.tfvars

# Review the plan carefully
# Ensure all security and compliance features are enabled

# Apply the infrastructure
terraform apply -var-file=terraform.tfvars

# Save important outputs
terraform output > infrastructure-outputs.txt
```

### 3. **Kubernetes Cluster Setup**

#### Configure kubectl
```bash
# Update kubeconfig for EKS cluster
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Verify cluster access
kubectl get nodes
kubectl get namespaces

# Install cluster autoscaler
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# Annotate the cluster autoscaler service account
kubectl annotate serviceaccount cluster-autoscaler \
  -n kube-system \
  eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT-ID:role/cluster-autoscaler-role
```

#### Install Essential Add-ons
```bash
# Install AWS Load Balancer Controller
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# Install with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Install Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Install cert-manager for SSL
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

---

## Phase 2: Security and Compliance Configuration

### 1. **AWS Security Services**

#### Enable AWS GuardDuty
```bash
# Enable GuardDuty
aws guardduty create-detector --enable --finding-publishing-frequency FIFTEEN_MINUTES

# Configure threat intelligence feeds
aws guardduty create-threat-intel-set \
  --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
  --name "MedinovAI-ThreatIntel" \
  --format TXT \
  --location s3://your-security-bucket/threat-intel.txt \
  --activate
```

#### Configure AWS Config
```bash
# Create configuration aggregator
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name medinovai-compliance \
  --account-aggregation-sources AccountIds=${AWS_ACCOUNT_ID},AllAwsRegions=true

# Enable HIPAA compliance rules
aws configservice put-config-rule \
  --config-rule file://hipaa-config-rules.json
```

#### Setup AWS CloudTrail
```bash
# Create CloudTrail for audit logging
aws cloudtrail create-trail \
  --name medinovai-audit-trail \
  --s3-bucket-name medinovai-audit-logs-${AWS_ACCOUNT_ID} \
  --include-global-service-events \
  --is-multi-region-trail \
  --enable-log-file-validation

# Start logging
aws cloudtrail start-logging --name medinovai-audit-trail
```

### 2. **Encryption Configuration**

#### AWS KMS Key Setup
```bash
# Create KMS key for application encryption
aws kms create-key \
  --description "MedinovAI Application Encryption Key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT

# Create alias for the key
aws kms create-alias \
  --alias-name alias/medinovai-app \
  --target-key-id $(aws kms describe-key --key-id alias/medinovai-app --query 'KeyMetadata.KeyId' --output text)

# Create key for RDS encryption
aws kms create-key \
  --description "MedinovAI RDS Encryption Key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT

aws kms create-alias \
  --alias-name alias/medinovai-rds \
  --target-key-id $(aws kms describe-key --key-id alias/medinovai-rds --query 'KeyMetadata.KeyId' --output text)
```

#### Kubernetes Secrets Management
```bash
# Install AWS Secrets Manager CSI driver
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml

# Create namespace for MedinovAI
kubectl create namespace medinovai

# Create service account with IRSA
kubectl create serviceaccount medinovai-secrets-sa -n medinovai
kubectl annotate serviceaccount medinovai-secrets-sa \
  -n medinovai \
  eks.amazonaws.com/role-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:role/medinovai-secrets-role
```

### 3. **Network Security**

#### VPC Security Groups
```bash
# Create security group for web traffic
aws ec2 create-security-group \
  --group-name medinovai-web-sg \
  --description "MedinovAI Web Security Group" \
  --vpc-id $(terraform output -raw vpc_id)

# Allow HTTPS traffic
aws ec2 authorize-security-group-ingress \
  --group-id $(aws ec2 describe-security-groups --group-names medinovai-web-sg --query 'SecurityGroups[0].GroupId' --output text) \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Create security group for database
aws ec2 create-security-group \
  --group-name medinovai-db-sg \
  --description "MedinovAI Database Security Group" \
  --vpc-id $(terraform output -raw vpc_id)

# Allow database access only from application
aws ec2 authorize-security-group-ingress \
  --group-id $(aws ec2 describe-security-groups --group-names medinovai-db-sg --query 'SecurityGroups[0].GroupId' --output text) \
  --protocol tcp \
  --port 5432 \
  --source-group $(aws ec2 describe-security-groups --group-names medinovai-app-sg --query 'SecurityGroups[0].GroupId' --output text)
```

#### WAF Configuration
```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name medinovai-waf \
  --scope CLOUDFRONT \
  --default-action Allow={} \
  --rules file://waf-rules.json \
  --region us-east-1
```

---

## Phase 3: Database and Storage Setup

### 1. **PostgreSQL Database Configuration**

#### RDS Instance Setup
```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name medinovai-db-subnet-group \
  --db-subnet-group-description "MedinovAI Database Subnet Group" \
  --subnet-ids $(terraform output -raw private_subnet_ids | tr ',' ' ')

# Create parameter group for HIPAA compliance
aws rds create-db-parameter-group \
  --db-parameter-group-name medinovai-postgres-params \
  --db-parameter-group-family postgres15 \
  --description "MedinovAI PostgreSQL Parameters"

# Configure security parameters
aws rds modify-db-parameter-group \
  --db-parameter-group-name medinovai-postgres-params \
  --parameters ParameterName=log_statement,ParameterValue=all,ApplyMethod=immediate \
  --parameters ParameterName=log_min_duration_statement,ParameterValue=1000,ApplyMethod=immediate \
  --parameters ParameterName=ssl,ParameterValue=on,ApplyMethod=pending-reboot
```

#### Database Creation
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier medinovai-prod-db \
  --db-instance-class db.r5.large \
  --engine postgres \
  --engine-version 15.4 \
  --master-username medinovai_admin \
  --master-user-password $(openssl rand -base64 32) \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --kms-key-id alias/medinovai-rds \
  --vpc-security-group-ids $(aws ec2 describe-security-groups --group-names medinovai-db-sg --query 'SecurityGroups[0].GroupId' --output text) \
  --db-subnet-group-name medinovai-db-subnet-group \
  --backup-retention-period 30 \
  --backup-window 03:00-04:00 \
  --maintenance-window sun:04:00-sun:05:00 \
  --multi-az \
  --auto-minor-version-upgrade \
  --deletion-protection \
  --copy-tags-to-snapshot \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --monitoring-interval 60 \
  --monitoring-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/rds-monitoring-role

# Wait for database to be available
aws rds wait db-instance-available --db-instance-identifier medinovai-prod-db
```

### 2. **Redis Cache Setup**

#### ElastiCache Configuration
```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name medinovai-cache-subnet-group \
  --cache-subnet-group-description "MedinovAI Cache Subnet Group" \
  --subnet-ids $(terraform output -raw private_subnet_ids | tr ',' ' ')

# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id medinovai-redis \
  --description "MedinovAI Redis Cluster" \
  --node-type cache.r6g.large \
  --engine redis \
  --engine-version 7.0 \
  --port 6379 \
  --cache-parameter-group-name default.redis7 \
  --cache-subnet-group-name medinovai-cache-subnet-group \
  --security-group-ids $(aws ec2 describe-security-groups --group-names medinovai-cache-sg --query 'SecurityGroups[0].GroupId' --output text) \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token $(openssl rand -base64 32) \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --snapshot-retention-limit 7 \
  --snapshot-window 03:00-05:00
```

### 3. **S3 Storage Configuration**

#### Create S3 Buckets
```bash
# Application data bucket
aws s3 mb s3://medinovai-app-data-${AWS_ACCOUNT_ID} --region $AWS_REGION

# Configure bucket encryption
aws s3api put-bucket-encryption \
  --bucket medinovai-app-data-${AWS_ACCOUNT_ID} \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms",
          "KMSMasterKeyID": "alias/medinovai-app"
        }
      }
    ]
  }'

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket medinovai-app-data-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket medinovai-app-data-${AWS_ACCOUNT_ID} \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## Phase 4: Application Deployment

### 1. **Secrets Management**

#### Create Application Secrets
```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name medinovai/prod/database \
  --description "MedinovAI Production Database Credentials" \
  --secret-string '{
    "host": "'$(aws rds describe-db-instances --db-instance-identifier medinovai-prod-db --query 'DBInstances[0].Endpoint.Address' --output text)'",
    "port": "5432",
    "username": "medinovai_admin",
    "password": "'$(aws rds describe-db-instances --db-instance-identifier medinovai-prod-db --query 'DBInstances[0].MasterUsername' --output text)'",
    "database": "medinovai"
  }'

aws secretsmanager create-secret \
  --name medinovai/prod/redis \
  --description "MedinovAI Production Redis Configuration" \
  --secret-string '{
    "host": "'$(aws elasticache describe-replication-groups --replication-group-id medinovai-redis --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address' --output text)'",
    "port": "6379",
    "auth_token": "your-redis-auth-token"
  }'

aws secretsmanager create-secret \
  --name medinovai/prod/openai \
  --description "MedinovAI OpenAI API Key" \
  --secret-string '{
    "api_key": "your-openai-api-key"
  }'

aws secretsmanager create-secret \
  --name medinovai/prod/jwt \
  --description "MedinovAI JWT Secrets" \
  --secret-string '{
    "secret_key": "'$(openssl rand -base64 64)'",
    "algorithm": "RS256"
  }'
```

#### Create Kubernetes Secret Store
```yaml
# Create secretstore.yaml
cat > secretstore.yaml << EOF
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: medinovai-secrets
  namespace: medinovai
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "medinovai/prod/database"
        objectType: "secretsmanager"
        jmesPath:
          - path: "host"
            objectAlias: "db_host"
          - path: "port"
            objectAlias: "db_port"
          - path: "username"
            objectAlias: "db_username"
          - path: "password"
            objectAlias: "db_password"
          - path: "database"
            objectAlias: "db_name"
      - objectName: "medinovai/prod/redis"
        objectType: "secretsmanager"
        jmesPath:
          - path: "host"
            objectAlias: "redis_host"
          - path: "port"
            objectAlias: "redis_port"
          - path: "auth_token"
            objectAlias: "redis_auth_token"
      - objectName: "medinovai/prod/openai"
        objectType: "secretsmanager"
        jmesPath:
          - path: "api_key"
            objectAlias: "openai_api_key"
      - objectName: "medinovai/prod/jwt"
        objectType: "secretsmanager"
        jmesPath:
          - path: "secret_key"
            objectAlias: "jwt_secret_key"
          - path: "algorithm"
            objectAlias: "jwt_algorithm"
  secretObjects:
  - secretName: medinovai-secrets
    type: Opaque
    data:
    - objectName: "db_host"
      key: "DB_HOST"
    - objectName: "db_port"
      key: "DB_PORT"
    - objectName: "db_username"
      key: "DB_USERNAME"
    - objectName: "db_password"
      key: "DB_PASSWORD"
    - objectName: "db_name"
      key: "DB_NAME"
    - objectName: "redis_host"
      key: "REDIS_HOST"
    - objectName: "redis_port"
      key: "REDIS_PORT"
    - objectName: "redis_auth_token"
      key: "REDIS_AUTH_TOKEN"
    - objectName: "openai_api_key"
      key: "OPENAI_API_KEY"
    - objectName: "jwt_secret_key"
      key: "JWT_SECRET_KEY"
    - objectName: "jwt_algorithm"
      key: "JWT_ALGORITHM"
EOF

kubectl apply -f secretstore.yaml
```

### 2. **Application Configuration**

#### Create ConfigMap
```yaml
# Create configmap.yaml
cat > configmap.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: medinovai-config
  namespace: medinovai
data:
  APP_NAME: "MedinovAI Chatbot"
  APP_VERSION: "1.0.0"
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "info"
  
  # Server Configuration
  HOST: "0.0.0.0"
  PORT: "8000"
  CORS_ORIGINS: "https://admin.yourdomain.com,https://api.yourdomain.com"
  
  # Feature Flags
  ENABLE_VOICE_CHAT: "true"
  ENABLE_MATTERMOST: "true"
  ENABLE_EHR_INTEGRATION: "false"
  
  # Security Configuration
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "60"
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: "7"
  
  # Rate Limiting
  RATE_LIMIT_REQUESTS_PER_MINUTE: "60"
  RATE_LIMIT_BURST: "100"
  
  # AI Configuration
  OPENAI_MODEL: "gpt-4-turbo"
  OPENAI_TEMPERATURE: "0.3"
  OPENAI_MAX_TOKENS: "1000"
  
  # Monitoring Configuration
  PROMETHEUS_ENABLED: "true"
  METRICS_PORT: "9090"
  HEALTH_CHECK_ENDPOINT: "/health"
EOF

kubectl apply -f configmap.yaml
```

### 3. **Deploy Application**

#### Backend Deployment
```yaml
# Create backend-deployment.yaml
cat > backend-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medinovai-backend
  namespace: medinovai
  labels:
    app: medinovai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: medinovai-backend
  template:
    metadata:
      labels:
        app: medinovai-backend
    spec:
      serviceAccountName: medinovai-secrets-sa
      containers:
      - name: medinovai-backend
        image: medinovai/backend:1.0.0
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: DATABASE_URL
          value: "postgresql://\$(DB_USERNAME):\$(DB_PASSWORD)@\$(DB_HOST):\$(DB_PORT)/\$(DB_NAME)"
        - name: REDIS_URL
          value: "redis://:\$(REDIS_AUTH_TOKEN)@\$(REDIS_HOST):\$(REDIS_PORT)"
        envFrom:
        - configMapRef:
            name: medinovai-config
        - secretRef:
            name: medinovai-secrets
        volumeMounts:
        - name: secrets-store
          mountPath: "/mnt/secrets-store"
          readOnly: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      volumes:
      - name: secrets-store
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: "medinovai-secrets"
EOF

kubectl apply -f backend-deployment.yaml
```

#### Frontend Deployment
```yaml
# Create frontend-deployment.yaml
cat > frontend-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medinovai-frontend
  namespace: medinovai
  labels:
    app: medinovai-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: medinovai-frontend
  template:
    metadata:
      labels:
        app: medinovai-frontend
    spec:
      containers:
      - name: medinovai-frontend
        image: medinovai/frontend:1.0.0
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.yourdomain.com"
        - name: NEXTAUTH_URL
          value: "https://admin.yourdomain.com"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
EOF

kubectl apply -f frontend-deployment.yaml
```

### 4. **Service and Ingress Configuration**

#### Create Services
```yaml
# Create services.yaml
cat > services.yaml << EOF
apiVersion: v1
kind: Service
metadata:
  name: medinovai-backend-service
  namespace: medinovai
spec:
  selector:
    app: medinovai-backend
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: medinovai-frontend-service
  namespace: medinovai
spec:
  selector:
    app: medinovai-frontend
  ports:
  - name: http
    port: 80
    targetPort: 3000
  type: ClusterIP
EOF

kubectl apply -f services.yaml
```

#### Configure Ingress
```yaml
# Create ingress.yaml
cat > ingress.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: medinovai-ingress
  namespace: medinovai
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:ACCOUNT-ID:certificate/CERTIFICATE-ID
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{"Type": "redirect", "RedirectConfig": { "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}'
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT-ID:global/webacl/medinovai-waf/WAF-ID
spec:
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ssl-redirect
            port:
              name: use-annotation
      - path: /
        pathType: Prefix
        backend:
          service:
            name: medinovai-backend-service
            port:
              number: 80
  - host: admin.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ssl-redirect
            port:
              name: use-annotation
      - path: /
        pathType: Prefix
        backend:
          service:
            name: medinovai-frontend-service
            port:
              number: 80
EOF

kubectl apply -f ingress.yaml
```

---

## Phase 5: Monitoring and Observability

### 1. **Prometheus and Grafana Setup**

#### Install Prometheus Stack
```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp3 \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword=admin123 \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.storageClassName=gp3 \
  --set grafana.persistence.size=10Gi
```

#### Configure Grafana Dashboards
```bash
# Create Grafana dashboard ConfigMap
kubectl create configmap medinovai-dashboard \
  --from-file=dashboards/ \
  --namespace monitoring

# Label ConfigMap for Grafana discovery
kubectl label configmap medinovai-dashboard \
  grafana_dashboard=1 \
  --namespace monitoring
```

### 2. **Logging Setup**

#### Install Fluent Bit
```bash
# Add Fluent Bit Helm repository
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

# Install Fluent Bit
helm install fluent-bit fluent/fluent-bit \
  --namespace kube-system \
  --set serviceAccount.create=false \
  --set serviceAccount.name=fluent-bit \
  --set config.outputs="[OUTPUT]\n    Name cloudwatch_logs\n    Match *\n    region us-east-1\n    log_group_name /medinovai/prod\n    auto_create_group true"
```

### 3. **Alerting Configuration**

#### Configure AlertManager
```yaml
# Create alertmanager-config.yaml
cat > alertmanager-config.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-prometheus-kube-prometheus-alertmanager
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'alerts@yourdomain.com'
    
    route:
      group_by: ['alertname']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 1h
      receiver: 'web.hook'
    
    receivers:
    - name: 'web.hook'
      email_configs:
      - to: 'admin@yourdomain.com'
        subject: 'MedinovAI Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
EOF

kubectl apply -f alertmanager-config.yaml
```

---

## Phase 6: Database Migration and Initial Data

### 1. **Database Migration**

#### Run Database Migrations
```bash
# Create migration job
kubectl create job medinovai-migrate \
  --image=medinovai/backend:1.0.0 \
  --namespace=medinovai \
  -- alembic upgrade head

# Wait for migration to complete
kubectl wait --for=condition=complete job/medinovai-migrate -n medinovai --timeout=300s

# Check migration status
kubectl logs job/medinovai-migrate -n medinovai
```

#### Load Initial Data
```bash
# Create initial data job
kubectl create job medinovai-init-data \
  --image=medinovai/backend:1.0.0 \
  --namespace=medinovai \
  -- python scripts/load_initial_data.py

# Monitor progress
kubectl logs -f job/medinovai-init-data -n medinovai
```

### 2. **Create Admin User**

```bash
# Create admin user
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
from src.models.user import User
from src.utils.auth import get_password_hash

db = next(get_db())
admin_user = User(
    email='admin@yourdomain.com',
    phone_number='+1234567890',
    is_admin=True,
    is_verified=True,
    password_hash=get_password_hash('admin123')
)
db.add(admin_user)
db.commit()
print('Admin user created successfully')
"
```

---

## Phase 7: DNS and SSL Configuration

### 1. **DNS Configuration**

#### Update DNS Records
```bash
# Get Load Balancer DNS name
LOAD_BALANCER_DNS=$(kubectl get ingress medinovai-ingress -n medinovai -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Create DNS records
aws route53 change-resource-record-sets \
  --hosted-zone-id $(aws route53 list-hosted-zones --query "HostedZones[?Name=='yourdomain.com.'].Id" --output text | cut -d'/' -f3) \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.yourdomain.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$LOAD_BALANCER_DNS'"}]
        }
      },
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "admin.yourdomain.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$LOAD_BALANCER_DNS'"}]
        }
      }
    ]
  }'
```

### 2. **SSL Certificate Validation**

```bash
# Verify SSL certificate
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com

# Test HTTPS connectivity
curl -I https://api.yourdomain.com/health
curl -I https://admin.yourdomain.com
```

---

## Phase 8: Testing and Validation

### 1. **System Health Checks**

#### API Health Check
```bash
# Test API health endpoint
curl https://api.yourdomain.com/health

# Test authentication endpoint
curl -X POST https://api.yourdomain.com/api/auth/sms/request \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'
```

#### Database Connectivity
```bash
# Test database connection
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
db = next(get_db())
result = db.execute('SELECT version();')
print('Database connection successful:', result.fetchone()[0])
"
```

#### Cache Connectivity
```bash
# Test Redis connection
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import redis
import os
r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_AUTH_TOKEN'),
    ssl=True
)
r.ping()
print('Redis connection successful')
"
```

### 2. **Security Validation**

#### Security Scan
```bash
# Run security scan
kubectl run security-scan \
  --image=aquasec/trivy:latest \
  --rm -it --restart=Never \
  -- image medinovai/backend:1.0.0

# Check for vulnerabilities
kubectl run cve-scan \
  --image=clair/clair:latest \
  --rm -it --restart=Never \
  -- analyze medinovai/backend:1.0.0
```

#### Compliance Check
```bash
# Run compliance check
kubectl run compliance-check \
  --image=docker.io/cis/kubernetes-benchmark:latest \
  --rm -it --restart=Never

# Check HIPAA compliance
kubectl run hipaa-check \
  --image=your-registry/hipaa-compliance-checker:latest \
  --rm -it --restart=Never
```

---

## Phase 9: Performance Testing

### 1. **Load Testing**

#### API Load Test
```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.46.0/k6-v0.46.0-linux-amd64.tar.gz -L | tar xvz --strip-components 1

# Create load test script
cat > load-test.js << EOF
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '5m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  let response = http.get('https://api.yourdomain.com/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
EOF

# Run load test
./k6 run load-test.js
```

### 2. **Database Performance**

```bash
# Run database performance test
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
import time
from src.utils.database import get_db

db = next(get_db())
start_time = time.time()

for i in range(1000):
    db.execute('SELECT 1;')

end_time = time.time()
print(f'1000 queries completed in {end_time - start_time:.2f} seconds')
"
```

---

## Phase 10: Backup and Recovery Setup

### 1. **Database Backup Configuration**

#### Configure Automated Backups
```bash
# Verify RDS backup configuration
aws rds describe-db-instances \
  --db-instance-identifier medinovai-prod-db \
  --query 'DBInstances[0].{BackupRetentionPeriod:BackupRetentionPeriod,BackupWindow:PreferredBackupWindow}'

# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier medinovai-prod-db \
  --db-snapshot-identifier medinovai-prod-initial-snapshot
```

### 2. **Application Data Backup**

#### Configure Velero for Kubernetes Backups
```bash
# Install Velero
curl -fsSL -o velero-v1.12.0-linux-amd64.tar.gz https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin

# Create S3 bucket for backups
aws s3 mb s3://medinovai-backups-${AWS_ACCOUNT_ID} --region $AWS_REGION

# Install Velero
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket medinovai-backups-${AWS_ACCOUNT_ID} \
  --backup-location-config region=$AWS_REGION \
  --snapshot-location-config region=$AWS_REGION

# Create backup schedule
velero schedule create medinovai-daily \
  --schedule="0 2 * * *" \
  --include-namespaces medinovai

# Test backup
velero backup create medinovai-initial --include-namespaces medinovai
```

---

## Phase 11: Final Validation and Go-Live

### 1. **Pre-Go-Live Checklist**

#### Security Checklist
- [ ] SSL certificates installed and validated
- [ ] WAF rules configured and tested
- [ ] Security groups properly configured
- [ ] All data encrypted at rest and in transit
- [ ] Access controls and RBAC implemented
- [ ] Audit logging enabled and functioning
- [ ] Vulnerability scanning completed

#### Compliance Checklist
- [ ] HIPAA risk assessment completed
- [ ] Business Associate Agreements signed
- [ ] Staff HIPAA training completed
- [ ] Incident response procedures documented
- [ ] Data backup and recovery tested
- [ ] Audit logs retention configured (7 years)

#### Performance Checklist
- [ ] Load testing completed successfully
- [ ] Database performance optimized
- [ ] Monitoring and alerting configured
- [ ] Auto-scaling configured and tested
- [ ] CDN configured for static assets
- [ ] Performance benchmarks met

#### Operational Checklist
- [ ] DNS records configured and propagated
- [ ] Admin users created and tested
- [ ] Database migrations completed
- [ ] Initial data loaded successfully
- [ ] Backup and recovery procedures tested
- [ ] Documentation updated and accessible

### 2. **Go-Live Procedure**

#### Final Deployment
```bash
# Final deployment verification
kubectl get pods -n medinovai
kubectl get services -n medinovai
kubectl get ingress -n medinovai

# Check all services are healthy
kubectl get pods -n medinovai -o wide

# Verify external access
curl -I https://api.yourdomain.com/health
curl -I https://admin.yourdomain.com

# Check database connectivity
kubectl exec -it deployment/medinovai-backend -n medinovai -- python -c "
from src.utils.database import get_db
print('Database connection:', 'OK' if next(get_db()) else 'FAILED')
"
```

#### Post-Go-Live Monitoring
```bash
# Monitor application logs
kubectl logs -f deployment/medinovai-backend -n medinovai

# Monitor resource usage
kubectl top pods -n medinovai
kubectl top nodes

# Check metrics in Grafana
echo "Access Grafana at: http://$(kubectl get svc prometheus-grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
```

---

## Maintenance and Operations

### 1. **Regular Maintenance Tasks**

#### Daily Tasks
- Monitor system health and performance
- Review security alerts and logs
- Check backup completion status
- Monitor database performance

#### Weekly Tasks
- Review and analyze usage metrics
- Update security patches if available
- Test backup and recovery procedures
- Review compliance audit logs

#### Monthly Tasks
- Perform security vulnerability scans
- Review and update documentation
- Conduct disaster recovery drills
- Review and optimize costs

### 2. **Troubleshooting Common Issues**

#### Application Issues
```bash
# Check pod status
kubectl describe pod <pod-name> -n medinovai

# View application logs
kubectl logs <pod-name> -n medinovai --previous

# Check resource usage
kubectl top pod <pod-name> -n medinovai
```

#### Database Issues
```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier medinovai-prod-db

# Monitor database connections
aws rds describe-db-log-files --db-instance-identifier medinovai-prod-db

# Check slow queries
aws logs filter-log-events \
  --log-group-name /aws/rds/instance/medinovai-prod-db/postgresql \
  --filter-pattern "duration"
```

---

## Support and Documentation

### 1. **Emergency Contacts**

- **Technical Support**: tech-support@myonsitehealthcare.com
- **Security Issues**: security@myonsitehealthcare.com
- **Emergency Hotline**: +1-XXX-XXX-XXXX (24/7)

### 2. **Additional Resources**

- **Runbook**: [Operations Runbook](../troubleshooting/operations-runbook.md)
- **Security Procedures**: [Security Incident Response](../compliance/incident-response.md)
- **API Documentation**: [API Reference](../api/)
- **Monitoring**: [Monitoring Guide](../deployment/monitoring.md)

---

## Conclusion

Your MedinovAI Chatbot system is now successfully deployed and ready for production use. The system includes:

✅ **Complete AWS infrastructure** with HIPAA compliance  
✅ **Kubernetes cluster** with auto-scaling and monitoring  
✅ **Secure database and caching** with encryption  
✅ **Application deployment** with health checks  
✅ **Monitoring and alerting** with Prometheus and Grafana  
✅ **Backup and recovery** procedures  
✅ **Security controls** and compliance measures  

Remember to follow the maintenance procedures and keep all components updated for optimal security and performance.

For any issues or questions, refer to the troubleshooting documentation or contact our support team. 