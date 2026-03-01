# Security Audit: Production Code (Active)
## Focus: Next.js API Routes on Vercel

**Date:** 2026-01-30
**Scope:** Active production code only (Python scripts excluded - not deployed)
**Architecture:** Next.js (TypeScript) + Supabase (PostgreSQL)

---

## Production Architecture

```
USER REQUEST
     │
     ▼
[Vercel Edge Network]
     │
     ▼
[Next.js API Routes] ← 71 endpoints (AUDIT THESE)
     │
     ▼
[Supabase PostgreSQL] ← Database (Row-Level Security?)
```

**NOT in scope:**
- ❌ Python scripts (only run locally, not deployed)
- ❌ Data extraction/enrichment scripts
- ❌ Analysis scripts

---

## Critical Security Areas

### 1. Input Validation ⚠️ MIXED

**GOOD Example:** `/api/feedback/submit/route.ts`
```typescript
import { z } from 'zod';

const feedbackSchema = z.object({
  type: z.enum(['address_issue', 'missing_data', 'incorrect_calculation', 'general']),
  context: z.object({
    propertyAddress: z.string(),
    section: z.string(),
  }),
  description: z.string().min(1),
  userType: z.enum(['certifier', 'planner', 'developer', 'architect', 'other']),
  severity: z.enum(['low', 'medium', 'high']),
  contactEmail: z.string().email().optional(),
});

// Validate BEFORE database operation
const validatedFeedback = feedbackSchema.parse(body);
```

✅ **Uses Zod for validation**
✅ **Rejects invalid input before SQL**

---

**CONCERN:** `/api/provisions/for-property/route.ts` (lines 32-48)
```typescript
interface PropertyFilters {
  lga?: string;               // ⚠️ User-controlled
  zone?: string;              // ⚠️ User-controlled
  precinct_id?: string;       // ⚠️ User-controlled
  dev_type?: string;          // ⚠️ User-controlled
  topic?: string;             // ⚠️ User-controlled
  version_date?: string;      // ⚠️ User-controlled (date parsing!)
  hca?: string;               // ⚠️ User-controlled
}

// NO ZOD VALIDATION VISIBLE IN FIRST 150 LINES
```

**Risk:** Unvalidated input could cause:
- ❌ SQL injection (if not parameterized)
- ❌ Date parsing exploits
- ❌ Resource exhaustion (malformed queries)

**Recommendation:** Add Zod schema:
```typescript
const propertyFiltersSchema = z.object({
  lga: z.string().max(100).optional(),
  zone: z.string().regex(/^[A-Z0-9]+$/).max(10).optional(),
  precinct_id: z.string().max(50).optional(),
  dev_type: z.enum([
    'dwelling_house', 'secondary_dwelling', 'dual_occupancy',
    'multi_dwelling_housing', /* ... */
  ]).optional(),
  topic: z.enum(['setbacks', 'parking', 'heritage', /* ... */]).optional(),
  version_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  hca: z.string().max(100).optional(),
});
```

---

### 2. SQL Injection Protection ✅ GOOD (Mostly)

**All queries use parameterized statements:**
```typescript
// GOOD: Parameterized query
const result = await query(`
  INSERT INTO user_feedback (type, property_address, description)
  VALUES ($1, $2, $3)
`, [
  validatedFeedback.type,
  validatedFeedback.context.propertyAddress,
  validatedFeedback.description
]);
```

✅ **No string concatenation in SQL**
✅ **Uses $1, $2, $3 placeholders**

**Verify in other 64 API routes:**
- Check for string interpolation: `` `SELECT * FROM table WHERE id = ${userId}` ``
- Check for template literals in SQL
- Ensure all user input uses `$N` placeholders

**Action Required:** Audit all 64 API routes for SQL injection

---

### 3. Authentication & Authorization ❌ NOT VISIBLE

**Critical Question:** Are API routes protected?

Looking at `/api/feedback/submit/route.ts`:
```typescript
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    // NO AUTH CHECK VISIBLE
    const validatedFeedback = feedbackSchema.parse(body);
    // Inserts directly into database
```

**Concern:** No authentication middleware visible.

**Questions:**
1. ❓ Can anyone call these APIs without authentication?
2. ❓ Is there rate limiting?
3. ❓ Are there API keys required?
4. ❓ Is Supabase Row-Level Security (RLS) enabled?

**Where to check:**
- `frontend-nextjs/middleware.ts` (Next.js middleware for auth)
- Supabase dashboard → Authentication → Policies
- Vercel dashboard → Edge Config (rate limiting)

