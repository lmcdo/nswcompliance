# NSW Planning Compliance Engine - Deployment Preparation Guide

## Current Status ✅

### **CLI Tools Ready**
- ✅ **Vercel CLI v41.7.0** - Authenticated as `lawrencemcdonell`
- ✅ **Supabase CLI v2.22.12** - 3 projects available
- ⚠️ **Supabase update** recommended to v2.54.11

### **Available Supabase Projects**
1. **nursecompliance** (dcduuaxzswwocgltaogz) - Southeast Asia
2. **nswpropertycloudapi** (yfzvvghmywbhhwdhhbjo) - Southeast Asia
3. **plotdetectChatbot** (wbvxdnmsmyzxxbwydhph) - Southeast Asia

---

## 🚀 Production Deployment Steps

### **Phase 1: Supabase Setup (Day 1)**

#### **1.1 Create New Supabase Project**
```bash
# Create dedicated project for NSW Compliance Engine
supabase projects create nsw-compliance-engine \
  --org-id sgezzktqeabipvkigcyg \
  --region southeast-asia \
  --db-password secure_password_here
```

#### **1.2 Link Project to Local Directory**
```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
supabase link --project-ref [new-project-ref]
```

#### **1.3 Database Migration**
```bash
# Generate migration from existing schema
supabase db diff --schema public --use-migra -f initial_schema

# Apply migration to new Supabase project
supabase db push
```

#### **1.4 Environment Variables Setup**
```bash
# Add to .env.local
DATABASE_URL="postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"
SUPABASE_URL="https://[project-ref].supabase.co"
SUPABASE_ANON_KEY="[anon-key]"
SUPABASE_SERVICE_ROLE_KEY="[service-role-key]"
```

#### **1.5 Row Level Security (RLS)**
```sql
-- Enable RLS on key tables
ALTER TABLE dcp_general_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE dcp_precinct_provisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory_provisions ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
CREATE POLICY "Users can view all provisions" ON dcp_general_requirements
  FOR SELECT USING (true);

CREATE POLICY "Users can view precinct provisions" ON dcp_precinct_provisions
  FOR SELECT USING (true);
```

### **Phase 2: Database Optimization (Day 1-2)**

#### **2.1 Performance Indexes**
```sql
-- Create indexes for common queries
CREATE INDEX idx_precinct_boundaries_geom ON dcp_precinct_boundaries USING GIST(boundary);
CREATE INDEX idx_general_requirements_zone ON dcp_general_requirements(zone, former_council);
CREATE INDEX idx_precinct_requirements_precinct_id ON dcp_precinct_requirements(precinct_id);
CREATE INDEX idx_regulatory_provisions_hierarchy ON regulatory_provisions(hierarchy_level, council);

-- Full-text search indexes
CREATE INDEX idx_provisions_search ON regulatory_provisions USING GIN(to_tsvector('english', provision_text));
CREATE INDEX idx_requirements_search ON dcp_general_requirements USING GIN(to_tsvector('english', requirement_text));
```

#### **2.2 Connection Pool Configuration**
```typescript
// Update lib/db.ts for Supabase
export function getPool(): Pool {
  if (!globalForDb.pool) {
    globalForDb.pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: true },
      max: 15, // Optimized for Vercel limits
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 10000,
      keepAlive: true,
    });
  }
  return globalForDb.pool;
}
```

### **Phase 3: Application Optimization (Day 2-3)**

#### **3.1 Add Caching Layer**
```bash
# Install Redis client
npm install ioredis @types/ioredis
```

```typescript
// lib/cache.ts
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

export async function getCachedData<T>(
  key: string,
  fetchFn: () => Promise<T>,
  ttl: number = 3600
): Promise<T> {
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached);

  const data = await fetchFn();
  await redis.setex(key, ttl, JSON.stringify(data));
  return data;
}
```

#### **3.2 Rate Limiting Implementation**
```bash
# Install rate limiting
npm install express-rate-limit @types/express-rate-limit
```

```typescript
// middleware/rateLimiter.ts
import rateLimit from 'express-rate-limit';

export const complianceLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false,
});
```

#### **3.3 API Response Caching**
```javascript
// vercel.json
{
  "caching": {
    "patterns": [
      {
        "match": "/api/compliance/**",
        "headers": {
          "Cache-Control": "public, max-age=300, s-maxage=600"
        }
      },
      {
        "match": "/api/property/**",
        "headers": {
          "Cache-Control": "public, max-age=600, s-maxage=1800"
        }
      }
    ]
  },
  "functions": {
    "app/api/**/*.route": {
      "maxDuration": 30,
      "memory": 1024,
      "runtime": "nodejs18.x"
    }
  }
}
```

### **Phase 4: Vercel Deployment (Day 3-4)**

#### **4.1 Environment Variables Setup**
```bash
# Set Vercel environment variables
vercel env add DATABASE_URL production
vercel env add SUPABASE_URL production
vercel env add SUPABASE_ANON_KEY production
vercel env add SUPABASE_SERVICE_ROLE_KEY production
vercel env add NSW_PLANNING_API_BASE_URL production
vercel env add GOOGLE_PLACES_API_KEY production
```

