#!/bin/bash
# PRP-UI3 Execution Script: ComplianceStatus Component Migration
# Week 3 - Days 15-21

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend-nextjs"
PRP_DIR="$PROJECT_ROOT/PRPs/NEWUI/AUTHORITATIVErouteUI"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for PRP-UI3..."

    # Check if previous PRPs completed
    if [[ ! -f "$FRONTEND_DIR/lib/feature-flags.ts" ]]; then
        error "PRP-UI1 not completed. Please run execute_prp_ui1.sh first"
        exit 1
    fi

    if [[ ! -f "$FRONTEND_DIR/components/development/DevelopmentSelector.tsx" ]]; then
        error "PRP-UI2 not completed. Please run execute_prp_ui2.sh first"
        exit 1
    fi

    success "Prerequisites check passed"
}

# Create directory structure
create_directories() {
    log "Creating directory structure for ComplianceStatus..."

    directories=(
        "$FRONTEND_DIR/components/compliance"
        "$FRONTEND_DIR/contexts"
        "$FRONTEND_DIR/lib"
        "$FRONTEND_DIR/pages/api/compliance"
        "$FRONTEND_DIR/__tests__/components/compliance"
        "$FRONTEND_DIR/__tests__/lib"
    )

    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done

    success "Directory structure created"
}

# Create compliance types
create_compliance_types() {
    log "Creating compliance type definitions..."

    cat > "$FRONTEND_DIR/components/compliance/types.ts" << 'EOF'
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
  developmentType: any;
  assessmentId?: string;
  showDetails?: boolean;
  autoRefresh?: boolean;
  onStatusChange?: (status: ComplianceStatusState) => void;
  variant?: 'full' | 'summary' | 'minimal';
  groupBy?: 'category' | 'severity' | 'status' | 'provision';
}

export interface ComplianceUpdate {
  type: 'status_change' | 'check_complete' | 'error';
  checkId?: string;
  status?: ComplianceCheck['status'];
  message?: string;
  timestamp: Date;
}
EOF

    success "Compliance types created"
}

# Create WebSocket manager
create_websocket_manager() {
    log "Creating compliance WebSocket manager..."

    cat > "$FRONTEND_DIR/lib/compliance-websocket.ts" << 'EOF'
import { ComplianceUpdate } from '@/components/compliance/types';

export interface UploadProgress {
  jobId: string;
  itemId: string;
  fileName: string;
  progress: number;
  status: 'pending' | 'uploading' | 'complete' | 'error';
}

export class ComplianceWebSocketManager {
  private connections: Map<string, WebSocket> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000; // Base interval in ms

  connect(assessmentId: string, onUpdate: (update: ComplianceUpdate) => void): void {
    if (this.connections.has(assessmentId)) {
      this.disconnect(assessmentId);
    }

    try {
      const wsUrl = this.getWebSocketUrl(assessmentId);
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

      ws.onclose = (event) => {
        console.log(`Compliance WebSocket closed for assessment ${assessmentId}`, event.code);
        this.handleReconnect(assessmentId, onUpdate);
      };

      ws.onerror = (error) => {
        console.error(`Compliance WebSocket error for assessment ${assessmentId}:`, error);
      };

      this.connections.set(assessmentId, ws);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.handleReconnect(assessmentId, onUpdate);
    }
  }

  disconnect(assessmentId: string): void {
    const ws = this.connections.get(assessmentId);
    if (ws) {
      ws.close();
      this.connections.delete(assessmentId);
      this.reconnectAttempts.delete(assessmentId);
    }
  }

  disconnectAll(): void {
    for (const [assessmentId] of this.connections) {
      this.disconnect(assessmentId);
    }
  }

  private getWebSocketUrl(assessmentId: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.host;
    return `${protocol}//${host}/api/compliance/ws/${assessmentId}`;
  }

  private handleReconnect(assessmentId: string, onUpdate: (update: ComplianceUpdate) => void): void {
    const attempts = this.reconnectAttempts.get(assessmentId) || 0;

    if (attempts < this.maxReconnectAttempts) {
      const delay = Math.min(this.reconnectInterval * Math.pow(2, attempts), 30000);

      setTimeout(() => {
        console.log(`Attempting to reconnect WebSocket for assessment ${assessmentId} (attempt ${attempts + 1})`);
        this.connect(assessmentId, onUpdate);
        this.reconnectAttempts.set(assessmentId, attempts + 1);
      }, delay);
    } else {
      console.error(`Max reconnection attempts reached for assessment ${assessmentId}`);
    }
  }

  isConnected(assessmentId: string): boolean {
    const ws = this.connections.get(assessmentId);
    return ws ? ws.readyState === WebSocket.OPEN : false;
  }

  getConnectionStatus(assessmentId: string): string {
    const ws = this.connections.get(assessmentId);
    if (!ws) return 'disconnected';

    switch (ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'connected';
      case WebSocket.CLOSING: return 'closing';
      case WebSocket.CLOSED: return 'closed';
      default: return 'unknown';
    }
  }
}

export const complianceWebSocketManager = new ComplianceWebSocketManager();

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    complianceWebSocketManager.disconnectAll();
  });
}
EOF

    success "WebSocket manager created"
}

