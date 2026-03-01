# Configure rclone for Cloudflare R2

## Step 1: Get Cloudflare R2 API Credentials

1. **Go to Cloudflare Dashboard**:
   - Visit: https://dash.cloudflare.com
   - Log in to your account

2. **Navigate to R2**:
   - Click **R2** in the left sidebar
   - You should see your bucket: `pub-7f3b945f2f0045d6991a6b9d6db51cd8`

3. **Get Account ID**:
   - Look for "Account ID" on the right sidebar
   - Copy it (looks like: `abc123def456...`)
   - **SAVE THIS** - you'll need it in Step 2

4. **Create API Token**:
   - Click **"Manage R2 API Tokens"** (top right)
   - Click **"Create API Token"**
   - **Name**: `rclone-upload`
   - **Permissions**: Select **"Object Read & Write"**
   - Click **"Create API Token"**

5. **SAVE CREDENTIALS** (you'll only see these once!):
   - **Access Key ID**: Copy and save
   - **Secret Access Key**: Copy and save

---

## Step 2: Configure rclone (Interactive)

Open PowerShell and run:
```powershell
C:\Users\lawre\AppData\Local\Programs\rclone\rclone.exe config
```

Follow these prompts:

```
No remotes found, make a new one?
n/s/q> n

name> r2

Type of storage> s3

Choose a number from below, or type in your own value.
provider> Cloudflare

Option env_auth.
env_auth> false

Option access_key_id.
access_key_id> [PASTE YOUR ACCESS KEY ID HERE]

Option secret_access_key.
secret_access_key> [PASTE YOUR SECRET ACCESS KEY HERE]

Option region.
region> [PRESS ENTER - leave blank]

Option endpoint.
endpoint> https://[YOUR-ACCOUNT-ID].r2.cloudflarestorage.com
         ↑ Replace [YOUR-ACCOUNT-ID] with the Account ID from Step 1

Option acl.
acl> [PRESS ENTER - leave blank]

Edit advanced config? (y/n)
y/n> n

Keep this "r2" remote? (y/n)
y/n> y

Current remotes:
Name                 Type
====                 ====
r2                   s3

e/n/d/r/c/s/q> q
```

---

## Step 3: Test Configuration

```powershell
C:\Users\lawre\AppData\Local\Programs\rclone\rclone.exe lsd r2:pub-7f3b945f2f0045d6991a6b9d6db51cd8
```

**Expected output**: List of folders in your R2 bucket (should show `dcps/` folder)

---

## ⚠️ Troubleshooting

### "403 Forbidden" error
- Check API token has "Object Read & Write" permissions
- Verify endpoint URL has correct Account ID
- Try regenerating the API token

### "Connection refused" error
- Check endpoint format: `https://ACCOUNT-ID.r2.cloudflarestorage.com`
- Ensure no trailing slashes
- Verify Account ID is correct

### "Access Denied" error
- API token may not have correct permissions
- Check bucket name is correct
- Ensure R2 is enabled on your Cloudflare account

---

## Next Step

After successful configuration, signal ready and I'll run the upload script!
