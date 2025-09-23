# PRP-INTEGRATION: Complete Backend-Frontend Integration

**Priority:** CRITICAL
**Version:** 1.0
**Date:** 2025-09-22
**Author:** Technical Implementation Team
**References:** documentation/TECHNICAL_ROLLOUT_FAILURE_PREVENTION_GUIDE.md

## Executive Summary
Complete the integration between backend services and frontend components to create functional end-to-end workflows. This PRP fixes the integration gaps identified in the AUTHORITATIVE UI implementation.

## Pre-Implementation Requirements

### Mandatory Checks (Run First)
```bash
# 1. Environment verification
./scripts/prp_environment_check.sh

# 2. Fix file associations (Windows)
./scripts/fix_file_associations.bat

# 3. Verify frontend is running
curl -I http://localhost:3007

# 4. Backup current state
cp -r frontend-nextjs frontend-nextjs.backup.$(date +%Y%m%d_%H%M%S)
```

### Success Criteria
- 100% of API endpoints return valid data
- Development type changes trigger compliance updates
- Property selection flows through all components
- Zero "manual integration required" comments
- All verification steps pass automatically

## Implementation Steps

### STEP 1: Fix ComplianceChecklist Integration in Main Page

#### 1.1 Implementation
```typescript
// frontend-nextjs/app/page.tsx - Line 88
// REPLACE:
<ComplianceChecklist propertyData={propertyData} />

// WITH:
<ComplianceChecklist
 propertyData={propertyData}
 developmentType={developmentType}
 propertyId={selectedProperty}
 zoneCode={zoneCode}
 onComplianceUpdate={(status) => {
 console.log('Compliance status updated:', status)
 // Trigger any parent state updates needed
 }}
/>
```

#### 1.2 Verification
```bash
# Auto-verify after implementation
python verify_integration.py --step 1 --project-root "."
```

### STEP 2: Update ComplianceChecklist Component Props

#### 2.1 Implementation
```typescript
// frontend-nextjs/components/compliance-checklist.tsx
interface ComplianceChecklistProps {
 propertyData: any
 developmentType: string
 propertyId: string | null
 zoneCode: string
 onComplianceUpdate?: (status: any) => void
}

export function ComplianceChecklist({
 propertyData,
 developmentType,
 propertyId,
 zoneCode,
 onComplianceUpdate
}: ComplianceChecklistProps) {
 // Update useEffect to respond to prop changes
 useEffect(() => {
 if (propertyData && developmentType && zoneCode) {
 fetchComplianceData()
 }
 }, [propertyData, developmentType, zoneCode])

 const fetchComplianceData = async () => {
 try {
 const response = await fetch('/api/compliance/enhanced', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 propertyId: propertyData?.propId,
 zone: zoneCode, // Note: API expects 'zone' not 'zoneCode'
 developmentType: developmentType
 })
 })

 if (response.ok) {
 const data = await response.json()
 setComplianceData(data)
 onComplianceUpdate?.(data)
 }
 } catch (error) {
 console.error('Compliance check failed:', error)
 }
 }
}
```

#### 2.2 Verification
```bash
python verify_integration.py --step 2 --project-root "."
```

### STEP 3: Connect DevelopmentSelector to Compliance Flow

#### 3.1 Implementation
```typescript
// frontend-nextjs/components/development-selector-enhanced.tsx
// Ensure onChange propagates properly
interface DevelopmentSelectorEnhancedProps {
 value: string
 onChange: (value: string) => void
 zoneCode: string
}

// Add zone-aware filtering
const getAvailableTypes = (zone: string) => {
 const zoneRestrictions: Record<string, string[]> = {
 'R2': ['dual_occupancy', 'single_dwelling', 'secondary_dwelling'],
 'R3': ['dual_occupancy', 'multi_dwelling', 'residential_flat'],
 'R4': ['residential_flat', 'shop_top_housing', 'multi_dwelling'],
 'B4': ['mixed_use', 'commercial', 'shop_top_housing']
 }

 return zoneRestrictions[zone] || Object.keys(developmentTypes)
}
```

#### 3.2 Verification
```bash
python verify_integration.py --step 3 --project-root "."
```

