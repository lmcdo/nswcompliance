'use client';

import React from 'react';
import { AssessmentStorage } from '@/lib/assessment/storage';
import { APICache } from '@/lib/assessment/cache';

interface StateIndicatorProps {
 isDirty: boolean;
 lastSaved: string | null;
 autoSaveEnabled: boolean;
 className?: string;
}

export function StateIndicator({
 isDirty,
 lastSaved,
 autoSaveEnabled,
 className = ''
}: StateIndicatorProps) {
 const getStatusColor = () => {
 if (!lastSaved) return 'text-gray-500';
 if (isDirty) return 'text-yellow-600';
 return 'text-green-600';
 };

 const getStatusText = () => {
 if (!lastSaved) return 'Not saved';
 if (isDirty) return autoSaveEnabled ? 'Saving...' : 'Unsaved changes';
 return 'Saved';
 };

 return (
 <div className={`flex items-center gap-2 text-sm ${getStatusColor()} ${className}`}>
 <div className={`w-2 h-2 rounded-full ${
 !lastSaved ? 'bg-gray-400' :
 isDirty ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'
 }`} />
 <span>{getStatusText()}</span>
 {lastSaved && (
 <span className="text-gray-400">
 • {new Date(lastSaved).toLocaleTimeString()}
 </span>
 )}
 </div>
 );
}

interface AutoSaveToggleProps {
 enabled: boolean;
 onToggle: () => void;
 className?: string;
}

export function AutoSaveToggle({ enabled, onToggle, className = '' }: AutoSaveToggleProps) {
 return (
 <label className={`flex items-center gap-2 cursor-pointer ${className}`}>
 <input
 type="checkbox"
 checked={enabled}
 onChange={onToggle}
 className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
 />
 <span className="text-sm text-gray-700">Auto-save</span>
 </label>
 );
}

interface SaveActionsProps {
 onSave: () => void;
 onClear: () => void;
 isDirty: boolean;
 lastSaved: string | null;
 className?: string;
}

export function SaveActions({
 onSave,
 onClear,
 isDirty,
 lastSaved,
 className = ''
}: SaveActionsProps) {
 return (
 <div className={`flex gap-2 ${className}`}>
 <button
 onClick={onSave}
 disabled={!isDirty}
 className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
 >
 Save Now
 </button>
 <button
 onClick={onClear}
 disabled={!lastSaved}
 className="px-3 py-1 border border-gray-300 text-gray-700 rounded text-sm hover:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
 >
 Clear Saved
 </button>
 </div>
 );
}

interface CacheStatsProps {
 className?: string;
}

export function CacheStats({ className = '' }: CacheStatsProps) {
 const [cacheStats, setCacheStats] = React.useState<any>(null);
 const [storageStats, setStorageStats] = React.useState<any>(null);

 React.useEffect(() => {
 const updateStats = () => {
 setCacheStats(APICache.getStats());
 setStorageStats(AssessmentStorage.getStorageStats());
 };

 updateStats();
 const interval = setInterval(updateStats, 5000); // Update every 5 seconds

 return () => clearInterval(interval);
 }, []);

 if (!cacheStats || !storageStats) return null;

 return (
 <div className={`bg-gray-50 border rounded-lg p-4 ${className}`}>
 <h4 className="font-semibold text-gray-800 mb-3">Performance Stats</h4>

 <div className="grid grid-cols-2 gap-4 text-sm">
 <div>
 <div className="font-medium text-gray-700 mb-1">API Cache</div>
 <div className="text-gray-600">
 {cacheStats.size} entries
 </div>
 </div>

 <div>
 <div className="font-medium text-gray-700 mb-1">Storage</div>
 <div className="text-gray-600">
 {storageStats.assessmentKeys} saved items
 </div>
 </div>
 </div>

 <div className="mt-3 pt-3 border-t border-gray-200">
 <button
 onClick={() => {
 APICache.clear();
 AssessmentStorage.clearAll();
 setCacheStats(APICache.getStats());
 setStorageStats(AssessmentStorage.getStorageStats());
 }}
 className="text-sm text-red-600 hover:text-red-700 transition-colors"
 >
 Clear All Cache & Storage
 </button>
 </div>
 </div>
 );
}

interface StateManagementPanelProps {
 isDirty: boolean;
 lastSaved: string | null;
 autoSaveEnabled: boolean;
 onToggleAutoSave: () => void;
 onSave: () => void;
 onClear: () => void;
 className?: string;
}

export function StateManagementPanel({
 isDirty,
 lastSaved,
 autoSaveEnabled,
 onToggleAutoSave,
 onSave,
 onClear,
 className = ''
}: StateManagementPanelProps) {
 return (
 <div className={`bg-white border rounded-lg p-4 ${className}`}>
 <h3 className="font-semibold text-gray-800 mb-4">State Management</h3>

 <div className="space-y-4">
 <StateIndicator
 isDirty={isDirty}
 lastSaved={lastSaved}
 autoSaveEnabled={autoSaveEnabled}
 />

 <div className="flex items-center justify-between">
 <AutoSaveToggle
 enabled={autoSaveEnabled}
 onToggle={onToggleAutoSave}
 />

 <SaveActions
 onSave={onSave}
 onClear={onClear}
 isDirty={isDirty}
 lastSaved={lastSaved}
 />
 </div>

 <CacheStats />
 </div>
 </div>
 );
}