**High-Risk Endpoints (Need Auth):**
```
/api/feedback/submit        ← Anyone can spam feedback
/api/ai/chat               ← LLM costs money (needs rate limit)
/api/admin/cache           ← ADMIN endpoint (needs strict auth)
/api/assessment/full       ← Could be scraped (needs rate limit)
```

---

### 4. Environment Variable Exposure ⚠️ NEEDS REVIEW

**23 files use environment variables:**
```typescript
process.env.SLACK_WEBHOOK_URL
process.env.DATABASE_URL
process.env.OPENAI_API_KEY       // ← LLM costs
process.env.SUPABASE_KEY         // ← Database access
```

**Check:**
```bash
# View what's exposed to client
grep "NEXT_PUBLIC_" frontend-nextjs/.env.local
```

**Rules:**
- ✅ `NEXT_PUBLIC_*` = OK to expose (client-side safe)
- ❌ `DATABASE_URL` = NEVER expose to client
- ❌ `OPENAI_API_KEY` = NEVER expose to client

**Action Required:**
1. Audit `.env.local` and `.env.vercel.final`
2. Ensure secrets are NOT prefixed with `NEXT_PUBLIC_`
3. Check Vercel dashboard → Environment Variables

---

### 5. Rate Limiting ❓ UNKNOWN

**Critical for cost control:**
```
/api/ai/chat               ← LLM API costs ($)
/api/assessment/full       ← Heavy database queries
/api/provisions/*          ← Could be scraped
```

**Without rate limiting:**
- 💸 **Cost:** Attacker spams `/api/ai/chat` → $1000s in OpenAI bills
- 💾 **Database:** DoS via heavy queries
- 🕷️ **Scraping:** Competitors scrape all provisions

**Solutions:**
1. **Vercel Rate Limiting** (built-in, check dashboard)
2. **Upstash Redis** (rate limiting middleware)
3. **API Key requirement** (for commercial use)

**Action Required:** Check Vercel dashboard → Edge Functions → Rate Limits

---

### 6. CORS Configuration ⚠️ NEEDS REVIEW

**Are APIs open to any origin?**

Check for CORS headers:
```typescript
// BAD: Allows any origin
res.setHeader('Access-Control-Allow-Origin', '*');

// GOOD: Restricts to your domain
res.setHeader('Access-Control-Allow-Origin', 'https://plotdetect.com.au');
```

**Action Required:**
```bash
grep -r "Access-Control-Allow-Origin" frontend-nextjs/app/api
```

If `*` is used, anyone can call your APIs from their website.

---

### 7. Sensitive Data Logging ⚠️ POTENTIAL LEAK

**Example from `/api/feedback/submit/route.ts`:**
```typescript
console.error('Feedback submission error:', error);
```

**Concern:** What if `error` contains user PII?

**Check Vercel logs:**
- Do errors log full request bodies?
- Do errors log email addresses?
- Do errors log IP addresses?

**Best Practice:**
```typescript
// BAD: Logs entire error object (may contain PII)
console.error('Error:', error);

// GOOD: Logs sanitized error
console.error('Error:', {
  message: error.message,
  code: error.code,
  // NO user data
});
```

**Action Required:** Audit console.log/error statements in all 64 API routes

---

## Quick Security Audit Checklist

Run these commands to find issues:

### 1. Find API routes without Zod validation
```bash
cd frontend-nextjs/app/api
for file in $(find . -name "route.ts"); do
  if ! grep -q "z\\.object\|zod" "$file"; then
    echo "⚠️  NO ZOD: $file"
  fi
done
```

### 2. Find SQL queries with string interpolation (SQL injection risk)
```bash
grep -r "\`SELECT.*\${" frontend-nextjs/app/api --include="*.ts"
grep -r "\`INSERT.*\${" frontend-nextjs/app/api --include="*.ts"
grep -r "\`UPDATE.*\${" frontend-nextjs/app/api --include="*.ts"
```

### 3. Find exposed secrets (client-side leak risk)
```bash
grep "NEXT_PUBLIC_.*KEY\|NEXT_PUBLIC_.*SECRET" frontend-nextjs/.env.local
```

### 4. Find admin endpoints (need strict auth)
```bash
find frontend-nextjs/app/api -name "*.ts" | xargs grep -l "admin\|debug\|cache"
```

### 5. Check for authentication middleware
```bash
ls frontend-nextjs/middleware.ts 2>/dev/null || echo "❌ NO MIDDLEWARE"
```

---

## Top 10 Security Priorities