### STEP 4: Fix API Parameter Mismatches

#### 4.1 Implementation
```typescript
// frontend-nextjs/app/api/compliance/enhanced/route.ts
export async function POST(request: Request) {
 const body = await request.json()

 // Handle both 'zone' and 'zoneCode' for compatibility
 const zone = body.zone || body.zoneCode
 const { propertyId, developmentType } = body

 // Validate required fields
 if (!propertyId || !zone || !developmentType) {
 return NextResponse.json(
 { error: 'Missing required fields: propertyId, zone, developmentType' },
 { status: 400 }
 )
 }

 // Process compliance check
 const complianceResult = await performComplianceCheck({
 propertyId,
 zone,
 developmentType
 })

 return NextResponse.json(complianceResult)
}
```

#### 4.2 Verification
```bash
python verify_integration.py --step 4 --project-root "."
```

### STEP 5: Implement State Management Integration

#### 5.1 Implementation
```typescript
// frontend-nextjs/app/page.tsx
// Add state management for compliance results
const [complianceStatus, setComplianceStatus] = useState<any>(null)
const [isLoading, setIsLoading] = useState(false)

// Update handler to trigger compliance checks
const handleDevelopmentTypeChange = async (type: string) => {
 setDevelopmentType(type)
 setIsLoading(true)

 // Trigger compliance recheck
 if (propertyData && zoneCode) {
 try {
 const response = await fetch('/api/compliance/enhanced', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 propertyId: propertyData.propId,
 zone: zoneCode,
 developmentType: type
 })
 })

 if (response.ok) {
 const data = await response.json()
 setComplianceStatus(data)
 }
 } catch (error) {
 console.error('Failed to update compliance:', error)
 }
 }

 setIsLoading(false)
}
```

#### 5.2 Verification
```bash
python verify_integration.py --step 5 --project-root "."
```

### STEP 6: Complete Error Handling and Loading States

#### 6.1 Implementation
```typescript
// Add to all components that fetch data
const [error, setError] = useState<string | null>(null)
const [loading, setLoading] = useState(false)

// Wrap all API calls
try {
 setLoading(true)
 setError(null)
 // API call
} catch (err) {
 setError(err.message || 'An error occurred')
} finally {
 setLoading(false)
}

// Display states
{loading && <div>Loading...</div>}
{error && <div>Error: {error}</div>}
```

#### 6.2 Verification
```bash
python verify_integration.py --step 6 --project-root "."
```

## Verification Script

Create the following auto-verification script:

