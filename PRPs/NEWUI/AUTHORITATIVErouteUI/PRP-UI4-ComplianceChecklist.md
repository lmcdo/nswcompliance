# PRP-UI4: ComplianceChecklist Component Migration

> **Priority**: High
> **Estimated Time**: 10-14 days
> **Dependencies**: PRP-UI1 (Feature Flags), PRP-UI2 (DevelopmentSelector), PRP-UI3 (ComplianceStatus)
> **Risk Level**: High
> **Week**: 4

## Overview

Migrate the ComplianceChecklist component from the authoritative route to the main page with enhanced interactivity, comprehensive evidence management, and automated compliance verification. This component serves as the primary interface for detailed compliance checking and documentation.

## Technical Specifications

### 1. Component Architecture

```typescript
// components/compliance/ComplianceChecklist.tsx
export interface ComplianceItem {
  id: string;
  provision: string;
  category: string;
  subcategory?: string;
  requirement: string;
  description: string;
  applicability: 'mandatory' | 'conditional' | 'optional';
  status: 'not-started' | 'in-progress' | 'compliant' | 'non-compliant' | 'conditional' | 'not-applicable';
  severity: 'critical' | 'major' | 'minor' | 'informational';
  evidence: Evidence[];
  calculations?: CalculationResult[];
  dependencies: string[];
  userNotes?: string;
  lastChecked?: Date;
  checkedBy?: string;
  autoCheckEnabled: boolean;
  manualOverride?: {
    status: ComplianceItem['status'];
    reason: string;
    approvedBy: string;
    approvedAt: Date;
  };
}

export interface Evidence {
  id: string;
  type: 'document' | 'calculation' | 'measurement' | 'photo' | 'drawing' | 'certificate';
  title: string;
  description?: string;
  fileUrl?: string;
  metadata: Record<string, any>;
  uploadedAt: Date;
  uploadedBy: string;
  verified: boolean;
  verifiedBy?: string;
  verifiedAt?: Date;
}

export interface ComplianceChecklistProps {
  propertyId: string;
  developmentType: DevelopmentType;
  assessmentId: string;
  items: ComplianceItem[];
  onItemUpdate: (itemId: string, updates: Partial<ComplianceItem>) => void;
  onEvidenceUpload: (itemId: string, evidence: File[]) => Promise<void>;
  onCalculationRun: (itemId: string, calculationType: string) => Promise<void>;
  readonly?: boolean;
  showCompleted?: boolean;
  groupBy?: 'category' | 'status' | 'severity' | 'provision';
  filterBy?: string[];
  variant?: 'full' | 'compact' | 'review';
}
```

### 2. Advanced State Management

#### A. Checklist Context
```typescript
// contexts/ChecklistContext.tsx
export interface ChecklistContextState {
  items: ComplianceItem[];
  filteredItems: ComplianceItem[];
  selectedItems: string[];
  bulkActions: {
    available: BulkAction[];
    inProgress: boolean;
  };
  uploadProgress: Map<string, UploadProgress>;
  calculations: Map<string, CalculationResult>;
  validationErrors: Map<string, string[]>;
  autoSaveEnabled: boolean;
  lastSaved: Date;
}

export interface ChecklistContextActions {
  loadChecklist: (assessmentId: string) => Promise<void>;
  updateItem: (itemId: string, updates: Partial<ComplianceItem>) => Promise<void>;
  bulkUpdateItems: (itemIds: string[], updates: Partial<ComplianceItem>) => Promise<void>;
  uploadEvidence: (itemId: string, files: File[]) => Promise<Evidence[]>;
  removeEvidence: (itemId: string, evidenceId: string) => Promise<void>;
  runCalculation: (itemId: string, calculationType: string) => Promise<CalculationResult>;
  validateItem: (item: ComplianceItem) => ValidationResult;
  exportChecklist: (format: 'pdf' | 'excel' | 'csv') => Promise<Blob>;
  importChecklist: (file: File) => Promise<void>;
  toggleAutoSave: (enabled: boolean) => void;
  resetItem: (itemId: string) => Promise<void>;
}
```

