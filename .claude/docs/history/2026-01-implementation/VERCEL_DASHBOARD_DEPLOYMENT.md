# Deploy to Vercel via Dashboard (No CLI Needed)

## 🚀 Step-by-Step Dashboard Deployment

### **Step 1: Go to Vercel Dashboard**

1. Open browser: https://vercel.com/login
2. Login with GitHub (or your account)
3. You'll land on: https://vercel.com/dashboard

---

### **Step 2: Import Your Project**

**Option A: If code is on GitHub (recommended)**

1. Click **"Add New..."** → **"Project"**
2. Click **"Import Git Repository"**
3. Find your repo or click **"Import from URL"**
4. Paste GitHub repo URL (if you have one)

**Option B: If code is NOT on GitHub (use this)**

1. First, push code to GitHub:

```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Initialize git
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/compliance-engine.git
git branch -M main
git push -u origin main
```

2. Then import from GitHub in Vercel

---

### **Step 3: Configure Project Settings**

When importing, Vercel will ask:

**Project Name:**
- Use: `nsw-planning-engine` (or keep default)

**Framework Preset:**
- Should auto-detect: **Next.js** ✅
- If not, select: Next.js

**Root Directory:**
- Click **"Edit"**
- Set to: `frontend-nextjs`
- ⚠️ **IMPORTANT:** Your Next.js app is in the `frontend-nextjs` folder!

**Build Settings:**
- Build Command: `npm run build` (auto-detected)
- Output Directory: `.next` (auto-detected)
- Install Command: `npm ci` (auto-detected)

---

### **Step 4: Add Environment Variables**

**BEFORE clicking Deploy**, click **"Environment Variables"** section.

Add each of these (copy from `.env.local`):

```bash
# Google Maps API
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyCi5UBAg6X-k6W8v1vv9XEQaML9aQE-w60

# Email - Resend
RESEND_API_KEY=re_DFTPtLtp_GnvQAq73cvsBvFCNyxjsB3o6
ADMIN_EMAIL=info@shiningarts.com.au

# AI APIs
ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
OPENAI_API_KEY=<OPENAI_API_KEY>
DEEPSEEK_API_KEY=sk-ec1634592f8a432bb51382a674aa69e7
GEMINI_API_KEY=AIzaSyA2oczqAd3-X2sKlRQ2P-UM-xf_Z0gyfgU

# TfNSW Traffic API
TFNSW_API_KEY=<TFNSW_API_KEY>

# Analytics
NEXT_PUBLIC_POSTHOG_KEY=phc_BwmI39jDeaLPEKYsjMvphVuz6rCfIYxD592NCU0GmrQ

# Feature Flags
ENABLE_PRECINCT_MATCHING=true
NEXT_PUBLIC_ENABLE_PRECINCT_CONTROLS=true
USE_POSTGRESQL_PROVISIONS=true
USE_POSTGRESQL_LIVE_CHECK=true
USE_POSTGRESQL_VERSIONS=true
USE_POSTGRESQL_TOD_RATES=true
USE_POSTGRESQL_VERSION_COMPLIANCE=true
USE_DIRECT_DATABASE=true
COMPLIANCE_ARCHITECTURE=direct_database

# Database - OPTION A: Supabase (recommended)
# Get these from Supabase dashboard after creating project
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST].supabase.co:5432/postgres
DATABASE_HOST=[HOST].supabase.co
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=postgres
DATABASE_PASSWORD=[YOUR_SUPABASE_PASSWORD]

PGHOST=[HOST].supabase.co
PGDATABASE=postgres
PGUSER=postgres
PGPASSWORD=[YOUR_SUPABASE_PASSWORD]
PGPORT=5432

DB_HOST=[HOST].supabase.co
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=[YOUR_SUPABASE_PASSWORD]
DB_PORT=5432
DB_POOL_MIN=2
DB_POOL_MAX=20
DB_IDLE_TIMEOUT=30000
DB_CONNECTION_TIMEOUT=2000
```

