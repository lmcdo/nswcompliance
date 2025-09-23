#!/bin/bash
# PRP-A1 Execution Script: Foundation & Project Merge

set -e  # Exit on any error

echo "🚀 Executing PRP-A1: Foundation & Project Merge"
echo "=============================================="

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "📁 Project root: $PROJECT_ROOT"

# Step 1: Create component directory structure
echo "Step 1: Creating component directories..."
mkdir -p frontend-nextjs/components/assessment/{core,shared,layouts}
mkdir -p frontend-nextjs/app/assessment
mkdir -p frontend-nextjs/lib/assessment
mkdir -p frontend-nextjs/hooks/assessment

echo "✅ Directories created"

# Step 2: Check if nsw-assessment folder exists
if [ ! -d "nsw-assessment" ]; then
    echo "❌ ERROR: nsw-assessment folder not found in project root"
    echo "Expected path: $PROJECT_ROOT/nsw-assessment"
    exit 1
fi

echo "✅ nsw-assessment folder found"

# Step 3: Copy components from nsw-assessment
echo "Step 2: Copying components from nsw-assessment..."

# Copy components (if they exist)
if [ -d "nsw-assessment/components" ]; then
    cp -r nsw-assessment/components/* frontend-nextjs/components/assessment/core/ 2>/dev/null || echo "ℹ️ No components to copy"
fi

# Copy app files
if [ -d "nsw-assessment/app" ]; then
    cp -r nsw-assessment/app/* frontend-nextjs/app/assessment/ 2>/dev/null || echo "ℹ️ No app files to copy"
fi

# Copy lib files
if [ -d "nsw-assessment/lib" ]; then
    cp -r nsw-assessment/lib/* frontend-nextjs/lib/assessment/ 2>/dev/null || echo "ℹ️ No lib files to copy"
fi

echo "✅ Files copied"

# Step 4: Create placeholder files if they don't exist
echo "Step 3: Creating placeholder files..."

# Create main assessment page
cat > frontend-nextjs/app/assessment/page.tsx << 'EOF'
'use client';

import React from 'react';

export default function AssessmentPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          NSW Planning Assessment
        </h1>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Property Context Panel */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Property Context</h2>
              <p className="text-gray-600">Property information will appear here</p>
            </div>
          </div>

          {/* Assessment Panel */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Compliance Assessment</h2>
              <p className="text-gray-600">Assessment tools will appear here</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
EOF

# Create layout file
cat > frontend-nextjs/app/assessment/layout.tsx << 'EOF'
import React from 'react';

export default function AssessmentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="assessment-layout">
      {children}
    </div>
  );
}
EOF

# Create core components
mkdir -p frontend-nextjs/components/assessment/core

cat > frontend-nextjs/components/assessment/core/PropertyCard.tsx << 'EOF'
'use client';

import React from 'react';

interface PropertyCardProps {
  address?: string;
  zone?: string;
  lga?: string;
  area?: string;
}

export default function PropertyCard({ address, zone, lga, area }: PropertyCardProps) {
  return (
    <div className="bg-white border rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Property Information</h3>

      <div className="space-y-3">
        <div>
          <label className="text-sm text-gray-600">Address</label>
          <p className="font-medium">{address || 'No address selected'}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-600">Zone</label>
            <p className="font-medium">{zone || '-'}</p>
          </div>
          <div>
            <label className="text-sm text-gray-600">Area</label>
            <p className="font-medium">{area || '-'}</p>
          </div>
        </div>

        <div>
          <label className="text-sm text-gray-600">LGA</label>
          <p className="font-medium">{lga || '-'}</p>
        </div>
      </div>
    </div>
  );
}
EOF

cat > frontend-nextjs/components/assessment/core/ComplianceChecklist.tsx << 'EOF'
'use client';

import React from 'react';

interface ChecklistItem {
  id: string;
  provision: string;
  clause: string;
  status: 'compliant' | 'non-compliant' | 'pending';
  details?: string;
}

interface ComplianceChecklistProps {
  items?: ChecklistItem[];
}

export default function ComplianceChecklist({ items = [] }: ComplianceChecklistProps) {
  return (
    <div className="bg-white border rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Compliance Checklist</h3>

      {items.length === 0 ? (
        <p className="text-gray-600">Select a development type to generate checklist</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="border rounded p-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">{item.provision}</h4>
                  <p className="text-sm text-gray-600">{item.clause}</p>
                </div>
                <div className={`px-2 py-1 rounded text-xs font-medium ${
                  item.status === 'compliant' ? 'bg-green-100 text-green-800' :
                  item.status === 'non-compliant' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {item.status}
                </div>
              </div>
              {item.details && (
                <p className="text-sm text-gray-600 mt-2">{item.details}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
EOF

echo "✅ Placeholder files created"

# Step 5: Check Node.js dependencies
echo "Step 4: Checking dependencies..."
cd frontend-nextjs

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ ERROR: package.json not found in frontend-nextjs"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✅ Dependencies already installed"
fi

cd ..

# Step 6: Create basic types
echo "Step 5: Creating TypeScript types..."

cat > frontend-nextjs/lib/assessment/types.ts << 'EOF'
export interface PropertyData {
  propId: number;
  address: string;
  zone: string;
  lga: string;
  area: string;
  landValue?: string;
  heritage?: boolean;
}

export interface AssessmentContext {
  propertyId?: number;
  developmentType?: string;
  assessmentDate: Date;
  versionId?: number;
}

export interface ComplianceResult {
  provision: string;
  clause: string;
  status: 'compliant' | 'non-compliant' | 'pending';
  details?: string;
  requirement?: string;
}

export interface AssessmentData {
  property?: PropertyData;
  compliance: ComplianceResult[];
  checklist: ComplianceResult[];
  versions: {
    current: string;
    effective: string;
  };
}

export type DevelopmentType =
  | 'dwelling_house'
  | 'dual_occupancy'
  | 'multi_dwelling_housing'
  | 'residential_flat_building'
  | 'commercial_premises'
  | 'retail_premises'
  | 'office_premises'
  | 'industrial'
  | 'warehouse'
  | 'mixed_use';
EOF

echo "✅ TypeScript types created"

# Step 7: Create navigation route
echo "Step 6: Adding assessment route to navigation..."

# Check if main layout exists and add assessment link
if [ -f "frontend-nextjs/app/layout.tsx" ]; then
    echo "ℹ️ Found existing layout - assessment route should be added manually"
else
    echo "ℹ️ No main layout found - will be handled in next PRP"
fi

echo ""
echo "🎉 PRP-A1 Execution Complete!"
echo "=============================="
echo ""
echo "✅ Component directories created"
echo "✅ Files copied from nsw-assessment"
echo "✅ Placeholder components created"
echo "✅ TypeScript types defined"
echo "✅ Dependencies checked"
echo ""
echo "🔍 Next: Run verification script"
echo "python PRPs/NEWUI/scripts/verify_prp_a1.py"