```python
# PRPs/PRP-INTEGRATION/verify_integration.py
#!/usr/bin/env python3
"""
Integration Verification Script
Runs automatically after each implementation step
"""

import sys
import subprocess
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import platform
import requests

class IntegrationVerifier:
 def __init__(self, project_root: str):
 self.project_root = Path(project_root).resolve()
 self.frontend_path = self.project_root / "frontend-nextjs"
 self.api_base = "http://localhost:3007"
 self.verification_results = []

 def verify_step_1(self) -> Tuple[bool, str]:
 """Verify main page integration"""
 print("Verifying Step 1: Main page integration...")

 # Check page.tsx has correct props
 page_file = self.frontend_path / "app" / "page.tsx"
 if not page_file.exists():
 return False, "page.tsx not found"

 content = page_file.read_text(encoding='utf-8')

 checks = [
 ("developmentType={developmentType}" in content, "developmentType prop"),
 ("propertyId={selectedProperty}" in content, "propertyId prop"),
 ("zoneCode={zoneCode}" in content, "zoneCode prop"),
 ("onComplianceUpdate" in content, "onComplianceUpdate callback")
 ]

 failed = []
 for check, name in checks:
 if not check:
 failed.append(f"Missing: {name}")

 if failed:
 return False, f"Integration incomplete: {', '.join(failed)}"

 return True, "Main page integration complete"

 def verify_step_2(self) -> Tuple[bool, str]:
 """Verify ComplianceChecklist component updates"""
 print("Verifying Step 2: ComplianceChecklist component...")

 component_file = self.frontend_path / "components" / "compliance-checklist.tsx"
 if not component_file.exists():
 # Try alternate location
 component_file = self.frontend_path / "components" / "compliance" / "ComplianceChecklist.tsx"
 if not component_file.exists():
 return False, "ComplianceChecklist component not found"

 content = component_file.read_text(encoding='utf-8')

 checks = [
 ("developmentType: string" in content, "developmentType prop type"),
 ("propertyId: string" in content, "propertyId prop type"),
 ("zoneCode: string" in content, "zoneCode prop type"),
 ("onComplianceUpdate" in content, "onComplianceUpdate callback"),
 ("useEffect" in content and "developmentType" in content, "useEffect dependency")
 ]

 failed = []
 for check, name in checks:
 if not check:
 failed.append(f"Missing: {name}")

 if failed:
 return False, f"Component update incomplete: {', '.join(failed)}"

 # Test TypeScript compilation
 if not self._test_typescript_compilation(component_file):
 return False, "TypeScript compilation failed"

 return True, "ComplianceChecklist component properly updated"

 def verify_step_3(self) -> Tuple[bool, str]:
 """Verify DevelopmentSelector integration"""
 print("Verifying Step 3: DevelopmentSelector integration...")

 selector_file = self.frontend_path / "components" / "development-selector-enhanced.tsx"
 if not selector_file.exists():
 return False, "DevelopmentSelectorEnhanced not found"

 content = selector_file.read_text(encoding='utf-8')

 checks = [
 ("zoneCode: string" in content, "zoneCode prop"),
 ("getAvailableTypes" in content, "zone-aware filtering"),
 ("onChange" in content, "onChange handler"),
 ("zoneRestrictions" in content, "zone restrictions defined")
 ]

 failed = []
 for check, name in checks:
 if not check:
 failed.append(f"Missing: {name}")

 if failed:
 return False, f"Selector integration incomplete: {', '.join(failed)}"

 return True, "DevelopmentSelector properly integrated"

 def verify_step_4(self) -> Tuple[bool, str]:
 """Verify API parameter handling"""
 print("Verifying Step 4: API parameter compatibility...")

 # Test API endpoint
 try:
 response = requests.post(
 f"{self.api_base}/api/compliance/enhanced",
 json={
 "propertyId": "test123",
 "zone": "R2",
 "developmentType": "dual_occupancy"
 },
 timeout=5
 )

 # Should either work or return specific error
 if response.status_code == 200:
 return True, "API accepts correct parameters"
 elif response.status_code == 400:
 error_data = response.json()
 if "Missing required fields" in error_data.get("error", ""):
 return False, "API still has parameter issues"

 except requests.RequestException as e:
 # Also test with zoneCode
 try:
 response = requests.post(
 f"{self.api_base}/api/compliance/enhanced",
 json={
 "propertyId": "test123",
 "zoneCode": "R2",
 "developmentType": "dual_occupancy"
 },
 timeout=5
 )

 if response.status_code != 400:
 return True, "API handles both zone and zoneCode"

 except:
 pass

 return False, "API parameter handling not working"

 def verify_step_5(self) -> Tuple[bool, str]:
 """Verify state management integration"""
 print("Verifying Step 5: State management...")

 page_file = self.frontend_path / "app" / "page.tsx"
 content = page_file.read_text(encoding='utf-8')

 checks = [
 ("complianceStatus, setComplianceStatus" in content, "compliance state"),
 ("isLoading, setIsLoading" in content, "loading state"),
 ("handleDevelopmentTypeChange" in content, "change handler"),
 ("fetch('/api/compliance/enhanced'" in content or 'fetch("/api/compliance/enhanced"' in content, "API call in handler")
 ]

 failed = []
 for check, name in checks:
 if not check:
 failed.append(f"Missing: {name}")

 if failed:
 return False, f"State management incomplete: {', '.join(failed)}"

 return True, "State management properly integrated"

 def verify_step_6(self) -> Tuple[bool, str]:
 """Verify error handling and loading states"""
 print("Verifying Step 6: Error handling...")

 components_to_check = [
 self.frontend_path / "app" / "page.tsx",
 self.frontend_path / "components" / "compliance-checklist.tsx",
 self.frontend_path / "components" / "development-selector-enhanced.tsx"
 ]

 for component in components_to_check:
 if component.exists():
 content = component.read_text(encoding='utf-8')

 if not ("loading" in content.lower() or "isloading" in content.lower()):
 return False, f"No loading state in {component.name}"

 if not ("error" in content.lower() and ("seterror" in content.lower() or "setError" in content)):
 return False, f"No error handling in {component.name}"

 if not ("try" in content and "catch" in content):
 return False, f"No try-catch blocks in {component.name}"

 return True, "Error handling and loading states implemented"

 def _test_typescript_compilation(self, file_path: Path) -> bool:
 """Test if TypeScript file compiles"""
 try:
 cmd = ["npx", "tsc", "--noEmit", "--skipLibCheck", str(file_path)]

 if platform.system() == "Windows":
 cmd = f'npx tsc --noEmit --skipLibCheck "{str(file_path)}"'
 result = subprocess.run(
 cmd,
 shell=True,
 cwd=self.frontend_path,
 capture_output=True,
 timeout=30,
 encoding='utf-8',
 errors='replace'
 )
 else:
 result = subprocess.run(
 cmd,
 cwd=self.frontend_path,
 capture_output=True,
 timeout=30,
 text=True
 )

 return result.returncode == 0

 except Exception as e:
 print(f"TypeScript compilation check failed: {e}")
 return False

 def verify_end_to_end(self) -> Tuple[bool, str]:
 """Verify complete end-to-end workflow"""
 print("\nVerifying end-to-end integration...")

 # Test complete workflow
 test_address = "30 ILLAWARRA ROAD MARRICKVILLE 2204"

 try:
 # 1. Fetch property
 response = requests.get(
 f"{self.api_base}/api/property",
 params={"address": test_address},
 timeout=10
 )

 if not response.ok:
 return False, "Property API failed"

 property_data = response.json().get("data")
 if not property_data:
 return False, "No property data returned"

 # 2. Test compliance check
 response = requests.post(
 f"{self.api_base}/api/compliance/enhanced",
 json={
 "propertyId": property_data.get("propId"),
 "zone": property_data.get("constraints", {}).get("zone"),
 "developmentType": "dual_occupancy"
 },
 timeout=10
 )

 if response.ok:
 return True, "End-to-end workflow successful"
 else:
 return False, f"Compliance check failed: {response.status_code}"

 except Exception as e:
 return False, f"End-to-end test failed: {str(e)}"

 def run_verification(self, step: int = None) -> bool:
 """Run verification for specific step or all steps"""

 print("="*60)
 print("INTEGRATION VERIFICATION")
 print("="*60)

 if step:
 # Run specific step
 verifier_method = getattr(self, f"verify_step_{step}", None)
 if not verifier_method:
 print(f"Invalid step: {step}")
 return False

 success, message = verifier_method()

 if success:
 print(f" Step {step}: PASS - {message}")
 return True
 else:
 print(f" Step {step}: FAIL - {message}")
 return False

 else:
 # Run all steps
 all_passed = True

 for i in range(1, 7):
 verifier_method = getattr(self, f"verify_step_{i}", None)
 if verifier_method:
 success, message = verifier_method()

 if success:
 print(f" Step {i}: PASS - {message}")
 else:
 print(f" Step {i}: FAIL - {message}")
 all_passed = False

 # Run end-to-end test
 success, message = self.verify_end_to_end()
 if success:
 print(f" End-to-End: PASS - {message}")
 else:
 print(f" End-to-End: FAIL - {message}")
 all_passed = False

 return all_passed

def main():
 parser = argparse.ArgumentParser(description="Verify integration implementation")
 parser.add_argument("--step", type=int, help="Specific step to verify (1-6)")
 parser.add_argument("--project-root", required=True, help="Project root directory")

 args = parser.parse_args()

 verifier = IntegrationVerifier(args.project_root)
 success = verifier.run_verification(args.step)

 sys.exit(0 if success else 1)

if __name__ == "__main__":
 main()
```