# Create Compliance Context
create_compliance_context() {
    log "Creating Compliance Context..."

    cat > "$FRONTEND_DIR/contexts/ComplianceContext.tsx" << 'EOF'
'use client';

import React, { createContext, useContext, useReducer, useEffect, ReactNode, useCallback } from 'react';
import { ComplianceStatusState, ComplianceCheck, ComplianceUpdate } from '@/components/compliance/types';
import { complianceWebSocketManager } from '@/lib/compliance-websocket';

interface ComplianceContextActions {
  initializeCompliance: (propertyId: string, developmentType: any) => Promise<void>;
  refreshStatus: (force?: boolean) => Promise<void>;
  subscribeToUpdates: (assessmentId: string) => void;
  unsubscribeFromUpdates: (assessmentId: string) => void;
  runComplianceCheck: (checkId: string) => Promise<void>;
  updateCheckStatus: (checkId: string, status: ComplianceCheck['status']) => void;
  toggleAutoRefresh: (enabled: boolean) => void;
  exportComplianceReport: () => Promise<Blob>;
}

interface ComplianceContextState {
  status: ComplianceStatusState;
  isLoading: boolean;
  error: string | null;
  subscriptions: Map<string, boolean>;
  refreshInterval: number;
  lastRefresh: Date;
}

type ComplianceAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_STATUS'; payload: ComplianceStatusState }
  | { type: 'UPDATE_CHECK'; payload: { checkId: string; updates: Partial<ComplianceCheck> } }
  | { type: 'SET_AUTO_REFRESH'; payload: boolean }
  | { type: 'ADD_SUBSCRIPTION'; payload: string }
  | { type: 'REMOVE_SUBSCRIPTION'; payload: string }
  | { type: 'SET_LAST_REFRESH'; payload: Date };

const initialState: ComplianceContextState = {
  status: {
    overallStatus: 'not-started',
    checks: [],
    progress: { completed: 0, total: 0, percentage: 0 },
    criticalIssues: [],
    warnings: [],
    lastUpdated: new Date(),
    autoRefreshEnabled: false,
  },
  isLoading: false,
  error: null,
  subscriptions: new Map(),
  refreshInterval: 30000, // 30 seconds
  lastRefresh: new Date(),
};

const complianceReducer = (
  state: ComplianceContextState,
  action: ComplianceAction
): ComplianceContextState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    case 'SET_STATUS':
      return { ...state, status: action.payload, isLoading: false, error: null };
    case 'UPDATE_CHECK': {
      const updatedChecks = state.status.checks.map(check =>
        check.id === action.payload.checkId
          ? { ...check, ...action.payload.updates }
          : check
      );

      const newStatus = { ...state.status, checks: updatedChecks };
      newStatus.progress = calculateProgress(updatedChecks);
      newStatus.criticalIssues = updatedChecks.filter(
        check => check.severity === 'critical' && check.status === 'non-compliant'
      );
      newStatus.warnings = updatedChecks.filter(
        check => check.status === 'conditional' ||
        (check.severity === 'major' && check.status === 'non-compliant')
      );

      return { ...state, status: newStatus };
    }
    case 'SET_AUTO_REFRESH':
      return {
        ...state,
        status: { ...state.status, autoRefreshEnabled: action.payload }
      };
    case 'ADD_SUBSCRIPTION':
      const newSubscriptions = new Map(state.subscriptions);
      newSubscriptions.set(action.payload, true);
      return { ...state, subscriptions: newSubscriptions };
    case 'REMOVE_SUBSCRIPTION':
      const updatedSubscriptions = new Map(state.subscriptions);
      updatedSubscriptions.delete(action.payload);
      return { ...state, subscriptions: updatedSubscriptions };
    case 'SET_LAST_REFRESH':
      return { ...state, lastRefresh: action.payload };
    default:
      return state;
  }
};

