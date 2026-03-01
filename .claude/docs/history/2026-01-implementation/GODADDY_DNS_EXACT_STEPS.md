# GoDaddy DNS Update - Exact Steps

## Part 1: Get Vercel DNS Records

### **Step 1: Add Custom Domain in Vercel**

1. Go to your Vercel dashboard: https://vercel.com/dashboard
2. Click your project name (e.g., `compliance-engine`)
3. Click **"Settings"** (top navigation)
4. Click **"Domains"** (left sidebar)
5. Click **"Add Domain"** button
6. Type: `shiningarts.com.au`
7. Click **"Add"**

**Vercel will show you:**
```
⚠️ Invalid Configuration

To configure shiningarts.com.au, add the following records to your DNS provider:

Type  Name  Value
A     @     76.76.21.21
CNAME www   cname.vercel-dns.com
```

**⚠️ COPY THESE VALUES!** Your IP will be different - use YOUR values from Vercel!

---

## Part 2: Update GoDaddy DNS to Point to Vercel

### **Step 1: Login to GoDaddy**

1. Go to: https://www.godaddy.com
2. Click **"Sign In"** (top right)
3. Login with your credentials

### **Step 2: Open DNS Management**

1. Click **"My Products"** (top menu)
2. Find **"Domains"** section
3. Find `shiningarts.com.au`
4. Click **"DNS"** button next to it

You'll see a list of DNS records.

---

### **Step 3: Delete OLD Wix Records**

**Find and delete these (click trash icon):**

| Type | Name | Value | Action |
|------|------|-------|--------|
| A | @ | `185.230.63.107` | ❌ Delete |
| A | @ | `185.230.63.171` | ❌ Delete |
| A | @ | `185.230.63.186` | ❌ Delete |
| A | @ | `Parked` | ❌ Delete (if exists) |
| CNAME | www | `shiningarts.com.au` | ❌ Delete |
| CNAME | www | `cdn1.wixdns.net` | ❌ Delete (if exists) |
| CNAME | en | `cdn1.wixdns.net` | ❌ Delete (if not needed) |

**To delete:**
- Find the record
- Click trash icon on the right
- Confirm deletion

---

### **Step 4: Add NEW Vercel Records**

#### **Add A Record:**

1. Click **"Add"** button (top of DNS records)
2. Select **"A"** from Type dropdown
3. Fill in:
   - **Type:** A
   - **Name:** `@`
   - **Value:** `76.76.21.21` (use YOUR IP from Vercel Step 1!)
   - **TTL:** 1 Hour (or 600 seconds)
4. Click **"Save"**

#### **Add CNAME Record:**

1. Click **"Add"** button again
2. Select **"CNAME"** from Type dropdown
3. Fill in:
   - **Type:** CNAME
   - **Name:** `www`
   - **Value:** `cname.vercel-dns.com` (use YOUR value from Vercel!)
   - **TTL:** 1 Hour
4. Click **"Save"**

---

### **Step 5: KEEP Email Records (CRITICAL!)**

**⚠️ DO NOT DELETE THESE** - your email depends on them:

| Type | Name | Value | Priority | Keep? |
|------|------|-------|----------|-------|
| MX | @ | `mx1.privateemail.com` | 10 | ✅ KEEP |
| MX | @ | `mx2.privateemail.com` | 10 | ✅ KEEP |
| TXT | @ | `v=spf1 +ip4:66.29.141.42...` | - | ✅ KEEP |

**If these are missing, ADD THEM:**

**Add MX Record 1:**
- Click **"Add"** → Select **"MX"**
- Name: `@`
- Value: `mx1.privateemail.com`
- Priority: `10`
- TTL: 1 Hour
- Click **"Save"**

**Add MX Record 2:**
- Click **"Add"** → Select **"MX"**
- Name: `@`
- Value: `mx2.privateemail.com`
- Priority: `10`
- TTL: 1 Hour
- Click **"Save"**

**Add SPF TXT Record:**
- Click **"Add"** → Select **"TXT"**
- Name: `@`
- Value: `v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all`
- TTL: 1 Hour
- Click **"Save"**

---

### **Step 6: Verify DNS Changes**

After making changes, your DNS should look like:

**✅ Correct DNS Records:**
```
A     @    76.76.21.21                      (Vercel)
CNAME www  cname.vercel-dns.com             (Vercel)

MX    @    mx1.privateemail.com (Priority 10)  (Email)
MX    @    mx2.privateemail.com (Priority 10)  (Email)

TXT   @    v=spf1 +ip4:66.29.141.42...      (Email)
```

---

### **Step 7: Wait for DNS Propagation**

**Wait 15-30 minutes** for changes to take effect globally.

**Check propagation:**
1. Visit: https://dnschecker.org
2. Enter: `shiningarts.com.au`
3. Select: "A" record
4. Should show your Vercel IP globally

---

### **Step 8: Verify in Vercel**

1. Go back to Vercel → Your Project → Settings → Domains
2. You should see `shiningarts.com.au` with:
   - ✅ **Valid Configuration**
   - 🔒 SSL Certificate: Issuing... (takes 1-5 min)
   - 🔒 SSL Certificate: Active (when done)

---

## Part 3: Add Resend DNS Records

### **Step 1: Add Domain in Resend**

1. Go to: https://resend.com/domains
2. Click **"Add Domain"** button
3. Enter: `shiningarts.com.au`
4. Click **"Add"**

**Resend will show you 3 DNS records:**