## Execute Script

Create the execution script that follows our prevention principles:

```bash
#!/bin/bash
# PRPs/PRP-INTEGRATION/execute_integration.sh

set -e # Exit on any error

# MANDATORY: Set project root (no relative paths!)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend-nextjs"
PRP_DIR="$PROJECT_ROOT/PRPs/PRP-INTEGRATION"
VERIFY_SCRIPT="$PRP_DIR/verify_integration.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Pre-flight checks
log "Running pre-flight checks..."

# 1. Check Node.js
if ! command -v node &> /dev/null; then
 error "Node.js is not installed"
fi

# 2. Check Python
if ! command -v python &> /dev/null; then
 error "Python is not installed"
fi

# 3. Check frontend is running
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:3007 | grep -q "200"; then
 error "Frontend is not running on localhost:3007"
fi

# 4. Create backup
log "Creating backup..."
BACKUP_DIR="$FRONTEND_DIR.backup.$(date +%Y%m%d_%H%M%S)"
cp -r "$FRONTEND_DIR" "$BACKUP_DIR"
log "Backup created at: $BACKUP_DIR"

# Implementation function
implement_step() {
 local step=$1
 local description=$2

 log "Implementing Step $step: $description"

 # Here you would add the actual implementation commands
 # For now, we'll just verify

 # Run verification immediately after implementation
 log "Verifying Step $step..."
 if python "$VERIFY_SCRIPT" --step $step --project-root "$PROJECT_ROOT"; then
 log "Step $step verification: PASSED"
 else
 error "Step $step verification: FAILED - Rolling back"
 # Rollback on failure
 rm -rf "$FRONTEND_DIR"
 cp -r "$BACKUP_DIR" "$FRONTEND_DIR"
 exit 1
 fi
}

# Main execution
log "Starting PRP-INTEGRATION implementation"
log "Project Root: $PROJECT_ROOT"

# Execute each step with immediate verification
implement_step 1 "Fix ComplianceChecklist integration in main page"
implement_step 2 "Update ComplianceChecklist component props"
implement_step 3 "Connect DevelopmentSelector to compliance flow"
implement_step 4 "Fix API parameter mismatches"
implement_step 5 "Implement state management integration"
implement_step 6 "Complete error handling and loading states"

# Final end-to-end verification
log "Running end-to-end verification..."
if python "$VERIFY_SCRIPT" --project-root "$PROJECT_ROOT"; then
 log "========================================="
 log "PRP-INTEGRATION COMPLETE - ALL TESTS PASS"
 log "========================================="

 # Clean up backup on success
 rm -rf "$BACKUP_DIR"
else
 error "End-to-end verification failed"
fi
```