#### **4.2 Build Configuration**
```javascript
// next.config.js (updated)
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['better-sqlite3']
  },
  reactStrictMode: false,
  swcMinify: false,
  // Production optimizations
  compress: true,
  poweredByHeader: false,
  images: {
    domains: ['maps.googleapis.com'],
    formats: ['image/webp', 'image/avif'],
  },
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.watchOptions = {
        poll: false,
        ignored: /node_modules/
      };
    }
    if (isServer) {
      config.externals.push('better-sqlite3');
    }
    return config;
  },
  env: {
    NSW_PLANNING_API_BASE_URL: process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning',
    GOOGLE_PLACES_API_KEY: process.env.GOOGLE_PLACES_API_KEY || '',
  }
};
```

#### **4.3 Deploy to Vercel**
```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### **Phase 5: Production Hardening (Day 4-5)**

#### **5.1 Monitoring Setup**
```typescript
// lib/monitoring.ts
export function setupMonitoring() {
  // Health check endpoint
  app.get('/api/health', async (req, res) => {
    try {
      const poolStats = getPoolStats();
      const dbHealth = await query('SELECT 1');

      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        database: poolStats,
        uptime: process.uptime()
      });
    } catch (error) {
      res.status(500).json({
        status: 'unhealthy',
        error: error.message
      });
    }
  });
}
```

#### **5.2 Error Tracking**
```bash
# Install error tracking
npm install @sentry/nextjs
```

```typescript
// sentry.client.config.js
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
});
```

#### **5.3 Performance Monitoring**
```typescript
// lib/performance.ts
export function logPerformance(metric: string, value: number) {
  console.log(`[Performance] ${metric}: ${value}ms`);

  // Send to monitoring service
  if (process.env.NODE_ENV === 'production') {
    // Integration with Vercel Analytics or custom monitoring
  }
}
```

---

## 📊 Pre-Deployment Checklist

### **Database Setup**
- [ ] Supabase project created and linked
- [ ] Schema migrated successfully
- [ ] Indexes created for performance
- [ ] RLS policies implemented
- [ ] Connection pooling configured

### **Application Configuration**
- [ ] Environment variables set in Vercel
- [ ] Caching layer implemented
- [ ] Rate limiting configured
- [ ] Error handling improved
- [ ] Monitoring endpoints added

### **Security**
- [ ] SSL/TLS enforced
- [ ] API keys secured
- [ ] RLS policies tested
- [ ] Rate limiting tested
- [ ] Input validation implemented

### **Performance**
- [ ] Bundle size optimized
- [ ] Database queries optimized
- [ ] Caching strategies implemented
- [ ] CDN configuration verified
- [ ] Load testing completed

---

## 🚨 Critical Considerations

### **Database Migration Risks**
- **Data integrity**: Validate all data after migration
- **Performance**: Monitor query performance post-migration
- **Connectivity**: Test all API endpoints with new database

### **External Dependencies**
- **NSW Planning API**: Monitor rate limits and availability
- **Google Maps API**: Track usage and costs
- **Supabase**: Monitor connection pool usage

### **Scaling Considerations**
- **Vercel limits**: Monitor function execution time and memory
- **Supabase limits**: Track database connections and storage
- **User load**: Implement gradual scaling strategy

---

## 📈 Expected Performance Metrics

### **Target Performance**
- **Page Load Time**: < 2 seconds
- **API Response Time**: < 500ms (with caching)
- **Database Query Time**: < 100ms (with indexes)
- **Concurrent Users**: 500-1000+ comfortable
- **Memory Usage**: < 512MB per request

### **Monitoring Alerts**
- API response time > 1 second
- Database connection pool > 80% utilized
- Error rate > 5%
- Memory usage > 800MB per function

---

## 🔄 Ongoing Maintenance

### **Weekly Tasks**
- Review performance metrics
- Check database query performance
- Monitor external API usage
- Update dependencies as needed

### **Monthly Tasks**
- Review and optimize slow queries
- Update Supabase and Vercel configurations
- Conduct security audits
- Plan scaling improvements

### **Quarterly Tasks**
- Major performance reviews
- Architecture assessment
- Cost optimization review
- Disaster recovery testing

---

## 📞 Support and Troubleshooting

### **Common Issues**
1. **Database Connection Errors**: Check Supabase project status and connection strings
2. **Slow API Responses**: Review database query performance and caching
3. **High Memory Usage**: Optimize function code and check for memory leaks
4. **Rate Limiting**: Adjust limits based on usage patterns

### **Emergency Contacts**
- **Vercel Support**: Available through Vercel dashboard
- **Supabase Support**: Available through Supabase dashboard
- **Monitoring Alerts**: Configured notifications for critical issues

---

*Last Updated: November 2025*
*Ready for Production Deployment*