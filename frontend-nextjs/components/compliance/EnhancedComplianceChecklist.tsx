'use client';

import React, { useState, useEffect } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { ChecklistItem } from './ChecklistItem';
import { EvidenceSection } from './EvidenceSection';
import type { ComplianceItem } from './types';

export type { ComplianceItem };

interface EnhancedComplianceChecklistProps {
 propertyId?: string;
 developmentType?: string;
 zoneCode?: string;
 onStatusChange?: (itemId: string, status: string) => void;
}

export const EnhancedComplianceChecklist: React.FC<EnhancedComplianceChecklistProps> = ({
 propertyId,
 developmentType,
 zoneCode,
 onStatusChange
}) => {
 const { flags } = useFeatureFlags();
 const [items, setItems] = useState<ComplianceItem[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);
 const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

 useEffect(() => {
 if (propertyId && developmentType) {
 loadComplianceData();
 }
 }, [propertyId, developmentType, zoneCode]);

 const loadComplianceData = async () => {
 try {
 setLoading(true);
 setError(null);

 const params = new URLSearchParams();
 if (propertyId) params.append('propertyId', propertyId);
 if (developmentType) params.append('developmentType', developmentType);
 if (zoneCode) params.append('zoneCode', zoneCode);

 const response = await fetch(`/api/compliance/checklist?${params}`);
 if (!response.ok) {
 throw new Error('Failed to load compliance data');
 }

 const data = await response.json();
 setItems(data.items || []);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to load compliance data');
 } finally {
 setLoading(false);
 }
 };

 const handleStatusChange = (itemId: string, newStatus: string) => {
 setItems(prevItems =>
 prevItems.map(item =>
 item.id === itemId ? { ...item, status: newStatus as ComplianceItem['status'] } : item
 )
 );
 onStatusChange?.(itemId, newStatus);
 };

 const toggleExpanded = (itemId: string) => {
 setExpandedItems(prev => {
 const newSet = new Set(prev);
 if (newSet.has(itemId)) {
 newSet.delete(itemId);
 } else {
 newSet.add(itemId);
 }
 return newSet;
 });
 };

 const getComplianceStats = () => {
 const total = items.length;
 const compliant = items.filter(item => item.status === 'compliant').length;
 const nonCompliant = items.filter(item => item.status === 'non-compliant').length;
 const pending = items.filter(item => item.status === 'pending').length;
 const notApplicable = items.filter(item => item.status === 'not-applicable').length;

 return { total, compliant, nonCompliant, pending, notApplicable };
 };

 const stats = getComplianceStats();
 const progressPercentage = stats.total > 0 ? Math.round((stats.compliant / stats.total) * 100) : 0;

 if (loading) {
 return (
 <div className="space-y-4">
 <div className="h-32 bg-gray-100 animate-pulse rounded-lg"></div>
 <div className="space-y-2">
 {[...Array(5)].map((_, i) => (
 <div key={i} className="h-16 bg-gray-100 animate-pulse rounded"></div>
 ))}
 </div>
 </div>
 );
 }

 if (error) {
 return (
 <div className="bg-red-50 border border-red-200 rounded-lg p-4">
 <h3 className="text-red-800 font-medium">Error Loading Compliance Data</h3>
 <p className="text-red-700 text-sm mt-1">{error}</p>
 <button
 onClick={loadComplianceData}
 className="mt-2 text-red-700 hover:text-red-900 text-sm underline"
 >
 Try Again
 </button>
 </div>
 );
 }

 return (
 <div className="space-y-6">
 {/* Header with Progress */}
 <div className="bg-white border rounded-lg p-6">
 <div className="flex items-center justify-between mb-4">
 <h2 className="text-xl font-semibold text-gray-900">
 Compliance Checklist
 </h2>
 <div className="text-sm text-gray-600">
 {stats.compliant}/{stats.total} items compliant
 </div>
 </div>

 {/* Progress Bar */}
 <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
 <div
 className="bg-green-600 h-2 rounded-full transition-all duration-300"
 style={{ width: `${progressPercentage}%` }}
 ></div>
 </div>

 {/* Stats */}
 <div className="grid grid-cols-4 gap-4 text-center">
 <div>
 <div className="text-2xl font-bold text-green-600">{stats.compliant}</div>
 <div className="text-xs text-gray-600">Compliant</div>
 </div>
 <div>
 <div className="text-2xl font-bold text-red-600">{stats.nonCompliant}</div>
 <div className="text-xs text-gray-600">Non-Compliant</div>
 </div>
 <div>
 <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
 <div className="text-xs text-gray-600">Pending</div>
 </div>
 <div>
 <div className="text-2xl font-bold text-gray-600">{stats.notApplicable}</div>
 <div className="text-xs text-gray-600">N/A</div>
 </div>
 </div>
 </div>

 {/* Checklist Items */}
 <div className="space-y-3">
 {items.map((item) => (
 <ChecklistItem
 key={item.id}
 item={item}
 isExpanded={expandedItems.has(item.id)}
 onToggleExpanded={() => toggleExpanded(item.id)}
 onStatusChange={(status) => handleStatusChange(item.id, status)}
 />
 ))}
 </div>

 {/* Evidence Section */}
 {flags.newComplianceChecklist && (
 <EvidenceSection
 items={items}
 onEvidenceUpdate={(itemId, evidence) => {
 setItems(prevItems =>
 prevItems.map(item =>
 item.id === itemId ? { ...item, evidence } : item
 )
 );
 }}
 />
 )}

 {items.length === 0 && (
 <div className="text-center py-8 text-gray-500">
 No compliance items found for this development type and zone.
 </div>
 )}
 </div>
 );
};