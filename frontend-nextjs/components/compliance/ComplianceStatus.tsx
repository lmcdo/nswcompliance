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
