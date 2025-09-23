'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { FeatureFlags, FeatureFlagConfig, calculateFeatureFlags, DEFAULT_FLAGS } from '@/lib/feature-flags';

interface FeatureFlagContextType {
 flags: FeatureFlags;
 updateFlag: (key: keyof FeatureFlags, value: boolean) => void;
 toggleFlag: (key: keyof FeatureFlags) => void;
 resetFlags: () => void;
 isLoading: boolean;
 error: string | null;
}

const FeatureFlagContext = createContext<FeatureFlagContextType>({
 flags: DEFAULT_FLAGS,
 updateFlag: () => {},
 toggleFlag: () => {},
 resetFlags: () => {},
 isLoading: false,
 error: null,
});

interface FeatureFlagProviderProps {
 children: React.ReactNode;
 config?: Partial<FeatureFlagConfig>;
 initialFlags?: Partial<FeatureFlags>;
}

export function FeatureFlagProvider({
 children,
 config = {},
 initialFlags = {}
}: FeatureFlagProviderProps) {
 const [flags, setFlags] = useState<FeatureFlags>(DEFAULT_FLAGS);
 const [isLoading, setIsLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);

 // Get environment from Next.js
 const environment = process.env.NODE_ENV as 'development' | 'staging' | 'production';

 // Initialize feature flags
 useEffect(() => {
 const initializeFlags = async () => {
 try {
 setIsLoading(true);
 setError(null);

 // Create configuration
 const flagConfig: FeatureFlagConfig = {
 environment,
 rolloutPercentage: 100, // Full rollout in development
 ...config,
 };

 // Calculate flags based on environment and config
 const calculatedFlags = calculateFeatureFlags(flagConfig);

 // Apply initial overrides
 const finalFlags = {
 ...calculatedFlags,
 ...initialFlags,
 };

 // Load any persisted flags from localStorage (development only)
 if (environment === 'development') {
 const savedFlags = loadFlagsFromStorage();
 if (savedFlags) {
 Object.assign(finalFlags, savedFlags);
 }
 }

 setFlags(finalFlags);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to initialize feature flags');
 console.error('Feature flag initialization error:', err);
 } finally {
 setIsLoading(false);
 }
 };

 initializeFlags();
 }, [environment]); // Remove config and initialFlags from dependencies

 // Save flags to localStorage in development
 const saveFlagsToStorage = (newFlags: FeatureFlags) => {
 if (environment === 'development') {
 try {
 localStorage.setItem('featureFlags', JSON.stringify(newFlags));
 } catch (err) {
 console.warn('Failed to save feature flags to localStorage:', err);
 }
 }
 };

 // Load flags from localStorage
 const loadFlagsFromStorage = (): Partial<FeatureFlags> | null => {
 if (environment !== 'development') return null;

 try {
 const saved = localStorage.getItem('featureFlags');
 return saved ? JSON.parse(saved) : null;
 } catch (err) {
 console.warn('Failed to load feature flags from localStorage:', err);
 return null;
 }
 };

 // Update a single flag
 const updateFlag = (key: keyof FeatureFlags, value: boolean) => {
 setFlags(prevFlags => {
 const newFlags = { ...prevFlags, [key]: value };

 // Save to storage
 if (environment === 'development') {
 try {
 localStorage.setItem('featureFlags', JSON.stringify(newFlags));
 console.log(`Feature flag updated: ${key} = ${value}`);
 } catch (err) {
 console.warn('Failed to save feature flags to localStorage:', err);
 }
 }

 return newFlags;
 });
 };

 // Toggle a flag
 const toggleFlag = (key: keyof FeatureFlags) => {
 updateFlag(key, !flags[key]);
 };

 // Reset flags to defaults
 const resetFlags = () => {
 const defaultFlags = calculateFeatureFlags({
 environment,
 rolloutPercentage: 100,
 ...config,
 });

 setFlags(defaultFlags);
 saveFlagsToStorage(defaultFlags);

 if (environment === 'development') {
 console.log('Feature flags reset to defaults');
 }
 };

 const contextValue: FeatureFlagContextType = {
 flags,
 updateFlag,
 toggleFlag,
 resetFlags,
 isLoading,
 error,
 };

 return (
 <FeatureFlagContext.Provider value={contextValue}>
 {children}
 </FeatureFlagContext.Provider>
 );
}

// Hook to use feature flags
export function useFeatureFlags(): FeatureFlagContextType {
 const context = useContext(FeatureFlagContext);

 if (!context) {
 throw new Error('useFeatureFlags must be used within a FeatureFlagProvider');
 }

 return context;
}

// Convenience hooks for specific functionality
export function useFeatureFlag(flag: keyof FeatureFlags): boolean {
 const { flags } = useFeatureFlags();
 return flags[flag];
}

export function useMigrationFlags() {
 const { flags } = useFeatureFlags();

 return {
 isAuthoritativeRouteMigrationEnabled: flags.authoritativeRouteMigration,
 isNewDevelopmentSelectorEnabled: flags.newDevelopmentSelector,
 isNewComplianceStatusEnabled: flags.newComplianceStatus,
 isNewComplianceChecklistEnabled: flags.newComplianceChecklist,
 isUnifiedStateManagementEnabled: flags.unifiedStateManagement,
 shouldUseLegacyFallback: flags.legacyRouteFallback,
 };
}