#### B. Evidence Management
```typescript
// lib/evidence-manager.ts
export class EvidenceManager {
  private uploadQueue: Map<string, UploadJob> = new Map();
  private uploadLimit = 5; // Concurrent uploads

  async uploadEvidence(
    itemId: string,
    files: File[],
    onProgress?: (progress: UploadProgress) => void
  ): Promise<Evidence[]> {
    const uploadJobs = files.map(file => ({
      id: crypto.randomUUID(),
      itemId,
      file,
      status: 'pending' as const,
      progress: 0
    }));

    const results: Evidence[] = [];

    for (const job of uploadJobs) {
      try {
        const evidence = await this.uploadFile(job, onProgress);
        results.push(evidence);
      } catch (error) {
        console.error(`Failed to upload evidence for item ${itemId}:`, error);
        throw error;
      }
    }

    return results;
  }

  private async uploadFile(
    job: UploadJob,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<Evidence> {
    const formData = new FormData();
    formData.append('file', job.file);
    formData.append('itemId', job.itemId);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress = (event.loaded / event.total) * 100;
          onProgress?.({
            jobId: job.id,
            itemId: job.itemId,
            fileName: job.file.name,
            progress,
            status: 'uploading'
          });
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          const evidence = JSON.parse(xhr.responseText);
          resolve(evidence);
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      };

      xhr.onerror = () => reject(new Error('Upload failed'));

      xhr.open('POST', '/api/evidence/upload');
      xhr.send(formData);
    });
  }
}
```

### 3. Enhanced ComplianceChecklist Component

