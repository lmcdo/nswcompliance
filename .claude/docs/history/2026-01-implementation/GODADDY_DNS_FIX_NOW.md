# GoDaddy DNS - Fix Issues & Add Resend

## 🔍 Problems Found in Your Current GoDaddy DNS

### ✅ Already Correct:
- 3 A Records (185.230.63.171, .186, .107) ✅
- CNAME en → cdn1.wixdns.net ✅
- NS records (GoDaddy nameservers) ✅

### ❌ Issues to Fix:

1. **Wrong CNAME for www** ❌
   - Current: `www → shiningarts.com.au` (points to itself - loop!)
   - Should be: `www → cdn1.wixdns.net`

2. **Parked A Record** ❌
   - Delete: `@ → Parked` (GoDaddy placeholder)

3. **Missing MX Records** ❌ (Your email won't work!)
   - Need: `mx1.privateemail.com` and `mx2.privateemail.com`

4. **Missing SPF TXT Record** ❌ (Email authentication)
   - Need: `v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all`

5. **DMARC Conflict** ⚠️
   - Current: GoDaddy's DMARC (`p=quarantine`)
   - Resend needs: `p=none`
   - **This is blocking Resend's TXT record**

---

## 🛠️ Step-by-Step Fixes

### **Fix 1: Delete Parked A Record**

1. Find the row: `A @ Parked`
2. Click **Delete** (trash icon)
3. Confirm deletion

---

### **Fix 2: Fix www CNAME**

1. Find the row: `CNAME www shiningarts.com.au`
2. Click **Edit** (pencil icon)
3. Change **Data** from `shiningarts.com.au` to `cdn1.wixdns.net`
4. Click **Save**

**Result:** `www → cdn1.wixdns.net` (same as Wix)

---

### **Fix 3: Add MX Records (Critical for Email!)**

Click **"Add"** → Select **"MX"**

**First MX Record:**
- Type: `MX`
- Name: `@`
- Data/Value: `mx1.privateemail.com`
- Priority: `10`
- TTL: `1 Hour`
- Click **Save**

**Second MX Record:**
- Click **"Add"** again → Select **"MX"**
- Type: `MX`
- Name: `@`
- Data/Value: `mx2.privateemail.com`
- Priority: `10`
- TTL: `1 Hour`
- Click **Save**

**⚠️ Without these, `info@shiningarts.com.au` will not work!**

---

### **Fix 4: Add SPF TXT Record**

Click **"Add"** → Select **"TXT"**

- Type: `TXT`
- Name: `@`
- Data/Value: `v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all`
- TTL: `1 Hour`
- Click **Save**

**Purpose:** Allows your email server to send emails from your domain

---

### **Fix 5: Replace DMARC Record for Resend**

**GoDaddy is blocking Resend because of DMARC conflict. Here's the fix:**

1. **Find the row:** `TXT _dmarc v=DMARC1; p=quarantine...`
2. Click **Edit** (pencil icon)
3. **Replace** the Data/Value with:
   ```
   v=DMARC1; p=none;
   ```
4. Click **Save**

**Why this fixes it:**
- GoDaddy's DMARC says `p=quarantine` (strict - rejects emails)
- Resend needs `p=none` (monitoring only - allows emails)
- Changing to `p=none` lets Resend add its records

**⚠️ This is less strict but necessary for Resend to work**

---

## 🎯 After Fixes - Add Resend Records

Once you've completed Fixes 1-5, add Resend records:

### **Step 1: Add Domain to Resend**

1. Go to: https://resend.com/domains
2. Click **"Add Domain"**
3. Enter: `shiningarts.com.au`
4. Click **"Add"**

Resend will show you **3 DNS records**.

---

### **Step 2: Add Resend DNS Records to GoDaddy**

**Record 1: Domain Verification (TXT)**

Click **"Add"** → Select **"TXT"**
- Type: `TXT`
- Name: `@`
- Data: `resend-domain-verification=abc123...` (copy from Resend)
- TTL: `1 Hour`
- Click **Save**

**⚠️ If GoDaddy says "TXT record already exists for @":**
- Click **Edit** on existing `@ TXT` record
- **Append** the Resend verification to the SPF record with a space:
  ```
  v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all resend-domain-verification=abc123...
  ```
- **OR** delete the SPF record temporarily, add Resend TXT, then re-add SPF

**Record 2: DKIM (CNAME)**

Click **"Add"** → Select **"CNAME"**
- Type: `CNAME`
- Name: `resend._domainkey`
- Data: `resend._domainkey.resend.com`
- TTL: `1 Hour`
- Click **Save**

**This should work now** (after you changed DMARC to `p=none`)

**Record 3: DMARC (Already done!)**

You already have `_dmarc` pointing to GoDaddy's value. You changed it to `p=none` in Fix 5, which is what Resend needs.

✅ **Skip this** - Already handled in Fix 5.

---

### **Step 3: Wait for Resend Verification**

1. Wait **5-30 minutes** for DNS propagation
2. Go to Resend → Domains
3. Look for **green checkmark** next to `shiningarts.com.au`
4. If not verified after 30 min, click **"Verify"** button

---

## 📋 Final DNS Should Look Like This

```
A RECORDS:
@ → 185.230.63.107
@ → 185.230.63.171
@ → 185.230.63.186

CNAME RECORDS:
en → cdn1.wixdns.net
www → cdn1.wixdns.net (FIXED)
resend._domainkey → resend._domainkey.resend.com (NEW)

MX RECORDS:
@ → mx1.privateemail.com (Priority 10) (NEW)
@ → mx2.privateemail.com (Priority 10) (NEW)

TXT RECORDS:
@ → v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all (NEW)
@ → resend-domain-verification=... (NEW - may need to merge with SPF)
_dmarc → v=DMARC1; p=none; (CHANGED from p=quarantine)
```

---

## 🧪 Testing Checklist

### After Fixes 1-4 (Wait 30 min):

- [ ] Website loads: https://shiningarts.com.au
- [ ] www works: https://www.shiningarts.com.au
- [ ] **Send test email** from `info@shiningarts.com.au` (test MX records)
- [ ] **Receive test email** to `info@shiningarts.com.au`

### After Resend Records Added (Wait 30 min):

- [ ] Resend domain shows **green checkmark**
- [ ] Start dev server: `npm run dev`
- [ ] Submit **HIGH** severity feedback at localhost:3000/assessment
- [ ] Check inbox: `info@shiningarts.com.au`
- [ ] Email subject: `🚨 High Priority Feedback: ...`

---

## 🔧 Troubleshooting

### GoDaddy won't let me add TXT record for @ (Resend verification)?

**Solution 1: Merge with SPF**
Edit the SPF TXT record and append Resend's verification:
```
v=spf1 +ip4:66.29.141.42 +include:spf.web-hosting.com +include:spf.privateemail.com ~all resend-domain-verification=YOUR_KEY_HERE
```

**Solution 2: Use Subdomain**
- In Resend, verify a subdomain instead: `mail.shiningarts.com.au`
- Then use `from: 'NSW Planning <noreply@mail.shiningarts.com.au>'`

### GoDaddy still blocking resend._domainkey CNAME?

Make sure you:
1. Changed DMARC to `p=none` (Fix 5)
2. Waited 15 minutes after DMARC change
3. Try adding CNAME again

If still blocked:
- Check there's no existing `resend._domainkey` record
- Try using different name: `resend1._domainkey`

### Email not working after MX records added?

1. Verify both MX records are there with Priority 10
2. Wait 1 hour for full propagation
3. Check MX records: https://mxtoolbox.com/SuperTool.aspx?action=mx%3ashiningarts.com.au

---

## ⏱️ Timeline

- **Fix 1-5:** 10 minutes (manual work)
- **DNS Propagation:** 15-30 minutes (waiting)
- **Email Test:** 5 minutes
- **Add Resend:** 5 minutes
- **Resend Verification:** 15-30 minutes (waiting)
- **Test Feedback:** 5 minutes

**Total:** ~1 hour (mostly waiting for DNS)

---

## 🎯 Quick Action Items

**Do these now in order:**

1. ✅ Delete: `A @ Parked`
2. ✅ Edit: `CNAME www` → Change to `cdn1.wixdns.net`
3. ✅ Add: 2 MX records (`mx1` and `mx2.privateemail.com`)
4. ✅ Add: SPF TXT record
5. ✅ Edit: `_dmarc` → Change to `v=DMARC1; p=none;`
6. ⏸️ Wait 30 min → Test website & email
7. ✅ Add Resend domain → Copy 3 DNS records
8. ✅ Add: Resend TXT verification (may need to merge with SPF)
9. ✅ Add: Resend CNAME `resend._domainkey`
10. ⏸️ Wait 30 min → Verify green checkmark in Resend
11. ✅ Test feedback form → Check email inbox

---

**Start with Fix 1!** Let me know when you've completed each step or if you hit any issues.
