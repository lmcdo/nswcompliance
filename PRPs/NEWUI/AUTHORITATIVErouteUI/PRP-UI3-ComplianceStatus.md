# PRP-UI3: ComplianceStatus Component Migration

> **Priority**: High
> **Estimated Time**: 8-12 days
> **Dependencies**: PRP-UI1 (Feature Flags), PRP-UI2 (DevelopmentSelector)
> **Risk Level**: High
> **Week**: 3

## Overview

Migrate the ComplianceStatus component from the authoritative route to the main page with real-time status updates, enhanced visualization, and comprehensive compliance tracking. This component is critical for displaying compliance verification results and guiding user actions.

## Technical Specifications

### 1. Component Architecture

```typescript
// components/compliance/ComplianceStatus.tsx
export interface ComplianceCheck {
  id: string;
  provision: string;
  requirement: string;
  status: 'compliant' | 'non-compliant' | 'conditional' | 'not-applicable' | 'pending';
  severity: 'critical' | 'major' | 'minor' | 'informational';
  result?: any;
  evidence?: Evidence[];
  recommendations?: string[];
  lastChecked: Date;
  autoCheckEnabled: boolean;
}

export interface ComplianceStatusState {
  overallStatus: 'pass' | 'fail' | 'conditional' | 'incomplete' | 'not-started';
  checks: ComplianceCheck[];
  progress: {
    completed: number;
    total: number;
    percentage: number;
  };
  criticalIssues: ComplianceCheck[];
  warnings: ComplianceCheck[];
  lastUpdated: Date;
  autoRefreshEnabled: boolean;
}

export interface ComplianceStatusProps {
  propertyId: string;
  developmentType: DevelopmentType;
  assessmentId?: string;
  showDetails?: boolean;
  autoRefresh?: boolean;
  onStatusChange?: (status: ComplianceStatusState) => void;
  variant?: 'full' | 'summary' | 'minimal';
  groupBy?: 'category' | 'severity' | 'status' | 'provision';
}
```

### 2. Real-time Status Management

#### A. Compliance Context
```typescript
// contexts/ComplianceContext.tsx
export interface ComplianceContextState {
  status: ComplianceStatusState;
  isLoading: boolean;
  error: string | null;
  subscriptions: Map<string, WebSocket>;
  refreshInterval: number;
  lastRefresh: Date;
}

export interface ComplianceContextActions {
  initializeCompliance: (propertyId: string, developmentType: DevelopmentType) => Promise<void>;
  refreshStatus: (force?: boolean) => Promise<void>;
  subscribeToUpdates: (assessmentId: string) => void;
  unsubscribeFromUpdates: (assessmentId: string) => void;
  runComplianceCheck: (checkId: string) => Promise<void>;
  updateCheckStatus: (checkId: string, status: ComplianceCheck['status']) => void;
  toggleAutoRefresh: (enabled: boolean) => void;
  exportComplianceReport: () => Promise<Blob>;
}
```

#### B. WebSocket Integration
```typescript
// lib/compliance-websocket.ts
export class ComplianceWebSocketManager {
  private connections: Map<string, WebSocket> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private maxReconnectAttempts = 5;

  connect(assessmentId: string, onUpdate: (update: ComplianceUpdate) => void): void {
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/compliance/${assessmentId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`Compliance WebSocket connected for assessment ${assessmentId}`);
      this.reconnectAttempts.set(assessmentId, 0);
    };

    ws.onmessage = (event) => {
      try {
        const update: ComplianceUpdate = JSON.parse(event.data);
        onUpdate(update);
      } catch (error) {
        console.error('Failed to parse compliance update:', error);
      }
    };

    ws.onclose = () => {
      this.handleReconnect(assessmentId, onUpdate);
    };

    this.connections.set(assessmentId, ws);
  }

  private handleReconnect(assessmentId: string, onUpdate: (update: ComplianceUpdate) => void): void {
    const attempts = this.reconnectAttempts.get(assessmentId) || 0;

    if (attempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.connect(assessmentId, onUpdate);
        this.reconnectAttempts.set(assessmentId, attempts + 1);
      }, Math.pow(2, attempts) * 1000); // Exponential backoff
    }
  }
}
```

