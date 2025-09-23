#!/bin/bash
# PRP Environment Check Script
# Verifies all requirements are met before PRP implementation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Logging functions
log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; ((CHECKS_PASSED++)); }
error() { echo -e "${RED}[✗]${NC} $1"; ((CHECKS_FAILED++)); }
warning() { echo -e "${YELLOW}[⚠]${NC} $1"; ((WARNINGS++)); }

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend-nextjs"

log "PRP Environment Check - Starting..."
log "Project Root: $PROJECT_ROOT"

echo "================================================================"
echo "                PRP ENVIRONMENT VERIFICATION"
echo "================================================================"

# 1. Node.js Version Check
log "Checking Node.js version..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1 | cut -d'v' -f2)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        success "Node.js version: $NODE_VERSION (≥18 required)"
    else
        error "Node.js version: $NODE_VERSION (Need ≥18.0.0)"
    fi
else
    error "Node.js not found"
fi

# 2. npm Check
log "Checking npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    success "npm version: $NPM_VERSION"
else
    error "npm not found"
fi

# 3. Python Check
log "Checking Python..."
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    success "Python version: $PYTHON_VERSION"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    success "Python version: $PYTHON_VERSION"
else
    error "Python not found"
fi

# 4. Project Structure Check
log "Checking project structure..."

required_dirs=(
    "$FRONTEND_DIR"
    "$PROJECT_ROOT/PRPs"
    "$PROJECT_ROOT/PRPs/NEWUI"
    "$PROJECT_ROOT/PRPs/NEWUI/AUTHORITATIVErouteUI"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        success "Directory exists: $(basename "$dir")"
    else
        error "Missing directory: $dir"
    fi
done

# 5. Frontend Dependencies Check
log "Checking frontend dependencies..."
if [ -f "$FRONTEND_DIR/package.json" ]; then
    success "package.json exists"

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ -d "node_modules" ]; then
        success "node_modules directory exists"
    else
        warning "node_modules missing - run 'npm install'"
    fi

    # Check key dependencies
    dependencies=("next" "react" "typescript" "jest")
    for dep in "${dependencies[@]}"; do
        if npm list "$dep" &> /dev/null; then
            success "Dependency installed: $dep"
        else
            error "Missing dependency: $dep"
        fi
    done

    cd "$PROJECT_ROOT"
else
    error "package.json not found in frontend directory"
fi

# 6. TypeScript Configuration Check
log "Checking TypeScript configuration..."
if [ -f "$FRONTEND_DIR/tsconfig.json" ]; then
    success "tsconfig.json exists"

    # Test TypeScript compilation
    cd "$FRONTEND_DIR"
    if npx tsc --noEmit --skipLibCheck 2>/dev/null; then
        success "TypeScript compilation successful"
    else
        warning "TypeScript compilation has errors"
    fi
    cd "$PROJECT_ROOT"
else
    error "tsconfig.json not found"
fi

# 7. Jest Configuration Check
log "Checking Jest configuration..."
if [ -f "$FRONTEND_DIR/jest.config.js" ]; then
    success "jest.config.js exists"

    # Test Jest
    cd "$FRONTEND_DIR"
    if timeout 10 npm test -- --passWithNoTests --watchAll=false 2>/dev/null; then
        success "Jest configuration valid"
    else
        warning "Jest configuration issues detected"
    fi
    cd "$PROJECT_ROOT"
else
    warning "jest.config.js not found - may cause test failures"
fi

# 8. Verification Script Check
log "Checking PRP verification script..."
VERIFY_SCRIPT="$PROJECT_ROOT/PRPs/NEWUI/AUTHORITATIVErouteUI/verify_ui_migration.py"
if [ -f "$VERIFY_SCRIPT" ]; then
    success "Verification script exists"

    # Test verification script
    cd "$(dirname "$VERIFY_SCRIPT")"
    if python verify_ui_migration.py --help &> /dev/null; then
        success "Verification script executable"

        # Test project root parameter
        if python verify_ui_migration.py --project-root "$PROJECT_ROOT" --help &> /dev/null; then
            success "Project root parameter supported"
        else
            error "Verification script doesn't support --project-root"
        fi
    else
        error "Verification script not executable"
    fi
    cd "$PROJECT_ROOT"
else
    error "Verification script not found"
fi

# 9. Git Status Check
log "Checking git status..."
if git status &> /dev/null; then
    success "Git repository detected"

    # Check for uncommitted changes
    if git diff --quiet && git diff --cached --quiet; then
        success "Working directory clean"
    else
        warning "Uncommitted changes detected"
    fi
else
    error "Not a git repository"
fi

# 10. Disk Space Check
log "Checking disk space..."
AVAILABLE_SPACE=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -gt 1048576 ]; then  # 1GB in KB
    success "Sufficient disk space available"
else
    warning "Low disk space - consider cleaning up"
fi

echo "================================================================"
echo "                    ENVIRONMENT CHECK SUMMARY"
echo "================================================================"

echo -e "${GREEN}Checks Passed:${NC} $CHECKS_PASSED"
echo -e "${RED}Checks Failed:${NC} $CHECKS_FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo ""
    success "✅ ENVIRONMENT READY FOR PRP IMPLEMENTATION"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./scripts/prp_dependency_mapper.sh [PRP_ID]"
    echo "2. Follow PRP implementation guide"
    echo "3. Execute PRP scripts with proper project root"
    exit 0
else
    echo ""
    error "❌ ENVIRONMENT NOT READY - FIX ERRORS BEFORE PROCEEDING"
    echo ""
    echo "Required fixes:"
    echo "1. Install missing dependencies"
    echo "2. Fix configuration issues"
    echo "3. Re-run this script until all checks pass"
    exit 1
fi