```typescript
// components/compliance/EnhancedComplianceChecklist.tsx
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { useChecklistContext } from '@/contexts/ChecklistContext';
import { cn } from '@/lib/utils';

export const EnhancedComplianceChecklist: React.FC<ComplianceChecklistProps> = ({
  propertyId,
  developmentType,
  assessmentId,
  items,
  onItemUpdate,
  onEvidenceUpload,
  onCalculationRun,
  readonly = false,
  showCompleted = true,
  groupBy = 'category',
  filterBy = [],
  variant = 'full'
}) => {
  const { flags } = useFeatureFlags();
  const {
    filteredItems,
    selectedItems,
    bulkActions,
    uploadProgress,
    calculations,
    validationErrors,
    updateItem,
    bulkUpdateItems,
    uploadEvidence,
    runCalculation,
    validateItem
  } = useChecklistContext();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<'provision' | 'status' | 'severity' | 'lastChecked'>('provision');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  // Filter and group items
  const processedItems = useMemo(() => {
    let filtered = items;

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(item =>
        item.provision.toLowerCase().includes(term) ||
        item.requirement.toLowerCase().includes(term) ||
        item.description.toLowerCase().includes(term)
      );
    }

    // Apply category filter
    if (selectedCategories.length > 0) {
      filtered = filtered.filter(item =>
        selectedCategories.includes(item.category)
      );
    }

    // Apply status filter
    if (selectedStatuses.length > 0) {
      filtered = filtered.filter(item =>
        selectedStatuses.includes(item.status)
      );
    }

    // Apply show completed filter
    if (!showCompleted) {
      filtered = filtered.filter(item =>
        item.status !== 'compliant' && item.status !== 'not-applicable'
      );
    }

    // Apply additional filters
    if (filterBy.length > 0) {
      filtered = filtered.filter(item =>
        filterBy.some(filter =>
          item.category.includes(filter) ||
          item.provision.includes(filter) ||
          item.requirement.includes(filter)
        )
      );
    }

    // Sort items
    filtered = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'provision':
          return a.provision.localeCompare(b.provision);
        case 'status':
          const statusOrder = ['non-compliant', 'in-progress', 'not-started', 'conditional', 'compliant', 'not-applicable'];
          return statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status);
        case 'severity':
          const severityOrder = ['critical', 'major', 'minor', 'informational'];
          return severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity);
        case 'lastChecked':
          const aDate = a.lastChecked ? new Date(a.lastChecked).getTime() : 0;
          const bDate = b.lastChecked ? new Date(b.lastChecked).getTime() : 0;
          return bDate - aDate;
        default:
          return 0;
      }
    });

    // Group items
    const grouped = new Map<string, ComplianceItem[]>();

    filtered.forEach(item => {
      let groupKey: string;

      switch (groupBy) {
        case 'category':
          groupKey = item.category;
          break;
        case 'status':
          groupKey = item.status;
          break;
        case 'severity':
          groupKey = item.severity;
          break;
        case 'provision':
          groupKey = item.provision.split('.')[0] || 'Other';
          break;
        default:
          groupKey = 'All';
      }

      if (!grouped.has(groupKey)) {
        grouped.set(groupKey, []);
      }
      grouped.get(groupKey)!.push(item);
    });

    return grouped;
  }, [items, searchTerm, selectedCategories, selectedStatuses, showCompleted, filterBy, sortBy, groupBy]);

  // Handle item status update
  const handleStatusUpdate = useCallback(async (itemId: string, status: ComplianceItem['status']) => {
    try {
      await updateItem(itemId, { status, lastChecked: new Date() });
      onItemUpdate?.(itemId, { status });
    } catch (error) {
      console.error('Failed to update item status:', error);
    }
  }, [updateItem, onItemUpdate]);

  // Handle evidence upload
  const handleEvidenceUpload = useCallback(async (itemId: string, files: File[]) => {
    try {
      const evidence = await uploadEvidence(itemId, files);
      onEvidenceUpload?.(itemId, files);
    } catch (error) {
      console.error('Failed to upload evidence:', error);
    }
  }, [uploadEvidence, onEvidenceUpload]);

  // Handle calculation execution
  const handleCalculationRun = useCallback(async (itemId: string, calculationType: string) => {
    try {
      const result = await runCalculation(itemId, calculationType);
      onCalculationRun?.(itemId, calculationType);
    } catch (error) {
      console.error('Failed to run calculation:', error);
    }
  }, [runCalculation, onCalculationRun]);

  // Handle bulk actions
  const handleBulkAction = useCallback(async (action: string) => {
    if (selectedItems.length === 0) return;

    try {
      switch (action) {
        case 'mark-compliant':
          await bulkUpdateItems(selectedItems, { status: 'compliant', lastChecked: new Date() });
          break;
        case 'mark-not-applicable':
          await bulkUpdateItems(selectedItems, { status: 'not-applicable', lastChecked: new Date() });
          break;
        case 'reset':
          await bulkUpdateItems(selectedItems, { status: 'not-started', lastChecked: undefined });
          break;
        default:
          console.warn('Unknown bulk action:', action);
      }
    } catch (error) {
      console.error('Bulk action failed:', error);
    }
  }, [selectedItems, bulkUpdateItems]);

  if (variant === 'compact') {
    return <CompactChecklistView items={Array.from(processedItems.values()).flat()} />;
  }

  return (
    <div className="compliance-checklist">
      {/* Header with Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Compliance Checklist</h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                "px-3 py-1 text-sm border rounded-md",
                showFilters ? "bg-blue-50 border-blue-200" : "bg-white border-gray-200"
              )}
            >
              <Filter className="w-4 h-4 mr-1 inline" />
              Filters
            </button>
            {!readonly && selectedItems.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">
                  {selectedItems.length} selected
                </span>
                <select
                  onChange={(e) => handleBulkAction(e.target.value)}
                  className="px-3 py-1 text-sm border rounded-md"
                  defaultValue=""
                >
                  <option value="">Bulk Actions</option>
                  <option value="mark-compliant">Mark Compliant</option>
                  <option value="mark-not-applicable">Mark Not Applicable</option>
                  <option value="reset">Reset Status</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div className="mb-4">
          <input
            type="text"
            placeholder="Search compliance items..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-md"
          />
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-md">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Categories
              </label>
              <CheckboxGroup
                options={getUniqueCategories(items)}
                selected={selectedCategories}
                onChange={setSelectedCategories}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <CheckboxGroup
                options={['not-started', 'in-progress', 'compliant', 'non-compliant', 'conditional', 'not-applicable']}
                selected={selectedStatuses}
                onChange={setSelectedStatuses}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="provision">Provision</option>
                <option value="status">Status</option>
                <option value="severity">Severity</option>
                <option value="lastChecked">Last Checked</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Group By
              </label>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value as any)}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="category">Category</option>
                <option value="status">Status</option>
                <option value="severity">Severity</option>
                <option value="provision">Provision</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Checklist Items */}
      <div className="space-y-4">
        {Array.from(processedItems.entries()).map(([groupName, groupItems]) => (
          <ChecklistGroup
            key={groupName}
            title={groupName}
            items={groupItems}
            readonly={readonly}
            expandedItems={expandedItems}
            onToggleExpand={(itemId) => {
              const newExpanded = new Set(expandedItems);
              if (newExpanded.has(itemId)) {
                newExpanded.delete(itemId);
              } else {
                newExpanded.add(itemId);
              }
              setExpandedItems(newExpanded);
            }}
            onStatusUpdate={handleStatusUpdate}
            onEvidenceUpload={handleEvidenceUpload}
            onCalculationRun={handleCalculationRun}
            uploadProgress={uploadProgress}
            calculations={calculations}
            validationErrors={validationErrors}
          />
        ))}
      </div>

      {/* No Results */}
      {processedItems.size === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No compliance items match your filters.</p>
          <button
            onClick={() => {
              setSearchTerm('');
              setSelectedCategories([]);
              setSelectedStatuses([]);
            }}
            className="mt-2 text-blue-600 hover:text-blue-800"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
};
```

