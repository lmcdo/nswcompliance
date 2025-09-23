'use client';

import React from 'react';
import { withFeatureFlagSafeguard } from '@/lib/feature-flag-safeguards';
import { EnhancedDevelopmentSelector } from './EnhancedDevelopmentSelector';
import { DevelopmentSelectorProps } from './types';

// Legacy component placeholder
const LegacyDevelopmentSelector: React.FC<DevelopmentSelectorProps> = (props) => {
 return (
 <div className="p-4 border border-gray-300 rounded-md bg-gray-50">
 <p className="text-gray-600">Legacy Development Selector</p>
 <p className="text-sm text-gray-500">Feature flag disabled - using legacy component</p>
 </div>
 );
};

// Feature flag wrapped component
export const DevelopmentSelector = withFeatureFlagSafeguard(
 'newDevelopmentSelector',
 EnhancedDevelopmentSelector,
 LegacyDevelopmentSelector,
 {
 errorBoundary: true,
 performanceMonitoring: true,
 }
);

export default DevelopmentSelector;
