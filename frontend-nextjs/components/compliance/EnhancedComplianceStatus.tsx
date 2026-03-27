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
 const [groupByState, setGroupBy] = useState(groupBy);

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
 case 'pass': return 'text-emerald-600';
 case 'fail': return 'text-rose-600';
 case 'conditional': return 'text-amber-600';
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
 <span className="w-4 h-4 mr-1"></span>
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
 color={status.criticalIssues.length > 0 ? 'text-rose-600' : 'text-emerald-600'}
 />
 <ComplianceMetricCard
 title="Warnings"
 value={status.warnings.length}
 color={status.warnings.length > 0 ? 'text-amber-600' : 'text-emerald-600'}
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
 value={groupByState}
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
