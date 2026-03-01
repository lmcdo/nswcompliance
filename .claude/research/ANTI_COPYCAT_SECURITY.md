# Anti-Copycat Security Strategy

**Threat:** Competitor uses AI tools to reverse-engineer and copy our AI layer implementation
**Goal:** Make copying require >100 hours of effort (uneconomical)

---

## CRITICAL PROTECTIONS (Implement Week 1)

### 1. Route Obfuscation (2 hours)

**Replace obvious routes with hashes:**

```typescript
// BEFORE - Obvious
/api/ai/chat
/api/contextual-guidance

// AFTER - Obfuscated
/api/q/7f3a8b2c
/api/r/2e9d1c4f

// Implementation
// frontend-nextjs/lib/api/routes.ts (ADD TO .gitignore!)
export const API_ROUTES = {
  AI_CHAT: `/api/q/${process.env.NEXT_PUBLIC_ROUTE_HASH_1}`,
  GUIDANCE: `/api/r/${process.env.NEXT_PUBLIC_ROUTE_HASH_2}`,
};

// Store hashes in Vercel env vars only (never commit)
```

### 2. Response Obfuscation (1 hour)

**Encode responses so structure isn't obvious:**

```typescript
// BEFORE - Reveals structure
{ "answer": "Tree canopy: 25%", "citations": ["DCP 4.3.2"] }

// AFTER - Encoded
{ "d": "VHJlZSBjYW5vcHk6IDI1JQ==", "c": ["RENQIDQuMy4y"] }

// lib/response-encoder.ts
export const encodeResponse = (r: Response) => ({
  d: btoa(r.answer),
  c: r.citations.map(btoa),
  f: Math.round(r.confidence * 100)
});
```

### 3. Aggressive Rate Limiting (30 min)

```typescript
// CURRENT: 5 req/min per IP
// ENHANCED: 5 req/hour for suspected bots

if (isBotUA(userAgent) || !hasFingerprint) {
  limit = 5;  // per hour, not minute
}

// Block completely after 3 violations
if (violations >= 3) {
  await blockIP(ip);
}
```

### 4. Database Error Sanitization (1 hour)

```typescript
// BEFORE - Leaks schema
catch (error) {
  return Response.json({ error: error.message });
  // "column confidence_score does not exist" → reveals schema
}

// AFTER - Generic only
catch (error) {
  logError(error);  // Log internally
  return Response.json({ error: 'Query failed' });  // Generic to client
}
```

### 5. Honeypot Routes (1 hour)

**Create fake "obvious" routes that log access attempts:**

```typescript
// app/api/ai/chat/route.ts (FAKE - honeypot)
export async function POST(req: Request) {
  await logHoneypot(req);  // Alert: someone's probing
  return Response.json({ error: 'Service unavailable' }, { status: 503 });
}

// Real route is /api/q/7f3a8b2c (hidden)
```

**Week 1 Total:** 5.5 hours

---

## MEDIUM PRIORITY (Week 2-3)

### 6. Split Endpoint Logic (2 hours)

**Don't expose full flow in one endpoint:**

```typescript
// BEFORE - Single endpoint reveals everything
POST /api/ai/chat → classify → fetch → format → return

// AFTER - Split into 3 calls
POST /api/q/[hash1] → classify only → returns route hash
GET /api/r/[hash2] → fetch data only
POST /api/x/[hash3] → format only

// Competitor must reverse-engineer 3 steps + understand relationship
```

### 7. Client Code Minification (1 hour)

```javascript
// next.config.js
webpack: (config) => {
  config.optimization.minimize = true;
  config.optimization.minimizer = [new TerserPlugin({
    terserOptions: {
      mangle: { properties: { regex: /^_/ } },
      compress: { drop_console: true }
    }
  })];
}
```

### 8. Template Server-Side Only (1 hour)

**Never expose templates to client:**

```typescript
// BEFORE - Template downloadable
const template = await fetch('/templates/guidance.json');

// AFTER - Server renders, client gets result only
// Templates stored in database or server-side files only
```

---

## IMPLEMENTATION FILES

### Files to Add to .gitignore (CRITICAL)

```bash
# .gitignore - ADD THESE NOW
frontend-nextjs/lib/api/routes.ts
frontend-nextjs/lib/response-encoder.ts
frontend-nextjs/lib/templates/
.env.local
```

### Files to Create

1. **frontend-nextjs/lib/api/routes.ts** (not committed)
   - Route hash mappings
   - Built from env vars

2. **frontend-nextjs/lib/response-encoder.ts** (not committed)
   - Encode/decode logic
   - Obfuscation utilities

3. **frontend-nextjs/lib/rate-limit-enhanced.ts**
   - Bot detection
   - Fingerprint validation
   - IP blocking

4. **frontend-nextjs/app/api/ai/chat/route.ts** (honeypot)
   - Fake endpoint
   - Logs access attempts

5. **frontend-nextjs/app/api/q/[hash]/route.ts** (real)
   - Actual AI chat endpoint
   - Hash verification

### Environment Variables (Vercel Dashboard)

```bash
# Production only (NEVER commit)
NEXT_PUBLIC_ROUTE_HASH_1=7f3a8b2c
NEXT_PUBLIC_ROUTE_HASH_2=2e9d1c4f
NEXT_PUBLIC_ROUTE_HASH_3=9a4f2e1b
ROUTE_HASH_SECRET_KEY=<random-256-bit-key>

# Generate with:
node -e "console.log(require('crypto').randomBytes(4).toString('hex'))"
```

---

## MONITORING

### Daily Checks (2 min)

```sql
-- Check honeypot hits (someone's probing)
SELECT ip, user_agent, COUNT(*)
FROM honeypot_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY ip, user_agent
HAVING COUNT(*) > 5;
```

### Weekly Analysis (10 min)

```sql
-- Blocked IPs
SELECT ip, block_reason, blocked_at
FROM blocked_ips
WHERE blocked_at > NOW() - INTERVAL '7 days';

-- Unusual request patterns
SELECT ip, COUNT(*) as req_count
FROM request_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY ip
HAVING COUNT(*) > 100;  -- Suspiciously high
```

---

## LEGAL PROTECTION

### Add to Terms of Service

```markdown
**Prohibited Activities**

You may not:
- Reverse engineer, decompile, or disassemble any part of the Service
- Use automated tools to access the Service except via official API
- Systematically download or scrape content
- Attempt to discover source code or underlying algorithms

Violations may result in immediate account termination and legal action.
```

### Add to robots.txt

```
User-agent: *
Disallow: /api/

User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: CCBot
Disallow: /
```

---

## SUCCESS METRICS

**Security is working if:**
- [ ] Honeypot routes detect 0-2 hits/week (low probing)
- [ ] No obvious API routes visible in browser DevTools
- [ ] Rate limiting blocks bots within 5 requests
- [ ] No database schema exposed in error messages
- [ ] Competitor analysis shows >50 hours required to reverse-engineer

**Red flags (security failing):**
- [ ] Honeypot hits >10/week (active probing)
- [ ] Scraping succeeds for >100 requests
- [ ] API routes discoverable via simple inspection
- [ ] Error messages reveal table/column names

---

**Priority:** CRITICAL - Implement items 1-5 (5.5 hours) before Phase 1 production deployment
**Status:** Pre-implementation
**Last Updated:** 2026-02-01
