# Deployment Best Practices

This document outlines best practices to avoid deployment issues in the future.

## Pre-Deployment Checklist

**Before every deployment, run:**
```bash
cd frontend-nextjs
npm run pre-deploy
```

This will:
- ✅ Type check all TypeScript files
- ✅ Lint all code
- ✅ Test production build locally

## Common Issues & Solutions

### 1. **Untracked Files Not in Git**

**Problem:** Files created locally but not committed to Git won't be deployed.

**Solution:**
```bash
# Check for untracked files regularly
git status

# Before committing, review what's not tracked
git ls-files --others --exclude-standard

# Add important files
git add frontend-nextjs/lib/
git add frontend-nextjs/components/
```

**Prevention:** Run `git status` before every commit.

### 2. **TypeScript Type Errors**

**Problem:** Code works locally but fails type checking in CI/CD.

**Solution:**
```bash
# Run type check locally BEFORE pushing
npm run type-check

# Fix all errors before committing
```

**Prevention:**
- Enable TypeScript strict mode in `tsconfig.json`
- Run `npm run type-check` in pre-commit hook
- Never use `// @ts-ignore` without good reason

### 3. **Missing Dependencies**

**Problem:** Package used but not in `package.json`.

**Solution:**
```bash
# Check for imports of packages not in package.json
grep -r "from ['\"]package-name['\"]" app/ lib/

# Install missing packages
npm install package-name
```

**Prevention:** Always use `npm install <package>` when adding new imports.

### 4. **Vercel-Incompatible Code**

**Problem:** Code relies on Node.js features unavailable in serverless.

**Issues to avoid:**
- ❌ Python subprocess calls (`spawn('python', ...)`)
- ❌ File system writes (temp files, uploads without proper storage)
- ❌ Long-running processes (>10 second timeout)
- ❌ Native dependencies (better-sqlite3, etc.)

**Solution:**
- Use PostgreSQL/Supabase instead of subprocess/SQLite
- Use cloud storage (S3, Vercel Blob) for file uploads
- Implement feature flags for local vs serverless code paths

**Example:**
```typescript
// ✅ Good: Feature flag approach
if (shouldUsePostgreSQL()) {
  return await postgresClient.query(...);
} else {
  throw new Error('PostgreSQL required in serverless');
}

// ❌ Bad: Python subprocess
const result = spawn('python', ['script.py']);
```

### 5. **Environment Variables**

**Problem:** Env vars work locally but not in production.

**Solution:**
```bash
# Check .env.local matches Vercel settings
cat .env.local

# Verify in Vercel dashboard:
# https://vercel.com/[team]/[project]/settings/environment-variables
```

**Prevention:** Document all required env vars in `.env.example`.

## Git Workflow

### Before Pushing Code

1. **Check status:**
   ```bash
   git status
   ```

2. **Review changes:**
   ```bash
   git diff
   ```

3. **Add files selectively:**
   ```bash
   git add frontend-nextjs/app/
   git add frontend-nextjs/lib/
   git add frontend-nextjs/components/
   ```

4. **Run pre-deploy checks:**
   ```bash
   npm run pre-deploy
   ```

5. **Commit and push:**
   ```bash
   git commit -m "feat: Add new feature"
   git push origin feature-branch
   ```

## Vercel Configuration

### Required Settings

1. **Root Directory:** `frontend-nextjs`
2. **Build Command:** `npm run build` (default)
3. **Output Directory:** `.next` (default)
4. **Install Command:** `npm install` (default)

### Environment Variables Required

```
PGHOST=aws-1-ap-southeast-2.pooler.supabase.com
PGDATABASE=postgres
PGUSER=postgres.llzdrxywpziewrzudwhj
PGPASSWORD=[your-password]
PGPORT=5432
NODE_ENV=production
```

## Debugging Failed Deployments

### 1. Check Build Logs
```bash
# Via Vercel CLI
vercel logs [deployment-url]

# Or visit:
# https://vercel.com/[team]/[project]/[deployment-id]
```

### 2. Common Error Patterns

**"Module not found"**
- File not committed to Git
- Missing dependency in package.json
- Incorrect import path (case sensitivity)

**"Type error"**
- Run `npm run type-check` locally
- Fix TypeScript errors before pushing

**"Command failed with exit code 1"**
- Check build logs for specific error
- Often related to env vars or dependencies

## TypeScript Configuration

### Re-enabling Type Checking

Once all type errors are fixed, re-enable strict checking:

```javascript
// next.config.js
const nextConfig = {
  // Remove these temporary overrides:
  // typescript: {
  //   ignoreBuildErrors: true
  // },
  // eslint: {
  //   ignoreDuringBuilds: true
  // },
};
```

Then incrementally fix type errors:
1. Fix one file at a time
2. Run `npm run type-check` after each fix
3. Commit working changes frequently

## CI/CD Best Practices

### GitHub Actions (Future)

Consider adding a GitHub Action for pre-deployment checks:

```yaml
# .github/workflows/validate.yml
name: Validate
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: npm install
      - run: npm run type-check
      - run: npm run lint
      - run: npm run build
```

## Summary

**Golden Rules:**
1. ✅ Always run `npm run pre-deploy` before pushing
2. ✅ Check `git status` before every commit
3. ✅ Never disable TypeScript checking permanently
4. ✅ Test production builds locally
5. ✅ Avoid Vercel-incompatible code (subprocess, file system writes)
6. ✅ Document all environment variables
7. ✅ Use feature flags for local vs serverless code

**Emergency Bypass (Last Resort):**
If you must deploy with errors:
```javascript
// next.config.js - TEMPORARY ONLY
typescript: { ignoreBuildErrors: true }
```
Create a TODO immediately to fix the errors.
