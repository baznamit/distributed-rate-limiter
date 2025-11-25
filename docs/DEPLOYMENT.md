# 🚀 Production Deployment Guide

## Overview

This guide covers deploying the distributed rate limiter to production environments with high availability, scalability, and monitoring.

## Quick Start

### One-Command Docker Deployment
```bash
# Clone and deploy
git clone https://github.com/yourusername/distributed-rate-limiter
cd distributed-rate-limiter
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
curl http://localhost:8000/health
```

## Deployment Options

### 1. Docker Compose (Recommended for Small-Medium Scale)

#### Production Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  redis-cluster:
    image: redis:7-alpine
    deploy:
      replicas: 3
    configs:
      - redis.conf
    volumes:
      - redis_data:/data
    networks:
      - rate-limiter-net

  rate-limiter:
    image: ghcr.io/yourusername/rate-limiter:latest
    deploy:
      replicas: 4
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.5"
    environment:
      - REDIS_HOST=redis-cluster
      - WORKER_PROCESSES=4
      - LOG_LEVEL=INFO
    networks:
      - rate-limiter-net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80" 
      - "443:443"
    configs:
      - nginx.conf
    depends_on:
      - rate-limiter
    networks:
      - rate-limiter-net

networks:
  rate-limiter-net:
    driver: overlay
    attachable: true

volumes:
  redis_data:
```

#### Deployment Commands
```bash
# Initialize Docker Swarm (if not already done)
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml rate-limiter

# Scale services
docker service scale rate-limiter_rate-limiter=6

# Check status
docker service ls
docker service logs rate-limiter_rate-limiter
```

### 2. Kubernetes (Enterprise Scale)

#### Namespace Setup
```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rate-limiter
  labels:
    name: rate-limiter
```

#### Redis Cluster
```yaml
# kubernetes/redis-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
  namespace: rate-limiter
spec:
  replicas: 6
  serviceName: redis-cluster
  template:
    metadata:
      labels:
        app: redis-cluster
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        - containerPort: 16379
        command:
          - redis-server
          - /etc/redis/redis.conf
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

#### Rate Limiter Deployment
```yaml
# kubernetes/rate-limiter-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rate-limiter
  namespace: rate-limiter
spec:
  replicas: 6
  selector:
    matchLabels:
      app: rate-limiter
  template:
    metadata:
      labels:
        app: rate-limiter
    spec:
      containers:
      - name: rate-limiter
        image: ghcr.io/yourusername/rate-limiter:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-cluster"
        - name: REDIS_PORT
          value: "6379"
        - name: WORKER_PROCESSES
          value: "4"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Horizontal Pod Autoscaler
```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rate-limiter-hpa
  namespace: rate-limiter
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rate-limiter
  minReplicas: 3
  maxReplicas: 20
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
```

#### Ingress Configuration
```yaml
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rate-limiter-ingress
  namespace: rate-limiter
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.yourcompany.com
    secretName: rate-limiter-tls
  rules:
  - host: api.yourcompany.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rate-limiter-service
            port:
              number: 80
```

#### Deployment Commands
```bash
# Apply all Kubernetes manifests
kubectl apply -f kubernetes/

# Check deployment status
kubectl get pods -n rate-limiter
kubectl get services -n rate-limiter

# Scale deployment
kubectl scale deployment rate-limiter --replicas=10 -n rate-limiter

