import React from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';

interface SafeguardOptions {
 errorBoundary?: boolean;
 performanceMonitoring?: boolean;
 fallbackTimeout?: number;
}

export function withFeatureFlagSafeguard<T extends Record<string, any>>(
 flagName: string,
 WrappedComponent: React.ComponentType<T>,
 FallbackComponent: React.ComponentType<T>,
 options: SafeguardOptions = {}
) {
 const SafeguardedComponent: React.FC<T> = (props) => {
 const { flags } = useFeatureFlags();

 const isEnabled = flags[flagName as keyof typeof flags] === true;

 if (isEnabled) {
 return React.createElement(WrappedComponent, props);
 } else {
 return React.createElement(FallbackComponent, props);
 }
 };

 SafeguardedComponent.displayName = `withFeatureFlagSafeguard(${flagName})`;

 return SafeguardedComponent;
}

export default withFeatureFlagSafeguard;