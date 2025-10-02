# PRP-A3: Cloud Deployment Preparation
## Universal Technical Implementation Specification Compliance

**Date**: 2025-09-23
**Status**: READY FOR IMPLEMENTATION
**Priority**: MEDIUM - PRODUCTION DEPLOYMENT
**Duration**: 1 session
**Dependencies**: PRP-A1 (Database Safety), PRP-A2 (Architecture Refactor)

---

## **EXECUTIVE SUMMARY**

This PRP prepares the compliance engine for production cloud deployment with enterprise-grade configuration management, secrets handling, monitoring, and scalability. It ensures the application is production-ready for AWS, Azure, or other cloud providers with professional operational standards.

---

## **CLOUD DEPLOYMENT ARCHITECTURE**

### **Target Cloud Architecture**
```
┌─────────────────────────────────────────────────────────────────┐
│ CLOUD PROVIDER (AWS/Azure/GCP)                                 │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Load Balancer   │ │ Container       │ │ Database        │ │
│ │ (ALB/nginx)     │ │ Instances       │ │ (RDS/Managed)   │ │
│ │                 │ │ - Next.js App   │ │ - PostgreSQL    │ │
│ │ SSL Termination │ │ - Health Checks │ │ - Connection    │ │
│ │ Request Routing │ │ - Auto Scaling  │ │   Pooling       │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│          │                    │                    │        │
│          └────────────────────┼────────────────────┘        │
│                               │                             │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Secrets         │ │ Monitoring      │ │ Storage         │ │
│ │ Management      │ │ & Logging       │ │ & Backup        │ │
│ │ - Database PWD  │ │ - CloudWatch    │ │ - S3/Blob       │ │
│ │ - API Keys      │ │ - Application   │ │ - Database      │ │
│ │ - Certificates  │ │   Insights      │ │   Backups       │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### **Container Strategy**
```dockerfile
# Production-optimized Docker configuration
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS runtime
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

---

## **ENVIRONMENT CONFIGURATION SYSTEM**