## Rollback Procedures

If any step fails:

1. **Automatic Rollback**: The execute script automatically restores from backup
2. **Manual Rollback**:
 ```bash
 rm -rf frontend-nextjs
 cp -r frontend-nextjs.backup.[timestamp] frontend-nextjs
 ```
3. **Verify Rollback**:
 ```bash
 npm run dev
 curl -I http://localhost:3007
 ```

## Success Metrics

- **Step Completion**: Each step must pass verification before proceeding
- **TypeScript Compilation**: Zero errors
- **API Response Time**: <500ms for all endpoints
- **End-to-End Test**: Complete workflow from property selection to compliance check
- **No Manual Work**: Zero "manual integration required" comments

## Key Principles Applied

1. **No Relative Paths**: All paths use PROJECT_ROOT
2. **Immediate Verification**: Each step verified before next
3. **Platform Compatibility**: Windows and Unix support
4. **Dependency Order**: Props before state, state before API
5. **Integration First**: No isolated components
6. **Automatic Rollback**: Failure triggers restoration
7. **No Emojis**: Clean code only
8. **Complete Testing**: Unit and end-to-end

## Post-Implementation Checklist

- [ ] All 6 steps pass individual verification
- [ ] End-to-end workflow test passes
- [ ] TypeScript compiles without errors
- [ ] All API endpoints respond correctly
- [ ] Development type changes trigger updates
- [ ] Property selection flows through all components
- [ ] Error states display properly
- [ ] Loading states show during API calls
- [ ] No console errors in browser
- [ ] Backup has been cleaned up

---

**This PRP follows all principles from TECHNICAL_ROLLOUT_FAILURE_PREVENTION_GUIDE.md**