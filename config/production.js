/**
 * PRP-A3: Production Configuration Management
 * Enterprise-grade configuration for cloud deployment
 *
 * Supports AWS, Azure, GCP with secrets management
 */

const path = require('path');

module.exports = {
  // Database Configuration (PRP-A2 Compatible)
  database: {
    // Primary connection (direct database architecture)
    host: process.env.POSTGRES_HOST || process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || process.env.DB_PORT || '5432'),
    database: process.env.POSTGRES_DB || process.env.DB_NAME || 'nsw_planning',
    username: process.env.POSTGRES_USER || process.env.DB_USER || 'postgres',
    password: process.env.POSTGRES_PASSWORD || process.env.DB_PASSWORD || '',

    // Connection pooling (PRP-A2 optimized)
    pool: {
      min: parseInt(process.env.DB_POOL_MIN || '2'),
      max: parseInt(process.env.DB_POOL_MAX || '20'),
      idle: parseInt(process.env.DB_IDLE_TIMEOUT || '30000'),
      acquire: parseInt(process.env.DB_CONNECTION_TIMEOUT || '2000'),
      evict: parseInt(process.env.DB_EVICT_TIMEOUT || '1000'),
    },

    // SSL configuration for cloud deployment
    ssl: process.env.NODE_ENV === 'production' ? {
      require: true,
      rejectUnauthorized: process.env.DB_SSL_REJECT_UNAUTHORIZED !== 'false'
    } : false,

    // Statement timeouts (CLAUDE.md compliance)
    statement_timeout: parseInt(process.env.DB_STATEMENT_TIMEOUT || '30000'),
    query_timeout: parseInt(process.env.DB_QUERY_TIMEOUT || '30000'),

    // Backup configuration
    backup: {
      enabled: process.env.DB_BACKUP_ENABLED === 'true',
      interval: process.env.DB_BACKUP_INTERVAL || '1h',
      retention: process.env.DB_BACKUP_RETENTION || '7d',
      storage: process.env.DB_BACKUP_STORAGE || 's3://backup-bucket/database'
    }
  },

  // Redis Configuration (Session & Caching)
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD || '',
    db: parseInt(process.env.REDIS_DB || '0'),

    // Cluster support
    cluster: process.env.REDIS_CLUSTER_NODES ?
      process.env.REDIS_CLUSTER_NODES.split(',').map(node => {
        const [host, port] = node.split(':');
        return { host, port: parseInt(port) };
      }) : null,

    // TLS for cloud
    tls: process.env.REDIS_TLS === 'true' ? {
      servername: process.env.REDIS_HOST
    } : undefined
  },

  // External API Configuration
  apis: {
    // NSW Planning Portal
    nswPlanning: {
      baseUrl: process.env.NSW_PLANNING_API_URL || 'https://api.planningportal.nsw.gov.au',
      timeout: parseInt(process.env.NSW_PLANNING_TIMEOUT || '10000'),
      retries: parseInt(process.env.NSW_PLANNING_RETRIES || '3'),
      rateLimit: {
        requests: parseInt(process.env.NSW_PLANNING_RATE_LIMIT || '100'),
        window: parseInt(process.env.NSW_PLANNING_RATE_WINDOW || '60000')
      }
    },

    // Google Maps
    googleMaps: {
      apiKey: process.env.GOOGLE_MAPS_API_KEY,
      placesApiKey: process.env.GOOGLE_PLACES_API_KEY,
      timeout: parseInt(process.env.GOOGLE_MAPS_TIMEOUT || '5000')
    },

    // AI Services
    openai: {
      apiKey: process.env.OPENAI_API_KEY,
      model: process.env.OPENAI_MODEL || 'gpt-4-turbo',
      timeout: parseInt(process.env.OPENAI_TIMEOUT || '30000'),
      maxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '4000')
    },

    deepseek: {
      apiKey: process.env.DEEPSEEK_API_KEY,
      timeout: parseInt(process.env.DEEPSEEK_TIMEOUT || '30000')
    },

    gemini: {
      apiKey: process.env.GEMINI_API_KEY,
      timeout: parseInt(process.env.GEMINI_TIMEOUT || '30000')
    }
  },

  // Security Configuration
  security: {
    // JWT tokens
    jwt: {
      secret: process.env.JWT_SECRET || 'change-in-production',
      expiresIn: process.env.JWT_EXPIRES_IN || '24h',
      algorithm: process.env.JWT_ALGORITHM || 'HS256'
    },

    // CORS
    cors: {
      origin: process.env.CORS_ORIGIN ?
        process.env.CORS_ORIGIN.split(',') :
        ['http://localhost:3000', 'http://localhost:3007'],
      credentials: true,
      maxAge: 86400
    },

    // Rate limiting
    rateLimit: {
      windowMs: parseInt(process.env.RATE_LIMIT_WINDOW || '900000'), // 15 minutes
      max: parseInt(process.env.RATE_LIMIT_MAX || '100'), // limit each IP to 100 requests per windowMs
      skipSuccessfulRequests: process.env.RATE_LIMIT_SKIP_SUCCESS === 'true'
    },

    // Helmet security headers
    helmet: {
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'", "'unsafe-inline'", "https://maps.googleapis.com"],
          styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
          fontSrc: ["'self'", "https://fonts.gstatic.com"],
          imgSrc: ["'self'", "data:", "https://maps.gstatic.com", "https://maps.googleapis.com"],
          connectSrc: ["'self'", "https://api.planningportal.nsw.gov.au"]
        }
      }
    }
  },

  // Logging Configuration
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    format: process.env.LOG_FORMAT || 'json',

    // Cloud logging
    cloudLogging: {
      enabled: process.env.CLOUD_LOGGING_ENABLED === 'true',
      projectId: process.env.GOOGLE_CLOUD_PROJECT_ID,
      keyFilename: process.env.GOOGLE_CLOUD_KEY_FILE
    },

    // File logging
    file: {
      enabled: process.env.FILE_LOGGING_ENABLED === 'true',
      path: process.env.LOG_FILE_PATH || './logs',
      maxFiles: parseInt(process.env.LOG_MAX_FILES || '5'),
      maxSize: process.env.LOG_MAX_SIZE || '10MB'
    },

    // Audit logging
    audit: {
      enabled: process.env.AUDIT_LOGGING_ENABLED === 'true',
      events: ['database_query', 'api_request', 'user_action', 'security_event']
    }
  },

  // Monitoring & Health Checks
  monitoring: {
    // Health check endpoints
    healthChecks: {
      enabled: true,
      endpoints: {
        liveness: '/health/live',
        readiness: '/health/ready',
        metrics: '/health/metrics'
      },

      // Component checks
      components: {
        database: { timeout: 5000, critical: true },
        redis: { timeout: 2000, critical: false },
        nswApi: { timeout: 10000, critical: false },
        fileSystem: { timeout: 1000, critical: true }
      }
    },

    // Metrics collection
    metrics: {
      enabled: process.env.METRICS_ENABLED === 'true',
      interval: parseInt(process.env.METRICS_INTERVAL || '60000'),
      retention: process.env.METRICS_RETENTION || '7d',

      // Prometheus
      prometheus: {
        enabled: process.env.PROMETHEUS_ENABLED === 'true',
        port: parseInt(process.env.PROMETHEUS_PORT || '9090'),
        endpoint: process.env.PROMETHEUS_ENDPOINT || '/metrics'
      }
    },

    // Error tracking
    errorTracking: {
      enabled: process.env.ERROR_TRACKING_ENABLED === 'true',
      dsn: process.env.SENTRY_DSN,
      environment: process.env.NODE_ENV,
      release: process.env.APP_VERSION
    }
  },

  // Performance & Scaling
  performance: {
    // Caching
    cache: {
      enabled: process.env.CACHE_ENABLED === 'true',
      ttl: parseInt(process.env.CACHE_TTL || '300'), // 5 minutes
      maxSize: parseInt(process.env.CACHE_MAX_SIZE || '100'), // 100MB

      // Strategy
      strategy: process.env.CACHE_STRATEGY || 'lru', // lru, lfu, fifo
    },

    // Compression
    compression: {
      enabled: process.env.COMPRESSION_ENABLED === 'true',
      level: parseInt(process.env.COMPRESSION_LEVEL || '6'),
      threshold: parseInt(process.env.COMPRESSION_THRESHOLD || '1024')
    },

    // Request limits
    limits: {
      json: process.env.JSON_LIMIT || '1mb',
      raw: process.env.RAW_LIMIT || '1mb',
      text: process.env.TEXT_LIMIT || '1mb',
      urlencoded: { limit: process.env.URLENCODED_LIMIT || '1mb', extended: true }
    }
  },

  // Feature Flags
  features: {
    // PRP-A2 Architecture (default to direct database)
    useDirectDatabase: process.env.USE_DIRECT_DATABASE !== 'false' &&
                      (process.env.USE_DIRECT_DATABASE === 'true' ||
                       process.env.COMPLIANCE_ARCHITECTURE === 'direct_database' ||
                       process.env.COMPLIANCE_ARCHITECTURE === undefined),
    complianceArchitecture: process.env.COMPLIANCE_ARCHITECTURE || 'direct_database',

    // Development features
    enableDebugMode: process.env.DEBUG_MODE === 'true',
    enableApiDocs: process.env.API_DOCS_ENABLED === 'true',
    enablePerformanceMode: process.env.PERFORMANCE_MODE === 'true',

    // Cloud features
    enableAutoScaling: process.env.AUTO_SCALING_ENABLED === 'true',
    enableLoadBalancer: process.env.LOAD_BALANCER_ENABLED === 'true',
    enableCDN: process.env.CDN_ENABLED === 'true'
  },

  // Cloud Provider Specific
  cloud: {
    provider: process.env.CLOUD_PROVIDER || 'aws', // aws, azure, gcp

    // AWS
    aws: {
      region: process.env.AWS_REGION || 'ap-southeast-2',
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      s3Bucket: process.env.AWS_S3_BUCKET,
      rdsEndpoint: process.env.AWS_RDS_ENDPOINT,
      elasticacheEndpoint: process.env.AWS_ELASTICACHE_ENDPOINT
    },

    // Azure
    azure: {
      subscriptionId: process.env.AZURE_SUBSCRIPTION_ID,
      clientId: process.env.AZURE_CLIENT_ID,
      clientSecret: process.env.AZURE_CLIENT_SECRET,
      tenantId: process.env.AZURE_TENANT_ID,
      resourceGroup: process.env.AZURE_RESOURCE_GROUP,
      sqlServer: process.env.AZURE_SQL_SERVER,
      redisCache: process.env.AZURE_REDIS_CACHE
    },

    // Google Cloud
    gcp: {
      projectId: process.env.GOOGLE_CLOUD_PROJECT_ID,
      keyFilename: process.env.GOOGLE_CLOUD_KEY_FILE,
      sqlInstance: process.env.GCP_SQL_INSTANCE,
      redisInstance: process.env.GCP_REDIS_INSTANCE,
      storageBucket: process.env.GCP_STORAGE_BUCKET
    }
  }
};