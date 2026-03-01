# Email Form Independent of Wix - Complete Setup

## 🎯 Goal: Email Form Works Without Wix

Your feedback form will send emails using:
- **Resend** for sending (already configured in code)
- **Namecheap Private Email** for receiving (info@shiningarts.com.au)
- **Zero dependency on Wix**

---

## Current Situation

✅ **Already Done:**
- Resend SDK installed
- API key saved: `re_DFTPtLtp_GnvQAq73cvsBvFCNyxjsB3o6`
- Code updated to send emails via Resend
- Domain at GoDaddy (not Wix)

❌ **Still Wix-Dependent:**
- Website DNS points to Wix servers
- You want to delete Wix entirely

---

## 🔥 Complete Wix Removal Plan

### **Option A: Deploy to Vercel + Keep Email** (Recommended)

**What this does:**
- Your Next.js app runs on Vercel (not Wix)
- Feedback form sends emails via Resend
- You receive emails via Namecheap Private Email
- Delete Wix entirely

**Requirements:**
- Vercel account (free tier works)
- 30 minutes setup time

---

## Step 1: Deploy Next.js App to Vercel

### **1.1 Push Code to GitHub (if not already)**

```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Initialize git if needed
git init
git add .
git commit -m "Initial commit - NSW Planning Engine"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/nsw-planning-engine.git
git branch -M main
git push -u origin main
```

### **1.2 Deploy to Vercel**

1. Go to: https://vercel.com/signup
2. Sign in with GitHub
3. Click **"Add New Project"**
4. Import your GitHub repo
5. Configure:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `frontend-nextjs`
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`

6. **Add Environment Variables** (CRITICAL):

Click **"Environment Variables"** and add:

```bash
# Google Maps
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyCi5UBAg6X-k6W8v1vv9XEQaML9aQE-w60

# Database (Supabase or your PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
PGHOST=your-db-host
PGDATABASE=nsw_planning
PGUSER=postgres
PGPASSWORD=your-password
PGPORT=5432

# Email
RESEND_API_KEY=re_DFTPtLtp_GnvQAq73cvsBvFCNyxjsB3o6
ADMIN_EMAIL=info@shiningarts.com.au

# Other APIs
ANTHROPIC_API_KEY=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
OPENAI_API_KEY=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
```

7. Click **"Deploy"**

**Wait 2-5 minutes** for build to complete.

You'll get a URL like: `https://nsw-planning-engine.vercel.app`

---

## Step 2: Point Domain to Vercel (Not Wix!)

### **2.1 Get Vercel DNS Records**

1. In Vercel dashboard → Your project → **Settings** → **Domains**
2. Click **"Add Domain"**
3. Enter: `shiningarts.com.au`
4. Vercel will show you DNS records to add

**Example Vercel records:**
```
A     @     76.76.21.21
CNAME www   cname.vercel-dns.com
```

### **2.2 Update GoDaddy DNS**

**Go to GoDaddy → Manage DNS**

#### **Delete Wix Records:**
- ❌ Delete: `A @ 185.230.63.107`
- ❌ Delete: `A @ 185.230.63.171`
- ❌ Delete: `A @ 185.230.63.186`
- ❌ Delete: `CNAME www shiningarts.com.au` (or whatever Wix CNAME)
- ❌ Delete: `CNAME en cdn1.wixdns.net` (if not needed)

#### **Add Vercel Records:**
Use the exact values Vercel gave you:

| Type | Name | Value (from Vercel) | TTL |
|------|------|---------------------|-----|
| A | @ | `76.76.21.21` | 1 Hour |
| CNAME | www | `cname.vercel-dns.com` | 1 Hour |

**⚠️ Use YOUR actual Vercel values** - these are examples!

---

## Step 3: Keep Email Working (Namecheap Private Email)

Your MX records in GoDaddy DNS **must stay**:

```
MX @ mx1.privateemail.com (Priority 10)
MX @ mx2.privateemail.com (Priority 10)
```

**⚠️ Do NOT delete these!** These handle `info@shiningarts.com.au`

If they're missing, add them:

| Type | Name | Value | Priority | TTL |
|------|------|-------|----------|-----|
| MX | @ | `mx1.privateemail.com` | 10 | 1 Hour |
| MX | @ | `mx2.privateemail.com` | 10 | 1 Hour |

---

## Step 4: Add Resend DNS Records

**Same as before**, but now with Vercel hosting:

1. **Resend Dashboard** → Add domain → `shiningarts.com.au`
2. **Copy 3 DNS records** Resend gives you
3. **Add to GoDaddy DNS**:

| Type | Name | Value (from Resend) |
|------|------|---------------------|
| TXT | @ | `resend-domain-verification=...` |
| CNAME | resend._domainkey | `resend._domainkey.resend.com` |
| TXT | _dmarc | `v=DMARC1; p=none;` |

**Note:** If you already have `_dmarc`, edit it to `v=DMARC1; p=none;`

