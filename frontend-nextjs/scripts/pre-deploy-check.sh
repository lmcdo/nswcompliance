#!/bin/bash
# Pre-deployment validation script
# Run this before every deployment to catch issues early

set -e

echo "🔍 Running pre-deployment checks..."

# 1. Check for untracked files that should be committed
echo "📁 Checking for untracked files..."
UNTRACKED=$(git ls-files --others --exclude-standard | grep -v node_modules | grep -v .next || true)
if [ ! -z "$UNTRACKED" ]; then
  echo "⚠️  Warning: Found untracked files that may need to be committed:"
  echo "$UNTRACKED"
  read -p "Continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# 2. Run TypeScript type checking
echo "🔍 Running TypeScript type check..."
cd "$(dirname "$0")/.."
npx tsc --noEmit || {
  echo "❌ TypeScript errors found. Fix these before deploying."
  exit 1
}

# 3. Run linting
echo "🔍 Running ESLint..."
npm run lint || {
  echo "❌ Linting errors found."
  exit 1
}

# 4. Check for common Vercel incompatibilities
echo "🔍 Checking for Vercel incompatibilities..."

# Check for Python subprocess calls
if grep -r "spawn.*python" app/ lib/ 2>/dev/null | grep -v node_modules; then
  echo "⚠️  Warning: Found Python subprocess calls. These won't work on Vercel."
fi

# Check for missing dependencies
if grep -r "from ['\"]formidable['\"]" app/ pages/ 2>/dev/null | grep -v node_modules; then
  echo "⚠️  Warning: Found 'formidable' imports but package may not be installed."
fi

# Check for child_process without feature flags
if grep -r "from ['\"]child_process['\"]" app/ 2>/dev/null | grep -v node_modules; then
  echo "⚠️  Warning: Found child_process imports. Ensure feature flags are used."
fi

# 5. Try a production build locally
echo "🏗️  Running production build test..."
npm run build || {
  echo "❌ Build failed. Fix errors before deploying."
  exit 1
}

echo "✅ All pre-deployment checks passed!"
echo "📦 Ready to deploy to Vercel"