| Priority | Issue | Risk Level | Fix Time |
|----------|-------|------------|----------|
| **P0** | Add auth to `/api/admin/*` | 🔴 CRITICAL | 30 min |
| **P0** | Add rate limiting to `/api/ai/chat` | 🔴 CRITICAL (cost) | 1 hour |
| **P1** | Add Zod validation to all API routes | 🟠 HIGH | 4 hours |
| **P1** | Audit SQL queries for injection | 🟠 HIGH | 2 hours |
| **P1** | Add rate limiting to all APIs | 🟠 HIGH | 1 hour |
| **P2** | Review CORS configuration | 🟡 MEDIUM | 30 min |
| **P2** | Sanitize error logs (PII) | 🟡 MEDIUM | 2 hours |
| **P2** | Check Supabase RLS policies | 🟡 MEDIUM | 1 hour |
| **P3** | Add API key requirement | 🟢 LOW | 2 hours |
| **P3** | Add security headers (CSP, HSTS) | 🟢 LOW | 1 hour |

**Total fix time:** ~15 hours (for high-priority issues)

---

## Supabase Security (Database Layer)

### Row-Level Security (RLS) ❓ STATUS UNKNOWN

**Critical Question:** Is RLS enabled on Supabase tables?

**Check in Supabase Dashboard:**
1. Go to Database → Tables
2. For each table, check "Enable Row Level Security"
3. Define policies:
   ```sql
   -- Example: Only allow reads (no writes from client)
   CREATE POLICY "Public read access"
   ON regulatory_provisions
   FOR SELECT
   TO public
   USING (true);

   -- Prevent all writes from client
   CREATE POLICY "No public writes"
   ON regulatory_provisions
   FOR ALL
   TO public
   USING (false);
   ```

**Without RLS:**
- ❌ Client can bypass API and query database directly
- ❌ Client can modify/delete data if credentials leaked

**Action Required:** Enable RLS on ALL tables

---

## Recommended Security Stack

### 1. Authentication: Supabase Auth (or Clerk)
```typescript
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });
  const { data: { user } } = await supabase.auth.getUser();

  if (!user && req.nextUrl.pathname.startsWith('/api/admin')) {
    return NextResponse.redirect(new URL('/login', req.url));
  }

  return res;
}
```

### 2. Rate Limiting: Upstash Redis
```typescript
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, '10 s'), // 10 requests per 10 seconds
});

export async function POST(request: NextRequest) {
  const ip = request.ip ?? '127.0.0.1';
  const { success } = await ratelimit.limit(ip);

  if (!success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded' },
      { status: 429 }
    );
  }

  // Process request...
}
```

### 3. Input Validation: Zod (already using in 1 endpoint)
```typescript
import { z } from 'zod';

const schema = z.object({
  address: z.string().min(1).max(200),
  zone: z.string().regex(/^[A-Z0-9]+$/),
});

const validated = schema.parse(await request.json());
```

---

## Next Steps

### Immediate (This Week):
1. ✅ **Run security audit commands** (above)
2. ✅ **Check Vercel dashboard** for rate limits
3. ✅ **Check Supabase dashboard** for RLS policies
4. ✅ **Add auth to `/api/admin/*`** endpoints

### Short-term (This Month):
1. ⚠️ **Add Zod validation** to all 64 API routes
2. ⚠️ **Enable Supabase RLS** on all tables
3. ⚠️ **Add rate limiting** to expensive endpoints
4. ⚠️ **Audit SQL queries** for injection

### Long-term:
1. 🔒 **Add API key system** for commercial users
2. 🔒 **Add monitoring** (Sentry for errors, PostHog for usage)
3. 🔒 **Add security headers** (CSP, HSTS, X-Frame-Options)

---

## Testing for Vulnerabilities

### SQL Injection Test
```bash
# Try malicious input
curl -X POST https://your-domain.com/api/provisions/for-property \
  -H "Content-Type: application/json" \
  -d '{"lga": "Inner West\"; DROP TABLE regulatory_provisions; --"}'

# Should return: Validation error (if protected)
# Should NOT: Drop the table
```

### Rate Limit Test
```bash
# Spam endpoint
for i in {1..100}; do
  curl https://your-domain.com/api/ai/chat
done

# Should return: 429 Too Many Requests (if protected)
# Should NOT: Process all 100 requests
```

### Auth Bypass Test
```bash
# Try accessing admin endpoint without auth
curl https://your-domain.com/api/admin/cache

# Should return: 401 Unauthorized (if protected)
# Should NOT: Return cache data
```

---

*Document Status: AUDIT REQUIRED*
*Next Action: Run security audit commands and review Vercel/Supabase dashboards*
*Owner: Lawrence (PlotDetect)*