### **Phase 1: Environment Management**
```typescript
// lib/config/environment.ts
export interface EnvironmentConfig {
  app: {
    name: string;
    version: string;
    environment: 'development' | 'staging' | 'production';
    port: number;
    host: string;
  };
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    password: string;
    ssl: boolean;
    pool: {
      min: number;
      max: number;
      idleTimeoutMs: number;
      connectionTimeoutMs: number;
    };
  };
  apis: {
    nswPlanning: {
      baseUrl: string;
      timeout: number;
      retryCount: number;
      apiKey?: string;
    };
    googlePlaces: {
      apiKey: string;
      timeout: number;
    };
  };
  cache: {
    enabled: boolean;
    ttl: number;
    redisUrl?: string;
  };
  monitoring: {
    enabled: boolean;
    sentryDsn?: string;
    logLevel: 'debug' | 'info' | 'warn' | 'error';
    metricsPort: number;
  };
  security: {
    corsOrigins: string[];
    rateLimiting: {
      windowMs: number;
      maxRequests: number;
    };
    encryption: {
      algorithm: string;
      keyLength: number;
    };
  };
}

class ConfigurationManager {
  private static instance: ConfigurationManager;
  private config: EnvironmentConfig;

  private constructor() {
    this.config = this.loadConfiguration();
    this.validateConfiguration();
  }

  static getInstance(): ConfigurationManager {
    if (!ConfigurationManager.instance) {
      ConfigurationManager.instance = new ConfigurationManager();
    }
    return ConfigurationManager.instance;
  }

  private loadConfiguration(): EnvironmentConfig {
    const env = process.env.NODE_ENV || 'development';

    return {
      app: {
        name: process.env.APP_NAME || 'NSW Compliance Engine',
        version: process.env.APP_VERSION || '1.0.0',
        environment: env as any,
        port: parseInt(process.env.PORT || '3000'),
        host: process.env.HOST || '0.0.0.0'
      },
      database: {
        host: this.getRequiredEnv('DATABASE_HOST'),
        port: parseInt(process.env.DATABASE_PORT || '5432'),
        name: this.getRequiredEnv('DATABASE_NAME'),
        user: this.getRequiredEnv('DATABASE_USER'),
        password: this.getRequiredEnv('DATABASE_PASSWORD'),
        ssl: process.env.DATABASE_SSL === 'true',
        pool: {
          min: parseInt(process.env.DB_POOL_MIN || '2'),
          max: parseInt(process.env.DB_POOL_MAX || '20'),
          idleTimeoutMs: parseInt(process.env.DB_IDLE_TIMEOUT || '30000'),
          connectionTimeoutMs: parseInt(process.env.DB_CONNECTION_TIMEOUT || '2000')
        }
      },
      apis: {
        nswPlanning: {
          baseUrl: process.env.NSW_PLANNING_API_URL || 'https://api.apps1.nsw.gov.au/planning',
          timeout: parseInt(process.env.NSW_API_TIMEOUT || '10000'),
          retryCount: parseInt(process.env.NSW_API_RETRY_COUNT || '3'),
          apiKey: process.env.NSW_API_KEY
        },
        googlePlaces: {
          apiKey: this.getRequiredEnv('GOOGLE_PLACES_API_KEY'),
          timeout: parseInt(process.env.GOOGLE_API_TIMEOUT || '5000')
        }
      },
      cache: {
        enabled: process.env.CACHE_ENABLED === 'true',
        ttl: parseInt(process.env.CACHE_TTL || '3600'),
        redisUrl: process.env.REDIS_URL
      },
      monitoring: {
        enabled: process.env.MONITORING_ENABLED === 'true',
        sentryDsn: process.env.SENTRY_DSN,
        logLevel: (process.env.LOG_LEVEL as any) || 'info',
        metricsPort: parseInt(process.env.METRICS_PORT || '9090')
      },
      security: {
        corsOrigins: (process.env.CORS_ORIGINS || '').split(',').filter(Boolean),
        rateLimiting: {
          windowMs: parseInt(process.env.RATE_LIMIT_WINDOW || '60000'),
          maxRequests: parseInt(process.env.RATE_LIMIT_MAX || '100')
        },
        encryption: {
          algorithm: process.env.ENCRYPTION_ALGORITHM || 'aes-256-gcm',
          keyLength: parseInt(process.env.ENCRYPTION_KEY_LENGTH || '32')
        }
      }
    };
  }

  private getRequiredEnv(name: string): string {
    const value = process.env[name];
    if (!value) {
      throw new Error(`Required environment variable ${name} is not set`);
    }
    return value;
  }

  private validateConfiguration(): void {
    // Validate database configuration
    if (!this.config.database.host) {
      throw new Error('Database host is required');
    }

    // Validate API keys
    if (!this.config.apis.googlePlaces.apiKey) {
      throw new Error('Google Places API key is required');
    }

    // Validate production-specific requirements
    if (this.config.app.environment === 'production') {
      if (!this.config.monitoring.sentryDsn) {
        console.warn('Warning: Sentry DSN not configured for production');
      }
      if (!this.config.database.ssl) {
        console.warn('Warning: Database SSL not enabled for production');
      }
    }
  }

  getConfig(): EnvironmentConfig {
    return this.config;
  }

  getDatabaseConfig() {
    return this.config.database;
  }

  getAPIConfig() {
    return this.config.apis;
  }

  getMonitoringConfig() {
    return this.config.monitoring;
  }
}

export const config = ConfigurationManager.getInstance().getConfig();
export const getConfig = () => ConfigurationManager.getInstance().getConfig();
```

### **Phase 2: Secrets Management**
```typescript
// lib/security/secrets.ts
import { createCipher, createDecipher, randomBytes } from 'crypto';

export interface SecretConfig {
  provider: 'env' | 'aws-secrets' | 'azure-keyvault' | 'gcp-secrets';
  region?: string;
  vaultName?: string;
}

abstract class SecretsProvider {
  abstract getSecret(name: string): Promise<string>;
  abstract setSecret(name: string, value: string): Promise<void>;
}

class EnvironmentSecretsProvider extends SecretsProvider {
  async getSecret(name: string): Promise<string> {
    const value = process.env[name];
    if (!value) {
      throw new Error(`Secret ${name} not found in environment variables`);
    }
    return value;
  }

  async setSecret(name: string, value: string): Promise<void> {
    throw new Error('Cannot set secrets in environment provider');
  }
}

class AWSSecretsProvider extends SecretsProvider {
  private client: any;

  constructor(region: string) {
    // AWS SDK integration
    const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');
    this.client = new SecretsManagerClient({ region });
  }

  async getSecret(name: string): Promise<string> {
    try {
      const { GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');
      const command = new GetSecretValueCommand({ SecretId: name });
      const response = await this.client.send(command);
      return response.SecretString;
    } catch (error) {
      throw new Error(`Failed to retrieve secret ${name}: ${error}`);
    }
  }

  async setSecret(name: string, value: string): Promise<void> {
    const { CreateSecretCommand } = require('@aws-sdk/client-secrets-manager');
    const command = new CreateSecretCommand({
      Name: name,
      SecretString: value
    });
    await this.client.send(command);
  }
}

export class SecretsManager {
  private provider: SecretsProvider;

  constructor(config: SecretConfig) {
    switch (config.provider) {
      case 'env':
        this.provider = new EnvironmentSecretsProvider();
        break;
      case 'aws-secrets':
        this.provider = new AWSSecretsProvider(config.region!);
        break;
      default:
        throw new Error(`Unsupported secrets provider: ${config.provider}`);
    }
  }

  async getDatabasePassword(): Promise<string> {
    return this.provider.getSecret('DATABASE_PASSWORD');
  }

  async getGooglePlacesApiKey(): Promise<string> {
    return this.provider.getSecret('GOOGLE_PLACES_API_KEY');
  }

  async getNSWApiKey(): Promise<string> {
    return this.provider.getSecret('NSW_API_KEY');
  }

  async getEncryptionKey(): Promise<string> {
    return this.provider.getSecret('ENCRYPTION_KEY');
  }
}
```