---

## Step 5: Verify Everything Works

### **Website (Vercel):**
- Visit: https://shiningarts.com.au
- Should show your Next.js app (NOT Wix!)
- Should load `/assessment` page

### **Email Receiving (Namecheap):**
- Send test email to: `info@shiningarts.com.au`
- Check inbox in Namecheap webmail
- Should receive it

### **Email Sending (Resend):**
1. Visit: https://shiningarts.com.au/assessment
2. Submit **HIGH** severity feedback
3. Check `info@shiningarts.com.au` inbox
4. Should receive email from Resend

---

## Final GoDaddy DNS Should Look Like

```
A RECORDS (Vercel):
@ → 76.76.21.21 (Vercel IP - get from Vercel)

CNAME RECORDS (Vercel):
www → cname.vercel-dns.com (Vercel CNAME - get from Vercel)

MX RECORDS (Namecheap Email):
@ → mx1.privateemail.com (Priority 10)
@ → mx2.privateemail.com (Priority 10)

TXT RECORDS (Email Auth + Resend):
@ → v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all
@ → resend-domain-verification=... (from Resend)
_dmarc → v=DMARC1; p=none;

CNAME RECORDS (Resend):
resend._domainkey → resend._domainkey.resend.com

NS RECORDS (GoDaddy - don't touch):
@ → ns01.domaincontrol.com
@ → ns02.domaincontrol.com
```

**NO WIX RECORDS!** All deleted.

---

## What Happens After You Delete Wix

### ✅ **Will Still Work:**
- Website (runs on Vercel)
- Email sending (Resend)
- Email receiving (Namecheap)
- Database (Supabase/PostgreSQL)
- All app functionality

### ❌ **Will Break:**
- Nothing! (if DNS is configured correctly)

---

## Database Consideration

**Check your database location:**

```bash
# In .env.local
DATABASE_URL=postgresql://postgres:Onlyme123!@127.0.0.1:5432/nsw_planning
```

**127.0.0.1 = localhost** - This won't work on Vercel!

### **Options:**

**Option 1: Use Supabase (Recommended)**
1. Go to https://supabase.com
2. Create free project
3. Get connection string
4. Update Vercel env vars with Supabase URL

**Option 2: Use Vercel Postgres**
1. Vercel dashboard → Storage → Create Postgres
2. Migrate your data
3. Vercel auto-configures connection

**Option 3: Use Railway/Render Postgres**
- Railway.app or Render.com
- Deploy PostgreSQL
- Get connection string
- Update Vercel env vars

---

## Quick Migration Checklist

```
[ ] 1. Push code to GitHub
[ ] 2. Deploy to Vercel (vercel.com)
[ ] 3. Add all environment variables in Vercel
[ ] 4. Get Vercel DNS records (A + CNAME)
[ ] 5. Delete Wix A records in GoDaddy
[ ] 6. Delete Wix CNAME records in GoDaddy
[ ] 7. Add Vercel A record in GoDaddy
[ ] 8. Add Vercel CNAME in GoDaddy
[ ] 9. Verify MX records still exist (Namecheap email)
[ ] 10. Add Resend domain verification
[ ] 11. Add Resend DNS records to GoDaddy
[ ] 12. Wait 30 min for DNS propagation
[ ] 13. Test website loads on shiningarts.com.au
[ ] 14. Test email receiving (send to info@)
[ ] 15. Test feedback form (submit HIGH severity)
[ ] 16. Delete Wix account
```

---

## Troubleshooting

### "Database connection failed on Vercel"
→ Your DB is on `127.0.0.1` (localhost). Deploy database to Supabase/Railway/Vercel Postgres.

### "Email not sending after Vercel deploy"
→ Check Vercel env vars have `RESEND_API_KEY` and `ADMIN_EMAIL`

### "Website not loading after DNS change"
→ Wait 30-60 min for DNS propagation. Clear browser cache.

### "Can't delete Wix - domain is connected"
→ First disconnect domain in Wix dashboard, then delete site

---

## Timeline

- **Vercel Deploy:** 10 min (code upload + build)
- **DNS Update:** 5 min (change GoDaddy records)
- **DNS Propagation:** 30-60 min (waiting)
- **Resend Setup:** 5 min
- **Testing:** 10 min
- **Delete Wix:** 2 min

**Total:** ~1.5 hours (mostly waiting for DNS)

---

## Summary

**After this setup:**
- ✅ Website hosted on **Vercel** (not Wix)
- ✅ Email sending via **Resend** (not Wix)
- ✅ Email receiving via **Namecheap Private Email** (not Wix)
- ✅ Database on **Supabase/Vercel/Railway** (not Wix)
- ✅ DNS managed by **GoDaddy** (not Wix)
- ✅ **Zero Wix dependency** - safe to delete account

**Your feedback form will work completely independently of Wix.**

Ready to start? Begin with Step 1 (Vercel deployment).
