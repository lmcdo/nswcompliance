# GoDaddy DNS Migration - Exact Records for shiningarts.com.au

## ✅ Current Wix DNS Records (Copy These to GoDaddy)

I've extracted your exact Wix DNS records. Follow the steps below to migrate without breaking anything.

---

## Step 1: Switch Nameservers in GoDaddy

1. Login to **GoDaddy**: https://www.godaddy.com
2. Go to **My Products** → **Domains** → Click `shiningarts.com.au`
3. Find **Nameservers** section → Click **"Change"**
4. Select **"Use GoDaddy nameservers"** (Default)
5. Click **"Save"**

**Wait 5-30 minutes** before proceeding to Step 2.

---

## Step 2: Add ALL DNS Records to GoDaddy

Once nameservers are switched, go to **GoDaddy** → `shiningarts.com.au` → **Manage DNS**

Click **"Add"** for each record below:

---

### **A Records (Website Hosting - 3 records)**

Add these **3 separate A records**:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | `185.230.63.171` | 1 Hour |
| A | @ | `185.230.63.186` | 1 Hour |
| A | @ | `185.230.63.107` | 1 Hour |

**Note:** GoDaddy supports multiple A records for the same host. Add each one separately.

---

### **CNAME Records (2 records)**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | en | `cdn1.wixdns.net` | 1 Hour |
| CNAME | www | `cdn1.wixdns.net` | 1 Hour |

**Note:**
- `en` is for en.shiningarts.com.au
- `www` is for www.shiningarts.com.au

---

### **MX Records (Email - 2 records)** ✉️

**CRITICAL:** These handle your `info@shiningarts.com.au` email!

| Type | Name | Value | Priority | TTL |
|------|------|-------|----------|-----|
| MX | @ | `mx1.privateemail.com` | 10 | 1 Hour |
| MX | @ | `mx2.privateemail.com` | 10 | 1 Hour |

**⚠️ Important:**
- These point to Namecheap Private Email (privateemail.com)
- Without these, your email will stop working!
- Priority = 10 for both

---

### **TXT Record (SPF - Email Authentication)**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| TXT | @ | `v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all` | 1 Hour |

**Purpose:** Allows your email server to send emails from your domain.

---

## Step 3: Verify Everything Works

After adding all records, wait **15-30 minutes**, then test:

### **Website:**
- ✅ https://shiningarts.com.au (should load)
- ✅ https://www.shiningarts.com.au (should load)
- ✅ https://en.shiningarts.com.au (should load if used)

### **Email:**
- ✅ Send test email from `info@shiningarts.com.au`
- ✅ Receive test email to `info@shiningarts.com.au`
- ⚠️ If email fails, double-check MX records!

**Check DNS Propagation:**
- Visit: https://dnschecker.org
- Enter: `shiningarts.com.au`
- Select record type (A, MX, etc.)
- Should show your new GoDaddy nameservers

---

## Step 4: Add Resend DNS Records

**Only proceed once website and email are working!**

1. Go to **Resend Dashboard**: https://resend.com/domains
2. Click **"Add Domain"**
3. Enter: `shiningarts.com.au`
4. Click **"Add"**

Resend will show you 3 DNS records to add. **Example:**

```
TXT    @                  resend-domain-verification=abc123...
CNAME  resend._domainkey  resend._domainkey.resend.com
TXT    _dmarc             v=DMARC1; p=none;
```

### **Add to GoDaddy DNS:**

Go back to GoDaddy → Manage DNS → Add each:

| Type | Name | Value (from Resend) | TTL |
|------|------|---------------------|-----|
| TXT | @ | `resend-domain-verification=...` | 1 Hour |
| CNAME | resend._domainkey | `resend._domainkey.resend.com` | 1 Hour |
| TXT | _dmarc | `v=DMARC1; p=none;` | 1 Hour |

**Note:** Copy the **exact** values from your Resend dashboard.

---

## Step 5: Verify Resend Domain

1. Wait **5-30 minutes** for DNS propagation
2. Go to Resend → Domains
3. You should see a **green checkmark** next to `shiningarts.com.au`
4. If not verified after 30 minutes, click **"Verify"** button

---

## Step 6: Test Email Notifications

1. **Start dev server:**
   ```bash
   cd frontend-nextjs
   npm run dev
   ```

2. **Open browser:** http://localhost:3000/assessment

3. **Submit high-severity feedback:**
   - Enter an address
   - Click feedback widget (bottom right)
   - Fill form:
     - Type: "Data Accuracy Issue"
     - Severity: **HIGH** ⚠️
     - Description: "Test email notification"
     - Email: (optional)
   - Click **Submit**

4. **Check inbox:** `info@shiningarts.com.au`
   - Subject: `🚨 High Priority Feedback: ...`
   - From: `NSW Planning Engine <noreply@shiningarts.com.au>`

5. **Check server console:**
   ```
   High priority feedback email sent to: info@shiningarts.com.au
   ```

---

## Complete DNS Record Summary (for GoDaddy)

Here's everything you need to add:

```
A RECORDS (3):
@ → 185.230.63.171
@ → 185.230.63.186
@ → 185.230.63.107

CNAME RECORDS (2):
en → cdn1.wixdns.net
www → cdn1.wixdns.net

MX RECORDS (2):
@ → mx1.privateemail.com (Priority: 10)
@ → mx2.privateemail.com (Priority: 10)

TXT RECORDS (1 now, +3 after Resend):
@ → v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all

RESEND RECORDS (add after Step 4):
@ → resend-domain-verification=... (TXT)
resend._domainkey → resend._domainkey.resend.com (CNAME)
_dmarc → v=DMARC1; p=none; (TXT)
```

---

## ⚠️ Critical Notes

1. **Don't skip MX records** - Your email will break without them!
2. **Wait between steps** - DNS takes time to propagate
3. **Test before moving on** - Verify website/email work before adding Resend
4. **Keep this document** - You may need to reference these values

---

## Troubleshooting

### Website not loading after migration?
- Wait longer (DNS can take up to 48 hours, usually 30 mins)
- Clear browser cache: Ctrl+Shift+Delete
- Check DNS propagation: https://dnschecker.org
- Verify A records are correct in GoDaddy

### Email not working?
- Check MX records in GoDaddy DNS manager
- Verify both `mx1.privateemail.com` and `mx2.privateemail.com` are added
- Priority should be `10` for both
- Wait 1 hour for MX record propagation

### Resend not verifying?
- Check TXT records are added correctly
- No spaces or quotes around values
- Wait 30 minutes
- Use DNS checker to verify records visible globally

### Email notifications not sending?
1. Check `.env.local` has:
   - `RESEND_API_KEY=re_DFTPtLtp_GnvQAq73cvsBvFCNyxjsB3o6`
   - `ADMIN_EMAIL=info@shiningarts.com.au`
2. Check Resend domain has green checkmark
3. Check Resend **Logs** section for error messages
4. Verify you're submitting **HIGH** severity feedback (only high severity triggers email)
5. Check spam folder

---

## Next Steps After Migration

Once everything works:

1. ✅ Website loads on shiningarts.com.au
2. ✅ Email sending/receiving works
3. ✅ Resend domain verified (green checkmark)
4. ✅ Test email received in inbox

**Then you're done!** The feedback form will automatically send emails to `info@shiningarts.com.au` for all high-priority feedback submissions.

---

**Status:** Ready to migrate
**Estimated Time:** 30-60 minutes (mostly waiting for DNS)
**Risk Level:** Low (all records documented, can rollback to Wix if needed)
