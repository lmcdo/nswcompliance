# CRITICAL: Check Your Vercel Environment Variables

Go to: https://vercel.com/lawrence-mcdonells-projects/compliance-engine/settings/environment-variables

You MUST verify these exact values:

## Required for Vercel (Serverless):
```
PGHOST=aws-0-ap-southeast-2.pooler.supabase.com
PGPORT=6543
PGDATABASE=postgres
PGUSER=postgres.zvvqcxetdkhjnpygcrjp
PGPASSWORD=[your password]
```

## Common Mistakes:
❌ Using aws-1 instead of aws-0
❌ Using port 5432 instead of 6543
❌ Using "nsw_planning" database instead of "postgres"
❌ Wrong user format

The "Tenant or user not found" error means ONE of these is wrong.

Please check and paste:
1. What is your PGHOST? (should be aws-0...)
2. What is your PGPORT? (should be 6543)
3. What is your PGDATABASE? (should be postgres)
4. What is your PGUSER? (should be postgres.zvvqcxetdkhjnpygcrjp)