**⚠️ Database Note:**
- Your current database is localhost (won't work on Vercel)
- You need to either:
  1. **Create Supabase project** (recommended - free tier)
  2. **Use Vercel Postgres** (paid)
  3. **Skip database for now** (site deploys but searches won't work)

**For Supabase:**
1. Go to https://supabase.com → Create project
2. Wait 2 min for setup
3. Settings → Database → Copy connection string
4. Replace `[HOST]` and `[PASSWORD]` in env vars above

---

### **Step 5: Deploy**

1. Review settings one more time:
   - ✅ Root Directory: `frontend-nextjs`
   - ✅ Framework: Next.js
   - ✅ Environment variables added

2. Click **"Deploy"**

**Build will take 2-5 minutes.**

You'll see:
- Uploading files...
- Building...
- Deploying...

---

### **Step 6: Get Your Vercel URL**

Once deployment succeeds:

1. You'll get a URL like:
   ```
   https://nsw-planning-engine.vercel.app
   ```

2. Click **"Visit"** to test it

3. Try navigating to:
   ```
   https://nsw-planning-engine.vercel.app/assessment
   ```

**If it loads** → Success! ✅

---

### **Step 7: Add Custom Domain**

Now connect `shiningarts.com.au`:

1. In Vercel project → **Settings** → **Domains**
2. Click **"Add Domain"**
3. Enter: `shiningarts.com.au`
4. Click **"Add"**

Vercel will show:

```
⚠️ Invalid Configuration
Add the following records to your DNS provider:

A     @     76.76.21.21
CNAME www   cname.vercel-dns.com
```

**Copy these values** - you'll add them to GoDaddy next.

**Note:** The IP address will be different - use YOUR values from Vercel!

---

### **Step 8: Update GoDaddy DNS**

**Go to: GoDaddy → Domains → shiningarts.com.au → Manage DNS**

#### **8.1 Delete Wix Records:**

Find and delete:
- ❌ `A @ 185.230.63.107`
- ❌ `A @ 185.230.63.171`
- ❌ `A @ 185.230.63.186`
- ❌ `A @ Parked`
- ❌ `CNAME www shiningarts.com.au` (or any pointing to Wix)
- ❌ `CNAME en cdn1.wixdns.net` (unless you need en subdomain)

#### **8.2 Add Vercel Records:**

Click **"Add"** for each:

| Type | Name | Value (from Vercel Step 7) | TTL |
|------|------|---------------------------|-----|
| A | @ | `76.76.21.21` | 1 Hour |
| CNAME | www | `cname.vercel-dns.com` | 1 Hour |

**⚠️ Use YOUR actual Vercel values!**

#### **8.3 Keep Email Records (CRITICAL):**

**DO NOT DELETE THESE** - your email depends on them:

```
✅ MX @ mx1.privateemail.com (Priority 10)
✅ MX @ mx2.privateemail.com (Priority 10)
✅ TXT @ v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all
```

**If missing, add them back!**

---

### **Step 9: Add Resend DNS Records**

1. **Resend Dashboard:** https://resend.com/domains
2. Click **"Add Domain"**
3. Enter: `shiningarts.com.au`
4. Resend shows 3 DNS records

**Add to GoDaddy:**

| Type | Name | Value (from Resend) | TTL |
|------|------|---------------------|-----|
| TXT | @ | `resend-domain-verification=abc123...` | 1 Hour |
| CNAME | resend._domainkey | `resend._domainkey.resend.com` | 1 Hour |
| TXT | _dmarc | `v=DMARC1; p=none;` | 1 Hour |

**If _dmarc already exists:**
- Edit it to: `v=DMARC1; p=none;`

**If @ TXT already has SPF:**
- GoDaddy allows multiple TXT records
- Add Resend verification as separate TXT record

---

### **Step 10: Wait & Verify**

**Wait 15-30 minutes** for DNS propagation.

**Check DNS:**
- Visit: https://dnschecker.org
- Search: `shiningarts.com.au`
- Should show Vercel A record globally

**Check Vercel:**
- Go to Vercel → Domains
- Should show: **"Valid Configuration"** ✅
- SSL certificate issued automatically

**Check Resend:**
- Go to Resend → Domains
- Should show: **Green checkmark** ✅

---

### **Step 11: Test Everything**

#### **Website:**
```
✅ https://shiningarts.com.au
✅ https://www.shiningarts.com.au
✅ https://shiningarts.com.au/assessment
```

Should all load your Next.js app (not Wix!)

#### **Email Receiving:**
- Send email to: `info@shiningarts.com.au`
- Check Namecheap webmail
- Should receive it

#### **Feedback Form (Email Sending):**
1. Go to: https://shiningarts.com.au/assessment
2. Enter an address
3. Click feedback widget (bottom right)
4. Fill form with **HIGH** severity
5. Submit
6. Check `info@shiningarts.com.au` inbox
7. Should get email from Resend

---

## ✅ Success Checklist

```
[ ] Created/Logged into Vercel account
[ ] Imported project (from GitHub or uploaded)
[ ] Set Root Directory to: frontend-nextjs
[ ] Added all environment variables
[ ] Deployed successfully
[ ] Got Vercel URL working
[ ] Added custom domain in Vercel
[ ] Got Vercel DNS records (A + CNAME)
[ ] Deleted Wix records from GoDaddy
[ ] Added Vercel records to GoDaddy
[ ] Kept MX records for email
[ ] Added Resend domain
[ ] Added Resend DNS records to GoDaddy
[ ] Waited 30 min for DNS
[ ] Domain shows Valid in Vercel
[ ] Resend shows green checkmark
[ ] Website loads on custom domain
[ ] SSL certificate working (https)
[ ] Email receiving works
[ ] Feedback form sends emails
[ ] Ready to delete Wix!
```

---

## 🚨 Common Issues

### "Build Failed - TypeScript Errors"
- Check build logs in Vercel
- May need to fix TS errors in code
- Or add to `next.config.js`: `typescript: { ignoreBuildErrors: true }`

### "Database Connection Failed"
- Localhost doesn't work on Vercel
- Create Supabase project
- Add Supabase connection string to env vars
- Redeploy

### "Domain Not Verifying"
- Wait 30-60 min for DNS
- Check https://dnschecker.org
- Verify A record points to Vercel IP
- Clear browser cache

### "Email Not Sending"
- Check env vars: `RESEND_API_KEY`, `ADMIN_EMAIL`
- Check Resend domain verified
- Submit HIGH severity feedback (only high triggers email)
- Check Resend logs for errors

### "Root Directory Error"
- Make sure Root Directory is set to: `frontend-nextjs`
- Project Settings → General → Root Directory

---

## 🎯 Quick Start

**If you want to skip CLI completely:**

1. **Push to GitHub** (if not already)
2. **Go to Vercel:** https://vercel.com/new
3. **Import from GitHub**
4. **Set Root Directory:** `frontend-nextjs`
5. **Add env vars** (copy from above)
6. **Deploy**
7. **Add domain** → Get DNS records
8. **Update GoDaddy** → Point to Vercel
9. **Add Resend** → Add DNS records
10. **Test & celebrate!** 🎉

---

**Current Status:** Ready to deploy via dashboard
**Estimated Time:** 30 minutes active work + 30 min DNS wait
**Difficulty:** Easy (just follow the steps)