function calculateProgress(checks: ComplianceCheck[]) {
  const total = checks.length;
  const completed = checks.filter(
    check => check.status !== 'pending' && check.status !== 'not-applicable'
  ).length;

  return {
    completed,
    total,
    percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
  };
}

const ComplianceContext = createContext<
  (ComplianceContextState & ComplianceContextActions) | null
>(null);

export const useComplianceContext = () => {
  const context = useContext(ComplianceContext);
  if (!context) {
    throw new Error('useComplianceContext must be used within a ComplianceProvider');
  }
  return context;
};

interface ComplianceProviderProps {
  children: ReactNode;
}

export const ComplianceProvider: React.FC<ComplianceProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(complianceReducer, initialState);

  const initializeCompliance = useCallback(async (propertyId: string, developmentType: any) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      const response = await fetch('/api/compliance/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ propertyId, developmentType }),
      });

      if (!response.ok) {
        throw new Error('Failed to initialize compliance status');
      }

      const status = await response.json();
      dispatch({ type: 'SET_STATUS', payload: status });
      dispatch({ type: 'SET_LAST_REFRESH', payload: new Date() });
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }, []);

  const refreshStatus = useCallback(async (force = false) => {
    if (state.isLoading && !force) return;

    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      const response = await fetch('/api/compliance/status');
      if (!response.ok) {
        throw new Error('Failed to refresh compliance status');
      }

      const status = await response.json();
      dispatch({ type: 'SET_STATUS', payload: status });
      dispatch({ type: 'SET_LAST_REFRESH', payload: new Date() });
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }, [state.isLoading]);

  const subscribeToUpdates = useCallback((assessmentId: string) => {
    if (state.subscriptions.has(assessmentId)) return;

    const handleUpdate = (update: ComplianceUpdate) => {
      switch (update.type) {
        case 'status_change':
          if (update.checkId && update.status) {
            dispatch({
              type: 'UPDATE_CHECK',
              payload: {
                checkId: update.checkId,
                updates: { status: update.status, lastChecked: update.timestamp },
              },
            });
          }
          break;
        case 'check_complete':
          if (update.checkId) {
            dispatch({
              type: 'UPDATE_CHECK',
              payload: {
                checkId: update.checkId,
                updates: { lastChecked: update.timestamp },
              },
            });
          }
          break;
        case 'error':
          dispatch({ type: 'SET_ERROR', payload: update.message || 'WebSocket error' });
          break;
      }
    };

    complianceWebSocketManager.connect(assessmentId, handleUpdate);
    dispatch({ type: 'ADD_SUBSCRIPTION', payload: assessmentId });
  }, [state.subscriptions]);

  const unsubscribeFromUpdates = useCallback((assessmentId: string) => {
    complianceWebSocketManager.disconnect(assessmentId);
    dispatch({ type: 'REMOVE_SUBSCRIPTION', payload: assessmentId });
  }, []);

  const runComplianceCheck = useCallback(async (checkId: string) => {
    try {
      const response = await fetch(`/api/compliance/check/${checkId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to run compliance check');
      }

      // WebSocket will handle the update
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }, []);

  const updateCheckStatus = useCallback((checkId: string, status: ComplianceCheck['status']) => {
    dispatch({
      type: 'UPDATE_CHECK',
      payload: {
        checkId,
        updates: { status, lastChecked: new Date() },
      },
    });
  }, []);

  const toggleAutoRefresh = useCallback((enabled: boolean) => {
    dispatch({ type: 'SET_AUTO_REFRESH', payload: enabled });
  }, []);

  const exportComplianceReport = useCallback(async (): Promise<Blob> => {
    const response = await fetch('/api/compliance/export');
    if (!response.ok) {
      throw new Error('Failed to export compliance report');
    }
    return response.blob();
  }, []);

  // Auto-refresh effect
  useEffect(() => {
    if (!state.status.autoRefreshEnabled) return;

    const interval = setInterval(() => {
      refreshStatus();
    }, state.refreshInterval);

    return () => clearInterval(interval);
  }, [state.status.autoRefreshEnabled, state.refreshInterval, refreshStatus]);

  const contextValue = {
    ...state,
    initializeCompliance,
    refreshStatus,
    subscribeToUpdates,
    unsubscribeFromUpdates,
    runComplianceCheck,
    updateCheckStatus,
    toggleAutoRefresh,
    exportComplianceReport,
  };

  return (
    <ComplianceContext.Provider value={contextValue}>
      {children}
    </ComplianceContext.Provider>
  );
};
EOF

    success "Compliance Context created"
}

# Create supporting components
create_supporting_components() {
    log "Creating supporting components..."

    # ComplianceMetricCard
    cat > "$FRONTEND_DIR/components/compliance/ComplianceMetricCard.tsx" << 'EOF'
import React from 'react';

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
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  );
};
EOF

    # ComplianceProgressBar
    cat > "$FRONTEND_DIR/components/compliance/ComplianceProgressBar.tsx" << 'EOF'
import React from 'react';

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

  const getProgressColor = (progress: number) => {
    if (progress >= 100) return 'bg-green-500';
    if (progress >= 75) return 'bg-blue-500';
    if (progress >= 50) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  return (
    <div className="mt-4">
      {showLabel && (
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full ${heightClasses[height]}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ${getProgressColor(progress)}`}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  );
};
EOF

    # ComplianceGroup
    cat > "$FRONTEND_DIR/components/compliance/ComplianceGroup.tsx" << 'EOF'
import React, { useMemo } from 'react';
import { ComplianceCheck } from './types';

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant': return 'bg-green-100 text-green-800 border-green-200';
      case 'non-compliant': return 'bg-red-100 text-red-800 border-red-200';
      case 'conditional': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'not-applicable': return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'pending': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
      >
        <div className="flex items-center space-x-3">
          <span className={`transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
            ▶
          </span>
          <h3 className="font-medium text-gray-900">{title}</h3>
          <span className="text-sm text-gray-500">({checks.length} checks)</span>
        </div>
        <div className="flex items-center space-x-2">
          {Object.entries(statusCounts).map(([status, count]) => (
            <span
              key={status}
              className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(status)}`}
            >
              {count}
            </span>
          ))}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-200">
          {checks.map((check) => (
            <div key={check.id} className="px-6 py-4 border-b border-gray-100 last:border-b-0">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="font-mono text-sm text-gray-500">{check.provision}</span>
                    <span className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(check.status)}`}>
                      {check.status.replace('-', ' ')}
                    </span>
                    {check.severity === 'critical' && (
                      <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                        Critical
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-900 mb-1">{check.requirement}</p>
                  {check.recommendations && check.recommendations.length > 0 && (
                    <div className="text-sm text-gray-600">
                      <strong>Recommendations:</strong> {check.recommendations.join(', ')}
                    </div>
                  )}
                </div>
                <div className="ml-4">
                  <button
                    onClick={() => onRunCheck(check.id)}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Re-check
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
EOF

    success "Supporting components created"
}

# Create Enhanced ComplianceStatus component
create_enhanced_status() {
    log "Creating Enhanced ComplianceStatus component..."

    cat > "$FRONTEND_DIR/components/compliance/EnhancedComplianceStatus.tsx" << 'EOF'
'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { useComplianceContext } from '@/contexts/ComplianceContext';
import { ComplianceMetricCard } from './ComplianceMetricCard';
import { ComplianceProgressBar } from './ComplianceProgressBar';
import { ComplianceGroup } from './ComplianceGroup';
import { ComplianceStatusProps, ComplianceCheck } from './types';

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
    toggleAutoRefresh,
    initializeCompliance
  } = useComplianceContext();

  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [sortBy, setSortBy] = useState<'severity' | 'lastChecked' | 'provision'>('severity');

  // Initialize compliance on mount
  useEffect(() => {
    if (propertyId && developmentType) {
      initializeCompliance(propertyId, developmentType);
    }
  }, [propertyId, developmentType, initializeCompliance]);

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

  const getOverallStatusColor = (overallStatus: string) => {
    switch (overallStatus) {
      case 'pass': return 'text-green-600';
      case 'fail': return 'text-red-600';
      case 'conditional': return 'text-yellow-600';
      case 'incomplete': return 'text-blue-600';
      default: return 'text-gray-600';
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
        <div className={`w-3 h-3 rounded-full ${getOverallStatusColor(status.overallStatus).replace('text-', 'bg-')}`} />
        <span className="text-sm font-medium">
          {status.progress.completed}/{status.progress.total} checks complete
        </span>
      </div>
    );
  }

  return (
    <div className={`compliance-status ${variant === 'summary' ? 'compact-view' : ''}`}>
      {/* Header with Overall Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Compliance Status</h2>
          <div className="flex items-center space-x-2">
            {autoRefresh && (
              <div className="flex items-center text-sm text-gray-500">
                <span className="w-4 h-4 mr-1">🔄</span>
                Auto-refresh
              </div>
            )}
            <button
              onClick={() => refreshStatus(true)}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
            >
              <span className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}>↻</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <ComplianceMetricCard
            title="Overall Status"
            value={status.overallStatus.replace('-', ' ')}
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
EOF

    success "Enhanced ComplianceStatus component created"
}

# Create main ComplianceStatus with feature flag integration
create_main_status() {
    log "Creating main ComplianceStatus with feature flag integration..."

    cat > "$FRONTEND_DIR/components/compliance/ComplianceStatus.tsx" << 'EOF'
'use client';

import React from 'react';
import { withFeatureFlagSafeguard } from '@/lib/feature-flag-safeguards';
import { EnhancedComplianceStatus } from './EnhancedComplianceStatus';
import { ComplianceStatusProps } from './types';

// Legacy component placeholder
const LegacyComplianceStatus: React.FC<ComplianceStatusProps> = (props) => {
  return (
    <div className="p-4 border border-gray-300 rounded-md bg-gray-50">
      <p className="text-gray-600">Legacy Compliance Status</p>
      <p className="text-sm text-gray-500">Feature flag disabled - using legacy component</p>
    </div>
  );
};

// Feature flag wrapped component
export const ComplianceStatus = withFeatureFlagSafeguard(
  'newComplianceStatus',
  EnhancedComplianceStatus,
  LegacyComplianceStatus,
  {
    errorBoundary: true,
    performanceMonitoring: true,
  }
);

export default ComplianceStatus;
EOF

    success "Main ComplianceStatus component created"
}

# Create API endpoints
create_api_endpoints() {
    log "Creating compliance API endpoints..."

    # Compliance status endpoint
    cat > "$FRONTEND_DIR/pages/api/compliance/status.ts" << 'EOF'
import { NextApiRequest, NextApiResponse } from 'next';
import { ComplianceStatusState, ComplianceCheck } from '@/components/compliance/types';

// Mock compliance checks data
const generateMockChecks = (): ComplianceCheck[] => [
  {
    id: '1',
    provision: '4.6.1',
    requirement: 'Building height must not exceed 24m',
    status: 'compliant',
    severity: 'critical',
    evidence: [],
    recommendations: [],
    lastChecked: new Date(),
    autoCheckEnabled: true,
  },
  {
    id: '2',
    provision: '4.6.2',
    requirement: 'Floor space ratio must not exceed 1.2:1',
    status: 'pending',
    severity: 'major',
    evidence: [],
    recommendations: ['Submit architectural plans for review'],
    lastChecked: new Date(),
    autoCheckEnabled: true,
  },
  {
    id: '3',
    provision: '4.6.3',
    requirement: 'Minimum 3m front setback required',
    status: 'non-compliant',
    severity: 'major',
    evidence: [],
    recommendations: ['Adjust building placement to meet setback requirements'],
    lastChecked: new Date(),
    autoCheckEnabled: true,
  },
  {
    id: '4',
    provision: '4.6.4',
    requirement: 'Minimum 20 parking spaces required',
    status: 'conditional',
    severity: 'minor',
    evidence: [],
    recommendations: ['Provide parking calculation based on development mix'],
    lastChecked: new Date(),
    autoCheckEnabled: true,
  },
];

function calculateComplianceStatus(checks: ComplianceCheck[]): ComplianceStatusState {
  const total = checks.length;
  const completed = checks.filter(check =>
    check.status !== 'pending' && check.status !== 'not-applicable'
  ).length;

  const criticalIssues = checks.filter(check =>
    check.severity === 'critical' && check.status === 'non-compliant'
  );

  const warnings = checks.filter(check =>
    check.status === 'conditional' ||
    (check.severity === 'major' && check.status === 'non-compliant')
  );

  const nonCompliantChecks = checks.filter(check => check.status === 'non-compliant');

  let overallStatus: ComplianceStatusState['overallStatus'];
  if (criticalIssues.length > 0) {
    overallStatus = 'fail';
  } else if (warnings.length > 0 || nonCompliantChecks.length > 0) {
    overallStatus = 'conditional';
  } else if (completed < total) {
    overallStatus = 'incomplete';
  } else {
    overallStatus = 'pass';
  }

  return {
    overallStatus,
    checks,
    progress: {
      completed,
      total,
      percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
    },
    criticalIssues,
    warnings,
    lastUpdated: new Date(),
    autoRefreshEnabled: false,
  };
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    if (req.method === 'POST') {
      // Initialize compliance status
      const { propertyId, developmentType } = req.body;

      if (!propertyId || !developmentType) {
        return res.status(400).json({ error: 'Property ID and development type required' });
      }

      const checks = generateMockChecks();
      const status = calculateComplianceStatus(checks);

      return res.status(200).json(status);
    }

    if (req.method === 'GET') {
      // Get current compliance status
      const checks = generateMockChecks();
      const status = calculateComplianceStatus(checks);

      return res.status(200).json(status);
    }

    res.status(405).json({ error: 'Method not allowed' });
  } catch (error) {
    console.error('Compliance status API error:', error);
    res.status(500).json({ error: 'Failed to process compliance status' });
  }
}
EOF

    # Compliance check endpoint
    cat > "$FRONTEND_DIR/pages/api/compliance/check/[checkId].ts" << 'EOF'
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { checkId } = req.query;

    if (!checkId || typeof checkId !== 'string') {
      return res.status(400).json({ error: 'Check ID required' });
    }

    // Simulate check execution
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Mock result
    const result = {
      checkId,
      status: Math.random() > 0.5 ? 'compliant' : 'non-compliant',
      lastChecked: new Date(),
      message: 'Check completed successfully',
    };

    res.status(200).json(result);
  } catch (error) {
    console.error('Compliance check API error:', error);
    res.status(500).json({ error: 'Failed to run compliance check' });
  }
}
EOF

    success "API endpoints created"
}

# Create unit tests
create_unit_tests() {
    log "Creating unit tests..."

    # ComplianceStatus tests
    cat > "$FRONTEND_DIR/__tests__/components/compliance/ComplianceStatus.test.tsx" << 'EOF'
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { ComplianceProvider } from '@/contexts/ComplianceContext';
import { EnhancedComplianceStatus } from '@/components/compliance/EnhancedComplianceStatus';

// Mock fetch
global.fetch = jest.fn();

const mockComplianceStatus = {
  overallStatus: 'conditional' as const,
  checks: [
    {
      id: '1',
      provision: '4.6.1',
      requirement: 'Building height must not exceed 24m',
      status: 'compliant' as const,
      severity: 'critical' as const,
      evidence: [],
      recommendations: [],
      lastChecked: new Date(),
      autoCheckEnabled: true,
    },
    {
      id: '2',
      provision: '4.6.2',
      requirement: 'Floor space ratio must not exceed 1.2:1',
      status: 'non-compliant' as const,
      severity: 'major' as const,
      evidence: [],
      recommendations: ['Submit architectural plans'],
      lastChecked: new Date(),
      autoCheckEnabled: true,
    },
  ],
  progress: { completed: 2, total: 2, percentage: 100 },
  criticalIssues: [],
  warnings: [],
  lastUpdated: new Date(),
  autoRefreshEnabled: false,
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <FeatureFlagProvider>
    <ComplianceProvider>
      {children}
    </ComplianceProvider>
  </FeatureFlagProvider>
);

const defaultProps = {
  propertyId: 'test-property',
  developmentType: { id: '1', name: 'Test Development' },
};

describe('EnhancedComplianceStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockComplianceStatus),
    });
  });

  test('renders compliance status', async () => {
    render(
      <TestWrapper>
        <EnhancedComplianceStatus {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Compliance Status')).toBeInTheDocument();
    });
  });

  test('displays progress metrics', async () => {
    render(
      <TestWrapper>
        <EnhancedComplianceStatus {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Overall Status')).toBeInTheDocument();
      expect(screen.getByText('Progress')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  test('shows compliance checks when expanded', async () => {
    render(
      <TestWrapper>
        <EnhancedComplianceStatus {...defaultProps} showDetails />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Building height must not exceed 24m')).toBeInTheDocument();
    });
  });

  test('filters issues when toggle is enabled', async () => {
    render(
      <TestWrapper>
        <EnhancedComplianceStatus {...defaultProps} showDetails />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Show only issues')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('Show only issues'));

    // Should only show non-compliant items
    await waitFor(() => {
      expect(screen.getByText('Floor space ratio must not exceed 1.2:1')).toBeInTheDocument();
    });
  });

  test('renders minimal variant', () => {
    render(
      <TestWrapper>
        <EnhancedComplianceStatus {...defaultProps} variant="minimal" />
      </TestWrapper>
    );

    expect(screen.getByText(/checks complete/)).toBeInTheDocument();
  });
});
EOF

    # WebSocket tests
    cat > "$FRONTEND_DIR/__tests__/lib/compliance-websocket.test.ts" << 'EOF'
import { ComplianceWebSocketManager } from '@/lib/compliance-websocket';

// Mock WebSocket
class MockWebSocket {
  readyState = WebSocket.CONNECTING;
  onopen?: () => void;
  onmessage?: (event: { data: string }) => void;
  onclose?: (event: { code: number }) => void;
  onerror?: (error: any) => void;

  constructor(url: string) {}

  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.({ code: 1000 });
  }

  send(data: string) {}
}

// @ts-ignore
global.WebSocket = MockWebSocket;

describe('ComplianceWebSocketManager', () => {
  let manager: ComplianceWebSocketManager;

  beforeEach(() => {
    manager = new ComplianceWebSocketManager();
  });

  afterEach(() => {
    manager.disconnectAll();
  });

  test('connects to WebSocket', () => {
    const onUpdate = jest.fn();

    manager.connect('test-assessment', onUpdate);

    expect(manager.getConnectionStatus('test-assessment')).toBe('connecting');
  });

  test('handles WebSocket messages', () => {
    const onUpdate = jest.fn();

    manager.connect('test-assessment', onUpdate);

    // Simulate connection opening
    const ws = (manager as any).connections.get('test-assessment');
    ws.readyState = WebSocket.OPEN;
    ws.onopen?.();

    // Simulate message
    const mockUpdate = {
      type: 'status_change',
      checkId: 'test-check',
      status: 'compliant',
      timestamp: new Date(),
    };

    ws.onmessage?.({ data: JSON.stringify(mockUpdate) });

    expect(onUpdate).toHaveBeenCalledWith(mockUpdate);
  });

  test('disconnects WebSocket', () => {
    const onUpdate = jest.fn();

    manager.connect('test-assessment', onUpdate);
    manager.disconnect('test-assessment');

    expect(manager.getConnectionStatus('test-assessment')).toBe('disconnected');
  });

  test('returns correct connection status', () => {
    expect(manager.isConnected('test-assessment')).toBe(false);

    const onUpdate = jest.fn();
    manager.connect('test-assessment', onUpdate);

    const ws = (manager as any).connections.get('test-assessment');
    ws.readyState = WebSocket.OPEN;

    expect(manager.isConnected('test-assessment')).toBe(true);
  });
});
EOF

    success "Unit tests created"
}

# Create component index
create_component_index() {
    log "Creating compliance component index..."

    cat > "$FRONTEND_DIR/components/compliance/index.ts" << 'EOF'
export { ComplianceStatus as default } from './ComplianceStatus';
export { EnhancedComplianceStatus } from './EnhancedComplianceStatus';
export { ComplianceMetricCard } from './ComplianceMetricCard';
export { ComplianceProgressBar } from './ComplianceProgressBar';
export { ComplianceGroup } from './ComplianceGroup';
export type {
  ComplianceCheck,
  Evidence,
  ComplianceStatusState,
  ComplianceStatusProps,
  ComplianceUpdate
} from './types';
EOF

    success "Component index created"
}

# Run verification
run_verification() {
    log "Running PRP-UI3 verification..."

    cd "$PRP_DIR"
    python verify_ui_migration.py --project-root "$PROJECT_ROOT" ui3 --detailed

    if [[ $? -eq 0 ]]; then
        success "PRP-UI3 verification passed"
    else
        error "PRP-UI3 verification failed"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting PRP-UI3 execution: ComplianceStatus Component Migration"
    log "Project root: $PROJECT_ROOT"
    log "Frontend directory: $FRONTEND_DIR"

    check_prerequisites
    create_directories
    create_compliance_types
    create_websocket_manager
    create_compliance_context
    create_supporting_components
    create_enhanced_status
    create_main_status
    create_api_endpoints
    create_unit_tests
    create_component_index
    run_verification

    success "PRP-UI3 execution completed successfully!"
    log "ComplianceStatus migration is ready"
    log "Next steps:"
    log "  1. Enable 'newComplianceStatus' feature flag"
    log "  2. Test real-time updates functionality"
    log "  3. Verify WebSocket connections work properly"
    log "  4. Proceed with PRP-UI4: ComplianceChecklist migration"
}

# Execute main function
main "$@"