### 3. Enhanced ComplianceStatus Component

```typescript
// components/compliance/EnhancedComplianceStatus.tsx
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { useComplianceContext } from '@/contexts/ComplianceContext';
import { cn } from '@/lib/utils';

export const EnhancedComplianceStatus: React.FC<ComplianceStatusProps> = ({
  propertyId,
  developmentType,
  assessmentId,
  showDetails = true,
  autoRefresh = true,
  onStatusChange,
  variant = 'full',
  groupBy = 'category'
}) => {
  const { flags } = useFeatureFlags();
  const {
    status,
    isLoading,
    error,
    refreshStatus,
    subscribeToUpdates,
    runComplianceCheck,
    toggleAutoRefresh
  } = useComplianceContext();

  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [sortBy, setSortBy] = useState<'severity' | 'lastChecked' | 'provision'>('severity');

  // Subscribe to real-time updates
  useEffect(() => {
    if (assessmentId && autoRefresh) {
      subscribeToUpdates(assessmentId);
      toggleAutoRefresh(true);
    }

    return () => {
      if (assessmentId) {
        toggleAutoRefresh(false);
      }
    };
  }, [assessmentId, autoRefresh, subscribeToUpdates, toggleAutoRefresh]);

  // Notify parent of status changes
  useEffect(() => {
    if (onStatusChange) {
      onStatusChange(status);
    }
  }, [status, onStatusChange]);

  // Group and filter compliance checks
  const groupedChecks = useMemo(() => {
    let filteredChecks = status.checks;

    if (showOnlyIssues) {
      filteredChecks = filteredChecks.filter(check =>
        check.status === 'non-compliant' || check.status === 'conditional'
      );
    }

    // Sort checks
    filteredChecks = [...filteredChecks].sort((a, b) => {
      switch (sortBy) {
        case 'severity':
          const severityOrder = ['critical', 'major', 'minor', 'informational'];
          return severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity);
        case 'lastChecked':
          return new Date(b.lastChecked).getTime() - new Date(a.lastChecked).getTime();
        case 'provision':
          return a.provision.localeCompare(b.provision);
        default:
          return 0;
      }
    });

    // Group checks
    const grouped = new Map<string, ComplianceCheck[]>();

    filteredChecks.forEach(check => {
      let groupKey: string;

      switch (groupBy) {
        case 'category':
          groupKey = check.provision.split('.')[0] || 'Other';
          break;
        case 'severity':
          groupKey = check.severity;
          break;
        case 'status':
          groupKey = check.status;
          break;
        case 'provision':
          groupKey = check.provision;
          break;
        default:
          groupKey = 'All';
      }

      if (!grouped.has(groupKey)) {
        grouped.set(groupKey, []);
      }
      grouped.get(groupKey)!.push(check);
    });

    return grouped;
  }, [status.checks, showOnlyIssues, sortBy, groupBy]);

  // Status color mapping
  const getStatusColor = (status: ComplianceCheck['status']) => {
    switch (status) {
      case 'compliant': return 'text-green-600 bg-green-50 border-green-200';
      case 'non-compliant': return 'text-red-600 bg-red-50 border-red-200';
      case 'conditional': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'not-applicable': return 'text-gray-600 bg-gray-50 border-gray-200';
      case 'pending': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const handleRunCheck = useCallback(async (checkId: string) => {
    try {
      await runComplianceCheck(checkId);
    } catch (error) {
      console.error('Failed to run compliance check:', error);
    }
  }, [runComplianceCheck]);

  if (variant === 'minimal') {
    return (
      <div className="flex items-center space-x-2">
        <ComplianceStatusIndicator status={status.overallStatus} />
        <span className="text-sm font-medium">
          {status.progress.completed}/{status.progress.total} checks complete
        </span>
      </div>
    );
  }

  return (
    <div className={cn(
      "compliance-status",
      variant === 'summary' && "compact-view"
    )}>
      {/* Header with Overall Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Compliance Status</h2>
          <div className="flex items-center space-x-2">
            {autoRefresh && (
              <div className="flex items-center text-sm text-gray-500">
                <RefreshCw className="w-4 h-4 mr-1" />
                Auto-refresh
              </div>
            )}
            <button
              onClick={() => refreshStatus(true)}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
            >
              <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <ComplianceMetricCard
            title="Overall Status"
            value={status.overallStatus}
            color={getOverallStatusColor(status.overallStatus)}
          />
          <ComplianceMetricCard
            title="Progress"
            value={`${status.progress.percentage}%`}
            subtitle={`${status.progress.completed}/${status.progress.total} checks`}
          />
          <ComplianceMetricCard
            title="Critical Issues"
            value={status.criticalIssues.length}
            color={status.criticalIssues.length > 0 ? 'text-red-600' : 'text-green-600'}
          />
          <ComplianceMetricCard
            title="Warnings"
            value={status.warnings.length}
            color={status.warnings.length > 0 ? 'text-yellow-600' : 'text-green-600'}
          />
        </div>

        <ComplianceProgressBar progress={status.progress.percentage} />
      </div>

      {/* Controls */}
      {showDetails && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={showOnlyIssues}
                  onChange={(e) => setShowOnlyIssues(e.target.checked)}
                  className="mr-2"
                />
                Show only issues
              </label>

              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value as any)}
                className="px-3 py-1 border rounded-md text-sm"
              >
                <option value="category">Group by Category</option>
                <option value="severity">Group by Severity</option>
                <option value="status">Group by Status</option>
                <option value="provision">Group by Provision</option>
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-1 border rounded-md text-sm"
              >
                <option value="severity">Sort by Severity</option>
                <option value="lastChecked">Sort by Last Checked</option>
                <option value="provision">Sort by Provision</option>
              </select>
            </div>

            <div className="text-sm text-gray-500">
              Last updated: {new Date(status.lastUpdated).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Compliance Checks */}
      {showDetails && (
        <div className="space-y-4">
          {Array.from(groupedChecks.entries()).map(([groupName, checks]) => (
            <ComplianceGroup
              key={groupName}
              title={groupName}
              checks={checks}
              isExpanded={selectedGroup === groupName}
              onToggle={() => setSelectedGroup(
                selectedGroup === groupName ? null : groupName
              )}
              onRunCheck={handleRunCheck}
            />
          ))}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600">Error loading compliance status: {error}</p>
          <button
            onClick={() => refreshStatus(true)}
            className="mt-2 text-red-600 hover:text-red-800 text-sm"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
```