### 4. Supporting Components

#### A. Checklist Item Component
```typescript
// components/compliance/ChecklistItem.tsx
interface ChecklistItemProps {
  item: ComplianceItem;
  readonly: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onStatusUpdate: (status: ComplianceItem['status']) => void;
  onEvidenceUpload: (files: File[]) => void;
  onCalculationRun: (calculationType: string) => void;
  uploadProgress?: UploadProgress;
  calculations?: CalculationResult;
  validationErrors?: string[];
}

export const ChecklistItem: React.FC<ChecklistItemProps> = ({
  item,
  readonly,
  isExpanded,
  onToggleExpand,
  onStatusUpdate,
  onEvidenceUpload,
  onCalculationRun,
  uploadProgress,
  calculations,
  validationErrors
}) => {
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState(item.userNotes || '');

  const getStatusColor = (status: ComplianceItem['status']) => {
    switch (status) {
      case 'compliant': return 'bg-green-100 text-green-800 border-green-200';
      case 'non-compliant': return 'bg-red-100 text-red-800 border-red-200';
      case 'conditional': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'in-progress': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'not-applicable': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-50 text-gray-600 border-gray-200';
    }
  };

  return (
    <div className={cn(
      "border rounded-lg transition-all",
      item.severity === 'critical' ? 'border-red-300' :
      item.severity === 'major' ? 'border-orange-300' :
      item.severity === 'minor' ? 'border-yellow-300' : 'border-gray-200'
    )}>
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <span className="font-mono text-sm text-gray-500">{item.provision}</span>
              <span className={cn(
                "px-2 py-1 text-xs rounded-full",
                getStatusColor(item.status)
              )}>
                {item.status.replace('-', ' ')}
              </span>
              {item.severity === 'critical' && (
                <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                  Critical
                </span>
              )}
            </div>
            <h3 className="font-medium text-gray-900 mb-2">{item.requirement}</h3>
            <p className="text-sm text-gray-600">{item.description}</p>
          </div>
          <div className="flex items-center space-x-2 ml-4">
            {!readonly && (
              <StatusSelector
                currentStatus={item.status}
                onStatusChange={onStatusUpdate}
                disabled={readonly}
              />
            )}
            <button
              onClick={onToggleExpand}
              className="p-1 text-gray-500 hover:text-gray-700"
            >
              <ChevronDown className={cn(
                "w-4 h-4 transition-transform",
                isExpanded && "rotate-180"
              )} />
            </button>
          </div>
        </div>

        {/* Validation Errors */}
        {validationErrors && validationErrors.length > 0 && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
            <ul className="text-sm text-red-600 list-disc list-inside">
              {validationErrors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 space-y-4">
          {/* Evidence Section */}
          <EvidenceSection
            evidence={item.evidence}
            onUpload={onEvidenceUpload}
            uploadProgress={uploadProgress}
            readonly={readonly}
          />

          {/* Calculations Section */}
          {item.calculations && item.calculations.length > 0 && (
            <CalculationsSection
              calculations={item.calculations}
              onRunCalculation={onCalculationRun}
              readonly={readonly}
            />
          )}

          {/* Notes Section */}
          <NotesSection
            notes={notes}
            onNotesChange={setNotes}
            readonly={readonly}
          />

          {/* Dependencies */}
          {item.dependencies.length > 0 && (
            <DependenciesSection dependencies={item.dependencies} />
          )}
        </div>
      )}
    </div>
  );
};
```

