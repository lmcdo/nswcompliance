# Quick Deployment Guide

## Before Every Deployment

```bash
cd frontend-nextjs

# 1. Check for untracked files
git status

# 2. Run validation
npm run pre-deploy

# 3. Commit changes
git add .
git commit -m "your message"
git push
```

## If Pre-Deploy Fails

### TypeScript Errors
```bash
npm run type-check
# Fix errors, then re-run
```

### Build Errors
```bash
npm run build
# Check error message and fix
```

### Lint Errors
```bash
npm run lint
```

## Common Gotchas

❌ **Don't do this:**
- Push without running `git status`
- Ignore TypeScript errors
- Use `child_process.spawn()` for Python
- Commit without testing build

✅ **Do this:**
- Run `npm run pre-deploy` before pushing
- Fix type errors immediately
- Use PostgreSQL instead of subprocess
- Test locally first

## Emergency Deploy (If Build Fails)

Only if absolutely necessary:

1. Check deployment logs: https://vercel.com/lawrence-mcdonells-projects/compliance-engine
2. Temporarily disable type checking (see DEPLOYMENT_BEST_PRACTICES.md)
3. Create TODO to fix errors ASAP

## Useful Commands

```bash
# Test production build locally
npm run build

# Type check without building
npm run type-check

# Check Vercel deployment status
vercel ls

# View deployment logs
vercel logs [deployment-url]
```

## Environment Variables

Verify these are set in Vercel dashboard:
- PGHOST
- PGDATABASE
- PGUSER
- PGPASSWORD
- PGPORT
- NODE_ENV

Dashboard: https://vercel.com/lawrence-mcdonells-projects/compliance-engine/settings/environment-variables