### 4. Supporting Components

#### A. Compliance Metric Card
```typescript
// components/compliance/ComplianceMetricCard.tsx
interface ComplianceMetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: React.ReactNode;
}

export const ComplianceMetricCard: React.FC<ComplianceMetricCardProps> = ({
  title,
  value,
  subtitle,
  color = 'text-gray-900',
  icon
}) => {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className={cn("text-2xl font-bold", color)}>{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  );
};
```

#### B. Compliance Progress Bar
```typescript
// components/compliance/ComplianceProgressBar.tsx
interface ComplianceProgressBarProps {
  progress: number;
  showLabel?: boolean;
  height?: 'sm' | 'md' | 'lg';
}

export const ComplianceProgressBar: React.FC<ComplianceProgressBarProps> = ({
  progress,
  showLabel = true,
  height = 'md'
}) => {
  const heightClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4'
  };

  return (
    <div className="mt-4">
      {showLabel && (
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
      )}
      <div className={cn("w-full bg-gray-200 rounded-full", heightClasses[height])}>
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            progress >= 100 ? "bg-green-500" :
            progress >= 75 ? "bg-blue-500" :
            progress >= 50 ? "bg-yellow-500" : "bg-orange-500"
          )}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  );
};
```

#### C. Compliance Group
```typescript
// components/compliance/ComplianceGroup.tsx
interface ComplianceGroupProps {
  title: string;
  checks: ComplianceCheck[];
  isExpanded: boolean;
  onToggle: () => void;
  onRunCheck: (checkId: string) => void;
}

export const ComplianceGroup: React.FC<ComplianceGroupProps> = ({
  title,
  checks,
  isExpanded,
  onToggle,
  onRunCheck
}) => {
  const statusCounts = useMemo(() => {
    return checks.reduce((acc, check) => {
      acc[check.status] = (acc[check.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
  }, [checks]);

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
      >
        <div className="flex items-center space-x-3">
          <ChevronRight className={cn(
            "w-4 h-4 transition-transform",
            isExpanded && "rotate-90"
          )} />
          <h3 className="font-medium text-gray-900">{title}</h3>
          <span className="text-sm text-gray-500">({checks.length} checks)</span>
        </div>
        <div className="flex items-center space-x-2">
          {Object.entries(statusCounts).map(([status, count]) => (
            <span
              key={status}
              className={cn(
                "px-2 py-1 text-xs rounded-full",
                getStatusColor(status as ComplianceCheck['status'])
              )}
            >
              {count}
            </span>
          ))}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-200">
          {checks.map((check) => (
            <ComplianceCheckRow
              key={check.id}
              check={check}
              onRunCheck={() => onRunCheck(check.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

## Implementation Steps

### Phase 1: Context and WebSocket Setup (Day 1-3)
1. **Create ComplianceContext**
   - State management implementation
   - WebSocket manager integration
   - Real-time update handling

2. **API Integration**
   - Compliance status endpoints
   - Real-time WebSocket setup
   - Caching strategies

3. **Redux Integration**
   - Compliance slice creation
   - Async actions for status updates
   - Optimistic updates

### Phase 2: Component Development (Day 4-8)
1. **Core Components**
   - EnhancedComplianceStatus
   - Supporting metric cards
   - Progress visualization

2. **Interactive Features**
   - Grouping and filtering
   - Real-time updates
   - Manual check execution

3. **Responsive Design**
   - Mobile optimization
   - Accessibility compliance
   - Performance optimization

### Phase 3: Integration and Testing (Day 9-12)
1. **Feature Flag Integration**
   - Conditional rendering
   - Gradual rollout preparation
   - Fallback mechanisms

2. **State Synchronization**
   - Cross-component integration
   - Development type integration
   - Property data coordination

3. **Comprehensive Testing**
   - Real-time update testing
   - Performance benchmarking
   - User experience validation

## Risk Mitigation

### Critical Risks
1. **Real-time Update Performance**
   - **Mitigation**: Debounced updates and batching
   - **Monitoring**: WebSocket connection health
   - **Fallback**: Polling-based updates

2. **State Management Complexity**
   - **Mitigation**: Clear state boundaries and actions
   - **Testing**: Comprehensive state transition tests
   - **Debugging**: Redux DevTools integration

3. **User Experience Degradation**
   - **Mitigation**: Optimistic updates and loading states
   - **Performance**: Virtual scrolling for large datasets
   - **Accessibility**: ARIA labels and keyboard navigation

## Verification Criteria

### Automated Tests
1. **Unit Tests** (>95% coverage)
   - Component rendering and interaction
   - State management functions
   - WebSocket connection handling

2. **Integration Tests**
   - Real-time update flow
   - API integration
   - Cross-component communication

3. **E2E Tests**
   - Complete compliance checking flow
   - Real-time update scenarios
   - Performance under load

### Manual Verification Checklist
- [ ] Real-time updates function correctly
- [ ] Grouping and filtering work accurately
- [ ] Progress visualization is accurate
- [ ] Manual check execution works
- [ ] Mobile responsive design functions
- [ ] Accessibility standards met
- [ ] Performance meets benchmarks
- [ ] Error handling prevents crashes

## Success Metrics

### Technical Metrics
- **Real-time Update Latency**: <500ms
- **Component Render Time**: <200ms
- **Memory Usage**: <10MB additional
- **WebSocket Connection Stability**: >99%

### User Experience Metrics
- **Status Accuracy**: >99%
- **Update Responsiveness**: >95% satisfaction
- **Task Completion Rate**: >98%
- **Error Recovery**: <1% failure rate

## Next Steps

Upon completion of PRP-UI3:
1. **Prepare for PRP-UI4**: ComplianceChecklist migration
2. **Monitor Performance**: Real-time metrics tracking
3. **User Feedback**: Collect compliance workflow insights
4. **Optimization**: Performance improvements based on usage

This PRP delivers a robust, real-time compliance status system that enhances user experience while maintaining accuracy and performance standards.