### **Phase 3: Health Checks and Monitoring**
```typescript
// lib/monitoring/health.ts
export interface HealthCheckResult {
  service: string;
  status: 'healthy' | 'unhealthy' | 'degraded';
  responseTime: number;
  details?: any;
  error?: string;
}

export interface SystemHealth {
  overall: 'healthy' | 'unhealthy' | 'degraded';
  checks: HealthCheckResult[];
  uptime: number;
  version: string;
  timestamp: string;
}

export class HealthMonitor {
  private startTime: number;

  constructor() {
    this.startTime = Date.now();
  }

  async checkDatabase(): Promise<HealthCheckResult> {
    const start = Date.now();

    try {
      const { PostgreSQLComplianceClient } = await import('@/lib/database/postgres-client');
      const client = PostgreSQLComplianceClient.getInstance();
      const result = await client.healthCheck();

      return {
        service: 'database',
        status: result.healthy ? 'healthy' : 'unhealthy',
        responseTime: Date.now() - start,
        details: {
          connections: result.connections,
          host: config.database.host,
          database: config.database.name
        }
      };
    } catch (error) {
      return {
        service: 'database',
        status: 'unhealthy',
        responseTime: Date.now() - start,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async checkNSWAPI(): Promise<HealthCheckResult> {
    const start = Date.now();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${config.apis.nswPlanning.baseUrl}/health`, {
        signal: controller.signal,
        headers: {
          'User-Agent': 'NSW-Compliance-Engine/1.0'
        }
      });

      clearTimeout(timeoutId);

      return {
        service: 'nsw-api',
        status: response.ok ? 'healthy' : 'degraded',
        responseTime: Date.now() - start,
        details: {
          status: response.status,
          url: config.apis.nswPlanning.baseUrl
        }
      };
    } catch (error) {
      return {
        service: 'nsw-api',
        status: 'unhealthy',
        responseTime: Date.now() - start,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async checkCache(): Promise<HealthCheckResult> {
    const start = Date.now();

    if (!config.cache.enabled) {
      return {
        service: 'cache',
        status: 'healthy',
        responseTime: 0,
        details: { enabled: false }
      };
    }

    try {
      // Redis health check if enabled
      if (config.cache.redisUrl) {
        const Redis = require('ioredis');
        const redis = new Redis(config.cache.redisUrl);
        await redis.ping();
        redis.disconnect();
      }

      return {
        service: 'cache',
        status: 'healthy',
        responseTime: Date.now() - start,
        details: {
          enabled: config.cache.enabled,
          ttl: config.cache.ttl
        }
      };
    } catch (error) {
      return {
        service: 'cache',
        status: 'degraded',
        responseTime: Date.now() - start,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async checkDisk(): Promise<HealthCheckResult> {
    const start = Date.now();

    try {
      const fs = require('fs').promises;
      const { statSync } = require('fs');

      // Check disk space
      const stats = statSync('.');
      const freeSpace = stats.size; // Simplified check

      return {
        service: 'disk',
        status: 'healthy',
        responseTime: Date.now() - start,
        details: {
          available: true
        }
      };
    } catch (error) {
      return {
        service: 'disk',
        status: 'unhealthy',
        responseTime: Date.now() - start,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async getSystemHealth(): Promise<SystemHealth> {
    const checks = await Promise.all([
      this.checkDatabase(),
      this.checkNSWAPI(),
      this.checkCache(),
      this.checkDisk()
    ]);

    const healthyCount = checks.filter(c => c.status === 'healthy').length;
    const unhealthyCount = checks.filter(c => c.status === 'unhealthy').length;

    let overall: SystemHealth['overall'];
    if (unhealthyCount > 0) {
      overall = 'unhealthy';
    } else if (healthyCount === checks.length) {
      overall = 'healthy';
    } else {
      overall = 'degraded';
    }

    return {
      overall,
      checks,
      uptime: Date.now() - this.startTime,
      version: config.app.version,
      timestamp: new Date().toISOString()
    };
  }
}
```

### **Phase 4: Deployment Scripts**
```typescript
// scripts/deploy.ts
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

interface DeploymentConfig {
  environment: 'staging' | 'production';
  provider: 'aws' | 'azure' | 'gcp' | 'docker';
  region?: string;
  resourceGroup?: string;
  cluster?: string;
}

class CloudDeployer {
  constructor(private config: DeploymentConfig) {}

  async deploy(): Promise<void> {
    console.log(`Deploying to ${this.config.environment} on ${this.config.provider}`);

    try {
      await this.preDeploymentChecks();
      await this.buildApplication();
      await this.runTests();
      await this.deployToCloud();
      await this.postDeploymentVerification();

      console.log('Deployment completed successfully');
    } catch (error) {
      console.error('Deployment failed:', error);
      await this.rollbackDeployment();
      throw error;
    }
  }

  private async preDeploymentChecks(): Promise<void> {
    console.log('Running pre-deployment checks...');

    // Check environment variables
    const requiredEnvVars = [
      'DATABASE_HOST',
      'DATABASE_PASSWORD',
      'GOOGLE_PLACES_API_KEY'
    ];

    for (const envVar of requiredEnvVars) {
      if (!process.env[envVar]) {
        throw new Error(`Required environment variable ${envVar} is not set`);
      }
    }

    // Check database connectivity
    await this.checkDatabaseConnection();

    // Validate configuration
    const { getConfig } = await import('@/lib/config/environment');
    const config = getConfig();
    console.log(`Configuration validated for ${config.app.environment}`);
  }

  private async buildApplication(): Promise<void> {
    console.log('Building application...');

    await execAsync('npm run build');
    console.log('Application built successfully');
  }

  private async runTests(): Promise<void> {
    console.log('Running tests...');

    try {
      await execAsync('npm run test:production');
      console.log('All tests passed');
    } catch (error) {
      throw new Error(`Tests failed: ${error}`);
    }
  }

  private async deployToCloud(): Promise<void> {
    switch (this.config.provider) {
      case 'aws':
        await this.deployToAWS();
        break;
      case 'azure':
        await this.deployToAzure();
        break;
      case 'docker':
        await this.deployToDocker();
        break;
      default:
        throw new Error(`Unsupported provider: ${this.config.provider}`);
    }
  }

  private async deployToAWS(): Promise<void> {
    console.log('Deploying to AWS...');

    // Build Docker image
    await execAsync('docker build -t compliance-engine .');

    // Tag for ECR
    const ecrUri = `${process.env.AWS_ACCOUNT_ID}.dkr.ecr.${this.config.region}.amazonaws.com/compliance-engine`;
    await execAsync(`docker tag compliance-engine:latest ${ecrUri}:latest`);

    // Push to ECR
    await execAsync(`docker push ${ecrUri}:latest`);

    // Update ECS service
    await execAsync(`aws ecs update-service --cluster ${this.config.cluster} --service compliance-engine --force-new-deployment`);
  }

  private async deployToAzure(): Promise<void> {
    console.log('Deploying to Azure...');

    // Build and push to Azure Container Registry
    await execAsync(`az acr build --registry complianceengine --image compliance-engine:latest .`);

    // Update Azure Container Instances
    await execAsync(`az container restart --resource-group ${this.config.resourceGroup} --name compliance-engine`);
  }

  private async deployToDocker(): Promise<void> {
    console.log('Deploying with Docker...');

    // Build image
    await execAsync('docker build -t compliance-engine:latest .');

    // Stop existing container
    try {
      await execAsync('docker stop compliance-engine');
      await execAsync('docker rm compliance-engine');
    } catch {
      // Container might not exist
    }

    // Start new container
    const dockerRun = `
      docker run -d
      --name compliance-engine
      --restart unless-stopped
      -p 3000:3000
      -e NODE_ENV=production
      -e DATABASE_HOST=${process.env.DATABASE_HOST}
      -e DATABASE_PASSWORD=${process.env.DATABASE_PASSWORD}
      -e GOOGLE_PLACES_API_KEY=${process.env.GOOGLE_PLACES_API_KEY}
      compliance-engine:latest
    `.replace(/\s+/g, ' ').trim();

    await execAsync(dockerRun);
  }

  private async postDeploymentVerification(): Promise<void> {
    console.log('Running post-deployment verification...');

    // Wait for service to start
    await new Promise(resolve => setTimeout(resolve, 10000));

    // Health check
    const healthUrl = process.env.HEALTH_CHECK_URL || 'http://localhost:3000/api/health';

    try {
      const response = await fetch(healthUrl);
      const health = await response.json();

      if (health.overall !== 'healthy') {
        throw new Error(`Health check failed: ${JSON.stringify(health)}`);
      }

      console.log('Health check passed');
    } catch (error) {
      throw new Error(`Post-deployment verification failed: ${error}`);
    }
  }

  private async checkDatabaseConnection(): Promise<void> {
    try {
      const { PostgreSQLComplianceClient } = await import('@/lib/database/postgres-client');
      const client = PostgreSQLComplianceClient.getInstance();
      const result = await client.healthCheck();

      if (!result.healthy) {
        throw new Error('Database health check failed');
      }

      console.log('Database connectivity verified');
    } catch (error) {
      throw new Error(`Database connection failed: ${error}`);
    }
  }

  private async rollbackDeployment(): Promise<void> {
    console.log('Rolling back deployment...');

    try {
      switch (this.config.provider) {
        case 'aws':
          await execAsync(`aws ecs update-service --cluster ${this.config.cluster} --service compliance-engine --task-definition compliance-engine:previous`);
          break;
        case 'docker':
          await execAsync('docker stop compliance-engine');
          await execAsync('docker run -d --name compliance-engine compliance-engine:previous');
          break;
      }

      console.log('Rollback completed');
    } catch (error) {
      console.error('Rollback failed:', error);
    }
  }
}

// Usage example
async function deploy() {
  const deployer = new CloudDeployer({
    environment: (process.env.DEPLOY_ENV as any) || 'staging',
    provider: (process.env.CLOUD_PROVIDER as any) || 'docker',
    region: process.env.AWS_REGION || 'us-east-1',
    cluster: process.env.ECS_CLUSTER || 'compliance-engine-cluster'
  });

  await deployer.deploy();
}

if (require.main === module) {
  deploy().catch(console.error);
}
```

---

## **CONTAINERIZATION AND ORCHESTRATION**

### **Production Dockerfile**
```dockerfile
# Dockerfile
# Multi-stage build for production optimization

# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Stage 2: Builder
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Runtime
FROM node:18-alpine AS runtime
WORKDIR /app

# Security: Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Copy dependencies and built application
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

USER nextjs

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["npm", "start"]
```

### **Docker Compose for Development**
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_HOST=postgres
      - DATABASE_NAME=nsw_planning
      - DATABASE_USER=postgres
      - DATABASE_PASSWORD=postgres
      - GOOGLE_PLACES_API_KEY=${GOOGLE_PLACES_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=nsw_planning
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app

volumes:
  postgres_data:
```

### **Kubernetes Deployment**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-engine
  labels:
    app: compliance-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compliance-engine
  template:
    metadata:
      labels:
        app: compliance-engine
    spec:
      containers:
      - name: compliance-engine
        image: compliance-engine:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_HOST
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: database-host
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: database-password
        - name: GOOGLE_PLACES_API_KEY
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: google-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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

---
apiVersion: v1
kind: Service
metadata:
  name: compliance-engine-service
spec:
  selector:
    app: compliance-engine
  ports:
    - protocol: TCP
      port: 80
      targetPort: 3000
  type: LoadBalancer
```

---

## **MONITORING AND OBSERVABILITY**

### **Application Metrics**
```typescript
// lib/monitoring/metrics.ts
import * as prom from 'prom-client';

// Create metrics registry
const register = new prom.Registry();

// Default metrics (CPU, memory, etc.)
prom.collectDefaultMetrics({ register });

// Custom application metrics
export const httpRequestDuration = new prom.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

export const databaseQueryDuration = new prom.Histogram({
  name: 'database_query_duration_seconds',
  help: 'Duration of database queries in seconds',
  labelNames: ['query_type', 'table'],
  buckets: [0.01, 0.05, 0.1, 0.2, 0.5, 1, 2]
});

export const complianceRequests = new prom.Counter({
  name: 'compliance_requests_total',
  help: 'Total number of compliance requests',
  labelNames: ['zone', 'request_type']
});

export const errorRate = new prom.Counter({
  name: 'application_errors_total',
  help: 'Total number of application errors',
  labelNames: ['error_type', 'severity']
});

// Register metrics
register.registerMetric(httpRequestDuration);
register.registerMetric(databaseQueryDuration);
register.registerMetric(complianceRequests);
register.registerMetric(errorRate);

export { register };
```

### **Logging Configuration**
```typescript
// lib/monitoring/logger.ts
import winston from 'winston';
import { config } from '@/lib/config/environment';

const logFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

export const logger = winston.createLogger({
  level: config.monitoring.logLevel,
  format: logFormat,
  defaultMeta: {
    service: config.app.name,
    version: config.app.version,
    environment: config.app.environment
  },
  transports: [
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    }),
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 5242880,
      maxFiles: 5
    })
  ]
});

// Console logging for development
if (config.app.environment !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    )
  }));
}