## Implementation Steps

### Phase 1: Foundation and Context (Day 1-4)
1. **Create ChecklistContext**
   - State management implementation
   - Bulk operations support
   - Auto-save functionality

2. **Evidence Management System**
   - File upload handling
   - Progress tracking
   - Storage integration

3. **Validation Framework**
   - Item validation logic
   - Dependency checking
   - Error handling

### Phase 2: Core Component Development (Day 5-10)
1. **Main Checklist Component**
   - Enhanced filtering and grouping
   - Search functionality
   - Bulk operations UI

2. **Item Detail Components**
   - Individual item display
   - Evidence management
   - Calculation integration

3. **Interactive Features**
   - Status updates
   - Note taking
   - File uploads

### Phase 3: Advanced Features (Day 11-14)
1. **Calculation Integration**
   - Automated calculations
   - Result display
   - Progress tracking

2. **Import/Export Functionality**
   - PDF report generation
   - Excel/CSV export
   - Data import

3. **Performance Optimization**
   - Virtual scrolling
   - Lazy loading
   - Caching strategies

## Risk Mitigation

### Critical Risks
1. **Large Dataset Performance**
   - **Mitigation**: Virtual scrolling and pagination
   - **Monitoring**: Component render time tracking
   - **Optimization**: Lazy loading and memoization

2. **Evidence Upload Reliability**
   - **Mitigation**: Chunked uploads and retry logic
   - **Progress Tracking**: Real-time upload feedback
   - **Error Recovery**: Queue management and resumption

3. **State Synchronization Complexity**
   - **Mitigation**: Clear state boundaries and actions
   - **Testing**: Comprehensive state transition tests
   - **Debugging**: Detailed logging and DevTools

## Verification Criteria

### Automated Tests
1. **Unit Tests** (>95% coverage)
   - Component rendering and interaction
   - State management functions
   - File upload handling

2. **Integration Tests**
   - Bulk operations
   - Evidence management
   - Calculation execution

3. **E2E Tests**
   - Complete checklist workflow
   - File upload scenarios
   - Performance under load

### Manual Verification Checklist
- [ ] All compliance items display correctly
- [ ] Filtering and grouping work accurately
- [ ] Evidence upload functions properly
- [ ] Bulk operations execute correctly
- [ ] Status updates persist correctly
- [ ] Mobile responsive design functions
- [ ] Accessibility standards met
- [ ] Performance meets benchmarks

## Success Metrics

### Technical Metrics
- **Component Load Time**: <300ms for 100 items
- **Filter Response Time**: <150ms
- **Upload Success Rate**: >99%
- **Memory Usage**: <15MB for large datasets

### User Experience Metrics
- **Task Completion Rate**: >97%
- **Error Rate**: <1%
- **User Satisfaction**: >4.5/5
- **Time to Complete Assessment**: <20% improvement

## Next Steps

Upon completion of PRP-UI4:
1. **Prepare for PRP-UI5**: Full integration testing
2. **Performance Monitoring**: Track usage patterns
3. **User Training**: Documentation and tutorials
4. **Feedback Collection**: User experience insights

This PRP delivers a comprehensive, user-friendly compliance checklist system that streamlines the compliance verification process while maintaining accuracy and efficiency.