```
Type   Name                 Value
TXT    @                    resend-domain-verification=abc123xyz...
CNAME  resend._domainkey    resend._domainkey.resend.com
TXT    _dmarc               v=DMARC1; p=none;
```

**⚠️ COPY THESE VALUES!** Each domain gets unique values.

---

### **Step 2: Add Resend Records to GoDaddy**

**Go back to:** GoDaddy → Domains → shiningarts.com.au → DNS

#### **Record 1: Domain Verification (TXT)**

1. Click **"Add"**
2. Select **"TXT"**
3. Fill in:
   - **Type:** TXT
   - **Name:** `@`
   - **Value:** `resend-domain-verification=abc123xyz...` (your value from Resend)
   - **TTL:** 1 Hour
4. Click **"Save"**

**⚠️ If you get error "TXT record already exists for @":**
- You already have the SPF TXT record
- GoDaddy allows multiple TXT records for same name
- Just save it anyway - it should work
- Or, click **"Add New Record"** again and try

#### **Record 2: DKIM (CNAME)**

1. Click **"Add"**
2. Select **"CNAME"**
3. Fill in:
   - **Type:** CNAME
   - **Name:** `resend._domainkey`
   - **Value:** `resend._domainkey.resend.com`
   - **TTL:** 1 Hour
4. Click **"Save"**

#### **Record 3: DMARC (TXT)**

**Check if you already have `_dmarc` record:**
- Look for: `TXT _dmarc v=DMARC1; p=quarantine...`
- If it exists → Edit it
- If not → Add new

**If _dmarc EXISTS:**
1. Find `TXT _dmarc ...`
2. Click **Edit** (pencil icon)
3. Change Value to: `v=DMARC1; p=none;`
4. Click **"Save"**

**If _dmarc DOES NOT EXIST:**
1. Click **"Add"**
2. Select **"TXT"**
3. Fill in:
   - **Type:** TXT
   - **Name:** `_dmarc`
   - **Value:** `v=DMARC1; p=none;`
   - **TTL:** 1 Hour
4. Click **"Save"**

---

### **Step 3: Wait for Resend Verification**

**Wait 5-30 minutes** for DNS propagation.

**Check Resend:**
1. Go back to: https://resend.com/domains
2. Look for `shiningarts.com.au`
3. Should see **green checkmark** ✅ "Verified"
4. If not, click **"Verify"** button to force check

---

## Final DNS Summary

Your GoDaddy DNS should have:

```
=== WEBSITE (Vercel) ===
A     @                    76.76.21.21 (your Vercel IP)
CNAME www                  cname.vercel-dns.com

=== EMAIL (Namecheap Private Email) ===
MX    @                    mx1.privateemail.com (Priority 10)
MX    @                    mx2.privateemail.com (Priority 10)
TXT   @                    v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all

=== EMAIL SENDING (Resend) ===
TXT   @                    resend-domain-verification=...
CNAME resend._domainkey    resend._domainkey.resend.com
TXT   _dmarc               v=DMARC1; p=none;

=== SYSTEM (GoDaddy - don't touch) ===
NS    @                    ns01.domaincontrol.com
NS    @                    ns02.domaincontrol.com
SOA   @                    Primary nameserver: ns01.domaincontrol.com
```

---

## Testing Checklist

### **After 30 minutes, test:**

**✅ Website:**
- Visit: https://shiningarts.com.au
- Should load Vercel site (not Wix!)
- Should have 🔒 SSL/HTTPS

**✅ www subdomain:**
- Visit: https://www.shiningarts.com.au
- Should redirect or load same site

**✅ Email receiving:**
- Send test email to: info@shiningarts.com.au
- Check inbox (Namecheap webmail)
- Should receive it

**✅ Email sending (Resend):**
- Resend dashboard shows ✅ green checkmark
- Ready to send emails via Resend API

**✅ Feedback form:**
- Visit: https://shiningarts.com.au/assessment
- Submit HIGH severity feedback
- Check info@shiningarts.com.au inbox
- Should receive email from Resend

---

## Troubleshooting

### "DNS not updating"
- Wait longer (up to 48 hours, usually 30 min)
- Clear browser cache: Ctrl+Shift+Delete
- Check: https://dnschecker.org

### "Website shows Wix"
- Old DNS cached - wait 1 hour
- Make sure you deleted ALL Wix A records
- Verify A record points to Vercel IP

### "Email stopped working"
- Check MX records are present
- Verify mx1 and mx2.privateemail.com
- Both should have Priority 10

### "Resend not verifying"
- Check all 3 records added correctly
- No extra spaces in values
- Wait 30 min and click "Verify" button
- Check: https://mxtoolbox.com/SuperTool.aspx

### "Can't add multiple TXT records for @"
- GoDaddy allows it - click Add again
- Or combine values (not recommended)
- Or contact GoDaddy support

---

## Quick Reference

**GoDaddy DNS:** https://dcc.godaddy.com/manage/shiningarts.com.au/dns

**Vercel Domains:** https://vercel.com/dashboard → Your Project → Settings → Domains

**Resend Domains:** https://resend.com/domains

**DNS Checker:** https://dnschecker.org

**MX Toolbox:** https://mxtoolbox.com

---

**Estimated Time:**
- Add Vercel records: 5 minutes
- Add Resend records: 5 minutes
- DNS propagation: 15-30 minutes
- Testing: 5 minutes
- **Total: ~45 minutes**