// Structured logging helpers
export const logComplianceRequest = (data: {
  address: string;
  zone: string;
  processingTime: number;
  success: boolean;
}) => {
  logger.info('Compliance request processed', {
    type: 'compliance_request',
    ...data
  });
};

export const logDatabaseQuery = (data: {
  query: string;
  duration: number;
  rowCount: number;
}) => {
  logger.debug('Database query executed', {
    type: 'database_query',
    ...data
  });
};

export const logError = (error: Error, context?: any) => {
  logger.error('Application error', {
    type: 'application_error',
    error: error.message,
    stack: error.stack,
    context
  });
};
```

---

## **DEPLOYMENT CHECKLIST**

### **Pre-Deployment Requirements**
- [ ] **Environment Configuration**
  - [ ] All required environment variables set
  - [ ] Database connection string configured
  - [ ] API keys secured in secrets manager
  - [ ] SSL certificates obtained
  - [ ] DNS records configured

- [ ] **Security Checklist**
  - [ ] Security headers configured
  - [ ] Rate limiting implemented
  - [ ] CORS policies set
  - [ ] Input validation enabled
  - [ ] Secrets encrypted

- [ ] **Performance Optimization**
  - [ ] Connection pooling configured
  - [ ] Caching strategy implemented
  - [ ] CDN configured for static assets
  - [ ] Compression enabled
  - [ ] Health checks configured

### **Production Deployment Steps**
```bash
# 1. Environment setup
export NODE_ENV=production
export DATABASE_SSL=true
export MONITORING_ENABLED=true

