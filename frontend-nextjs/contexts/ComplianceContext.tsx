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
