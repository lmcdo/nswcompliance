# Security Setup Guide

## Phase 0 Critical Fixes - Environment Variables

### Admin API Key (REQUIRED)

The admin endpoints now require authentication via the `ADMIN_API_KEY` environment variable.

#### Local Development

Add to `.env.local`:

```bash
# Generate a secure random string
# Example: openssl rand -base64 32
ADMIN_API_KEY=your_secure_admin_key_here
```

#### Production (Vercel)

Add to Vercel environment variables:

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add new variable:
   - **Name:** `ADMIN_API_KEY`
   - **Value:** Generate a secure random string (e.g., `openssl rand -base64 32`)
   - **Environments:** Production, Preview, Development

#### Using Admin Endpoints

Protected endpoints:
- `GET /api/admin/cache` - Get cache statistics
- `POST /api/admin/cache?action=clear` - Clear all caches
- `POST /api/admin/cache?action=cleanup` - Remove expired entries

**Example Request:**

```bash
curl -H "X-Admin-Key: your_admin_key_here" \
  https://plotdetect.com/api/admin/cache
```

**Security Notes:**
- If `ADMIN_API_KEY` is not configured, all admin endpoints will return 403 Forbidden (fail-secure)
- Never commit the actual key to git
- Rotate the key periodically (recommended: every 90 days)
- Use different keys for development and production

## Phase 0 Security Fixes Summary

✅ **Fixed SQL Injection** - `lib/database/postgres-client.ts:96`
   - Parameterized the `LIMIT` clause to prevent SQL injection
   - Added input sanitization (min 1, max 100)

✅ **Added AI Rate Limiting** - `/api/ai/chat`
   - 5 requests per minute per IP address
   - Returns 429 with Retry-After header when exceeded

✅ **Added Admin Authorization** - `/api/admin/cache`
   - Requires `X-Admin-Key` header matching `ADMIN_API_KEY`
   - Fail-secure: denies access if env var not configured

## Testing the Fixes

### Test SQL Injection Fix
```bash
# Try to inject malicious limit value
curl "http://localhost:3003/api/test?limit=999999"
# Should return max 100 results (capped)
```

### Test AI Rate Limit
```bash
# Send 6 requests quickly
for i in {1..6}; do
  curl -X POST http://localhost:3003/api/ai/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"test"}';
done
# 6th request should return 429 Rate Limit Exceeded
```

### Test Admin Authorization
```bash
# Without key - should fail
curl http://localhost:3003/api/admin/cache
# Returns 403 Forbidden

# With valid key - should succeed
curl -H "X-Admin-Key: your_key_here" \
  http://localhost:3003/api/admin/cache
# Returns cache stats
```

## Next Steps: Phase 1

The next security phase will include:
1. Centralized Zod validation schemas
2. Input validation on top 10 high-risk routes
3. Redis-based rate limiting (production-grade)

See the full security plan for details.