# Check logs
kubectl logs -f deployment/rate-limiter -n rate-limiter
```

### 3. Cloud Platform Deployments

#### AWS ECS with Fargate
```json
{
  "family": "rate-limiter-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "rate-limiter",
      "image": "ghcr.io/yourusername/rate-limiter:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "REDIS_HOST",
          "value": "rate-limiter-cache.abc123.cache.amazonaws.com"
        },
        {
          "name": "WORKER_PROCESSES",
          "value": "4"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rate-limiter",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

```bash
# Deploy to ECS
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service \
  --cluster rate-limiter-cluster \
  --service-name rate-limiter-service \
  --task-definition rate-limiter-task:1 \
  --desired-count 4 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-abcdef],assignPublicIp=ENABLED}"
```

#### Google Cloud Run
```yaml
# cloud-run.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: rate-limiter
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "100"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 80
      containers:
      - image: gcr.io/PROJECT-ID/rate-limiter:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "10.0.0.1"  # Redis Memorystore IP
        resources:
          limits:
            cpu: "2"
            memory: "1Gi"
```

```bash
# Deploy to Cloud Run
gcloud run deploy rate-limiter \
  --image gcr.io/PROJECT-ID/rate-limiter:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --max-instances 100 \
  --memory 1Gi \
  --cpu 2
```

## Environment Configuration

### Production Environment Variables
```bash
# Core Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_HOST=0.0.0.0
APP_PORT=8000

# Redis Configuration (High Availability)
REDIS_HOST=redis-cluster.internal.company.com
REDIS_PORT=6379
REDIS_PASSWORD=secure-redis-password-here
REDIS_DB=0
REDIS_CONNECTION_POOL_SIZE=50
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_KEEPALIVE=true
REDIS_SOCKET_KEEPALIVE_OPTIONS=1,3,5

# Rate Limiting Settings
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=20
SLIDING_WINDOW_SIZE=300
ENABLE_IP_WHITELIST=true

# Security Configuration
SECRET_KEY=your-256-bit-secret-key-here
ALLOWED_HOSTS=api.yourcompany.com,internal-api.company.com
CORS_ORIGINS=https://dashboard.yourcompany.com,https://app.yourcompany.com
API_KEY_REQUIRED=true

# Performance Tuning
WORKER_PROCESSES=4
MAX_REQUESTS_PER_WORKER=1000
KEEP_ALIVE_TIMEOUT=65
CLIENT_MAX_SIZE=1048576

# Monitoring and Observability
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
METRICS_PATH=/metrics
HEALTH_CHECK_INTERVAL=30
ENABLE_REQUEST_LOGGING=true

# External Services
DATABASE_URL=postgresql://user:pass@db.company.com:5432/rate_limiter
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### SSL/TLS Configuration
```nginx
# nginx.conf for SSL termination
server {
    listen 443 ssl http2;
    server_name api.yourcompany.com;
    
    ssl_certificate /etc/ssl/certs/api.yourcompany.com.crt;
    ssl_certificate_key /etc/ssl/private/api.yourcompany.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    location / {
        proxy_pass http://rate-limiter:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## High Availability Setup

### Redis Clustering
```bash
# Redis Cluster setup (6 nodes: 3 masters + 3 replicas)
redis-cli --cluster create \
  redis-1:6379 redis-2:6379 redis-3:6379 \
  redis-4:6379 redis-5:6379 redis-6:6379 \
  --cluster-replicas 1
```

### Load Balancer Configuration
```yaml
# HAProxy configuration
global
    daemon
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend rate_limiter_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/api.yourcompany.com.pem
    redirect scheme https if !{ ssl_fc }
    default_backend rate_limiter_backend

backend rate_limiter_backend
    balance roundrobin
    option httpchk GET /health
    server api1 rate-limiter-1:8000 check
    server api2 rate-limiter-2:8000 check
    server api3 rate-limiter-3:8000 check
    server api4 rate-limiter-4:8000 check
```

## Monitoring and Observability

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rate-limiter'
    static_configs:
      - targets: ['rate-limiter:9090']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Rate Limiter Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Rate Limit Violations", 
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(rate_limit_violations_total[5m]))",
            "legendFormat": "Violations/sec"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules
```yaml
# alerts.yml
groups:
- name: rate-limiter
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      
  - alert: RedisDown
    expr: redis_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Redis instance is down"
```

## Backup and Disaster Recovery

### Redis Backup Strategy
```bash
# Automated Redis backup script
#!/bin/bash
BACKUP_DIR="/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
redis-cli --rdb ${BACKUP_DIR}/redis_backup_${DATE}.rdb

# Upload to S3 (or your cloud storage)
aws s3 cp ${BACKUP_DIR}/redis_backup_${DATE}.rdb s3://your-backup-bucket/redis/

# Cleanup old backups (keep last 7 days)
find ${BACKUP_DIR} -name "*.rdb" -mtime +7 -delete
```

### Application State Recovery
```bash
# Restore from backup
#!/bin/bash
BACKUP_FILE=$1

# Stop application
kubectl scale deployment rate-limiter --replicas=0

# Restore Redis data
redis-cli --rdb ${BACKUP_FILE}

# Restart application  
kubectl scale deployment rate-limiter --replicas=4

# Verify health
kubectl rollout status deployment/rate-limiter
```

## Security Hardening

### Network Security
```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rate-limiter-netpol
spec:
  podSelector:
    matchLabels:
      app: rate-limiter
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: redis
    ports:
    - protocol: TCP
      port: 6379
```

### Container Security
```dockerfile
# Security-hardened Dockerfile
FROM python:3.9-slim as builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.9-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] DNS records configured
- [ ] Load balancer setup complete
- [ ] Monitoring stack deployed
- [ ] Backup procedures tested

### During Deployment  
- [ ] Blue-green deployment strategy
- [ ] Health checks passing
- [ ] Canary traffic routing (1% → 10% → 50% → 100%)
- [ ] Performance monitoring active
- [ ] Error rate monitoring

### Post-Deployment
- [ ] End-to-end testing completed
- [ ] Performance benchmarks verified
- [ ] Alerting rules firing correctly
- [ ] Documentation updated
- [ ] Team notification sent

This comprehensive deployment guide ensures your rate limiter runs reliably in production! 🚀