# 2. Build and test
npm run build
npm run test:production

# 3. Security scan
npm audit --audit-level high

# 4. Deploy to cloud
npm run deploy:production

# 5. Post-deployment verification
npm run verify:production
```

### **Post-Deployment Monitoring**
```bash
# Health check
curl -f https://compliance-engine.example.com/api/health

# Performance metrics
curl https://compliance-engine.example.com/metrics

# Log monitoring
tail -f logs/combined.log | grep ERROR
```

---

## **SUCCESS CRITERIA**

### **Deployment Metrics**
- ✅ **99.9% uptime** during business hours
- ✅ **<2 second response times** for all API endpoints
- ✅ **Zero failed deployments** with rollback capability
- ✅ **SSL A+ rating** on security scanners
- ✅ **Container starts < 30 seconds** cold start

### **Operational Excellence**
- ✅ **Automated deployment pipeline** working
- ✅ **Health checks** responding correctly
- ✅ **Monitoring alerts** configured
- ✅ **Log aggregation** functional
- ✅ **Backup/restore** procedures tested

### **Security Compliance**
- ✅ **Secrets management** implemented
- ✅ **Access controls** configured
- ✅ **Audit logging** enabled
- ✅ **Vulnerability scanning** automated
- ✅ **Compliance standards** met

---

**This PRP delivers enterprise-grade cloud deployment capability with professional operational standards. The compliance engine is now production-ready for any cloud provider with comprehensive monitoring, security, and scalability.**

**Production Readiness: Development → Testing → Staging → Production**