'use client';

import React, { useState, useEffect } from 'react';

interface VersionInfo {
 id: number;
 document_type: string;
 document_identifier: string;
 version_number: string;
 version_status: string;
 effective_date: string;
 change_summary?: string;
}

interface VersionSelectorProps {
 documentType: string;
 documentIdentifier: string;
 selectedDate?: string;
 onVersionChange?: (version: VersionInfo | null) => void;
 className?: string;
}

export default function VersionSelector({
 documentType,
 documentIdentifier,
 selectedDate,
 onVersionChange,
 className = ""
}: VersionSelectorProps) {
 const [currentVersion, setCurrentVersion] = useState<VersionInfo | null>(null);
 const [historicalVersion, setHistoricalVersion] = useState<VersionInfo | null>(null);
 const [loading, setLoading] = useState(false);
 const [useHistorical, setUseHistorical] = useState(false);

 useEffect(() => {
 loadVersions();
 }, [documentType, documentIdentifier, selectedDate]);

 useEffect(() => {
 if (onVersionChange) {
 onVersionChange(useHistorical ? historicalVersion : currentVersion);
 }
 }, [useHistorical, currentVersion, historicalVersion, onVersionChange]);

 const loadVersions = async () => {
 if (!documentType || !documentIdentifier) return;

 setLoading(true);
 try {
 // Load current version
 const currentResponse = await fetch(
 `/api/versions?action=current&documentType=${documentType}&documentIdentifier=${documentIdentifier}`
 );

 if (currentResponse.ok) {
 const currentData = await currentResponse.json();
 setCurrentVersion(currentData);
 }

 // Load historical version if date is specified
 if (selectedDate) {
 const historicalResponse = await fetch(
 `/api/versions?action=atDate&documentType=${documentType}&documentIdentifier=${documentIdentifier}&targetDate=${selectedDate}`
 );

 if (historicalResponse.ok) {
 const historicalData = await historicalResponse.json();
 setHistoricalVersion(historicalData);
 }
 }
 } catch (error) {
 console.error('Failed to load versions:', error);
 } finally {
 setLoading(false);
 }
 };

 if (loading) {
 return (
 <div className={`bg-white border rounded-lg p-4 ${className}`}>
 <div className="animate-pulse">
 <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
 <div className="h-3 bg-gray-200 rounded w-2/3"></div>
 </div>
 </div>
 );
 }

 return (
 <div className={`bg-white border rounded-lg p-4 ${className}`}>
 <h4 className="font-semibold mb-3">Document Version</h4>

 <div className="space-y-3">
 {/* Current Version */}
 <div className="flex items-center gap-3">
 <input
 type="radio"
 id="current-version"
 name="version-selection"
 checked={!useHistorical}
 onChange={() => setUseHistorical(false)}
 className="text-blue-600"
 />
 <label htmlFor="current-version" className="flex-1">
 <div className="font-medium">Current Version</div>
 {currentVersion && (
 <div className="text-sm text-gray-600">
 {currentVersion.version_number} - Effective {new Date(currentVersion.effective_date).toLocaleDateString()}
 </div>
 )}
 </label>
 <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
 CURRENT
 </span>
 </div>

 {/* Historical Version */}
 {selectedDate && historicalVersion && (
 <div className="flex items-center gap-3">
 <input
 type="radio"
 id="historical-version"
 name="version-selection"
 checked={useHistorical}
 onChange={() => setUseHistorical(true)}
 className="text-blue-600"
 />
 <label htmlFor="historical-version" className="flex-1">
 <div className="font-medium">Version at Assessment Date</div>
 <div className="text-sm text-gray-600">
 {historicalVersion.version_number} - Effective {new Date(historicalVersion.effective_date).toLocaleDateString()}
 </div>
 {historicalVersion.change_summary && (
 <div className="text-xs text-gray-500 mt-1">
 {historicalVersion.change_summary}
 </div>
 )}
 </label>
 <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
 HISTORICAL
 </span>
 </div>
 )}

 {selectedDate && !historicalVersion && (
 <div className="text-sm text-amber-600 bg-amber-50 p-2 rounded">
 No historical version found for {new Date(selectedDate).toLocaleDateString()}. Using current version.
 </div>
 )}
 </div>

 {/* Version Details */}
 {(useHistorical ? historicalVersion : currentVersion) && (
 <div className="mt-4 pt-3 border-t border-gray-200">
 <div className="text-xs text-gray-600 space-y-1">
 <div>Document: {documentType} - {documentIdentifier}</div>
 <div>Version: {(useHistorical ? historicalVersion : currentVersion)?.version_number}</div>
 <div>Status: {(useHistorical ? historicalVersion : currentVersion)?.version_status}</div>
 </div>
 </div>
 )}
 </div>
 );
}
