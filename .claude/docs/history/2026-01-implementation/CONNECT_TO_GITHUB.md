# Connect Project to GitHub Repository

## Quick Steps

### **Step 1: Create GitHub Repository**

1. Go to: https://github.com/new
2. Fill in:
   - **Repository name:** `nsw-planning-engine` (or any name)
   - **Description:** NSW Planning Compliance Engine
   - **Visibility:** Private (or Public)
   - ❌ **DO NOT** check "Initialize with README" (you already have files)
3. Click **"Create repository"**

GitHub will show you setup instructions. **Copy the repository URL** - looks like:
```
https://github.com/YOUR_USERNAME/nsw-planning-engine.git
```

---

### **Step 2: Initialize Git (If Not Already)**

Open terminal in your project folder:

```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Check if git is already initialized
git status
```

**If you see:** "fatal: not a git repository"
```bash
git init
```

**If you see:** "On branch main" or files listed
→ Git is already initialized, skip to Step 3

---

### **Step 3: Add Remote Repository**

```bash
# Add GitHub as remote (replace with YOUR repository URL)
git remote add origin https://github.com/YOUR_USERNAME/nsw-planning-engine.git

# Verify it was added
git remote -v
```

**If you get error "remote origin already exists":**
```bash
# Remove old remote
git remote remove origin

# Add new one
git remote add origin https://github.com/YOUR_USERNAME/nsw-planning-engine.git
```

---

### **Step 4: Stage Your Files**

```bash
# Add all files
git add .

# Check what will be committed
git status
```

---

### **Step 5: Create Initial Commit**

```bash
git commit -m "Initial commit - NSW Planning Compliance Engine"
```

**If you get error about user.name:**
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Then try commit again
git commit -m "Initial commit - NSW Planning Compliance Engine"
```

---

### **Step 6: Push to GitHub**

```bash
# Set default branch name
git branch -M main

# Push to GitHub
git push -u origin main
```

**If prompted for credentials:**
- **Username:** Your GitHub username
- **Password:** Use a **Personal Access Token** (not your GitHub password)

**To create a Personal Access Token:**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Name: "Vercel Deploy"
4. Expiration: 90 days (or custom)
5. Scopes: Check `repo` (full control of repositories)
6. Click "Generate token"
7. **Copy the token** (you won't see it again!)
8. Use this as your password when pushing

---

### **Step 7: Connect Vercel to GitHub**

Once code is on GitHub:

1. **Vercel Dashboard:** https://vercel.com/dashboard
2. Click your project name
3. Click **"Settings"** → **"Git"**
4. Click **"Connect Git Repository"**
5. Select **GitHub**
6. Authorize Vercel (if needed)
7. Select your repository: `YOUR_USERNAME/nsw-planning-engine`
8. Click **"Connect"**

**Benefits:**
- ✅ Auto-deploy on every `git push`
- ✅ Preview deployments for branches
- ✅ Easy rollbacks
- ✅ Deploy logs in GitHub

---

## Alternative: Quick Git Commands

If you just want to push quickly:

```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Initialize (if needed)
git init

# Add files
git add .

# Commit
git commit -m "Initial commit"

# Add remote (replace URL)
git remote add origin https://github.com/YOUR_USERNAME/nsw-planning-engine.git

# Push
git branch -M main
git push -u origin main
```

---

## Connecting Existing Vercel Project to Git

**If your project is already deployed on Vercel without Git:**

1. Vercel Dashboard → Your Project
2. Settings → Git
3. Click **"Connect Git Repository"**
4. Choose GitHub
5. Select your repo
6. Click **"Connect"**

**Next deployment will use Git instead of manual uploads.**

---

## .gitignore - Important!

Make sure you have a `.gitignore` file to exclude sensitive files:

```bash
# Check if .gitignore exists
ls .gitignore
```

**Your `.gitignore` should include:**
```
# Dependencies
node_modules/
.pnp
.pnp.js

# Next.js
.next/
out/
build/
dist/

# Environment variables
.env
.env.local
.env*.local

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Vercel
.vercel

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Database
*.db
*.sqlite

# Python
__pycache__/
*.py[cod]
venv/
venv_linux/

# Backups
backups/
*.backup
```

**⚠️ NEVER commit `.env.local` - it has your API keys!**

---

## Troubleshooting

### "fatal: not a git repository"
→ Run `git init` first

### "remote origin already exists"
→ Run `git remote remove origin` then add again

### "failed to push - authentication failed"
→ Use Personal Access Token (not password)
→ Get token from: https://github.com/settings/tokens

### "Updates were rejected - non-fast-forward"
→ Run `git pull origin main --rebase` then push again

### Files are too large (>100MB)
→ Check for large files: `git ls-files --full-name --abbrev | xargs ls -sh`
→ Remove from git: `git rm --cached large-file.zip`
→ Add to `.gitignore`

---

## Quick Reference

**Create repo:** https://github.com/new

**Personal tokens:** https://github.com/settings/tokens

**Git documentation:** https://git-scm.com/doc

**Vercel Git integration:** https://vercel.com/docs/deployments/git

---

## Summary

```bash
# 1. Create repo on GitHub
# 2. In terminal:
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/nsw-planning-engine.git
git branch -M main
git push -u origin main

# 3. Connect in Vercel:
# Settings → Git → Connect Repository
```

**After connecting:** Every `git push` will trigger a new Vercel deployment automatically!
