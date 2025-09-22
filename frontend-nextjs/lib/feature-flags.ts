/**
 * Feature Flag System for Authoritative Route Migration
 * Enables safe, controlled rollout of new UI components
 */

export interface FeatureFlags {
 // Migration feature flags
 authoritativeRouteMigration: boolean;
 newDevelopmentSelector: boolean;
 newComplianceStatus: boolean;
 newComplianceChecklist: boolean;

 // Infrastructure flags
 unifiedStateManagement: boolean;
 legacyRouteFallback: boolean;

 // Performance flags
 enableCaching: boolean;
 enableAnalytics: boolean;
}

export interface FeatureFlagConfig {
 environment: 'development' | 'staging' | 'production';
 userId?: string;
 rolloutPercentage: number;
 overrides?: Partial<FeatureFlags>;
}

// Default feature flag values
export const DEFAULT_FLAGS: FeatureFlags = {
 authoritativeRouteMigration: false,
 newDevelopmentSelector: false,
 newComplianceStatus: false,
 newComplianceChecklist: false,
 unifiedStateManagement: false,
 legacyRouteFallback: true,
 enableCaching: true,
 enableAnalytics: false,
};

// Environment-specific defaults
export const ENVIRONMENT_DEFAULTS: Record<string, Partial<FeatureFlags>> = {
 development: {
 authoritativeRouteMigration: true,
 newDevelopmentSelector: true,
 newComplianceStatus: true,
 newComplianceChecklist: true,
 unifiedStateManagement: true,
 enableAnalytics: true,
 },
 staging: {
 authoritativeRouteMigration: true,
 newDevelopmentSelector: true,
 newComplianceStatus: true,
 newComplianceChecklist: false,
 },
 production: {
 authoritativeRouteMigration: false,
 newDevelopmentSelector: false,
 newComplianceStatus: false,
 newComplianceChecklist: false,
 },
};

/**
 * Calculate feature flags based on environment and user
 */
export function calculateFeatureFlags(config: FeatureFlagConfig): FeatureFlags {
 const environmentDefaults = ENVIRONMENT_DEFAULTS[config.environment] || {};

 let flags = {
 ...DEFAULT_FLAGS,
 ...environmentDefaults,
 ...config.overrides,
 };

 // Apply rollout percentage logic
 if (config.rolloutPercentage < 100) {
 const hash = hashUserId(config.userId || 'anonymous');
 const userPercentage = hash % 100;

 if (userPercentage >= config.rolloutPercentage) {
 // User is not in rollout - disable migration flags
 flags = {
 ...flags,
 authoritativeRouteMigration: false,
 newDevelopmentSelector: false,
 newComplianceStatus: false,
 newComplianceChecklist: false,
 };
 }
 }

 return flags;
}

/**
 * Simple hash function for consistent user bucketing
 */
function hashUserId(userId: string): number {
 let hash = 0;
 for (let i = 0; i < userId.length; i++) {
 const char = userId.charCodeAt(i);
 hash = ((hash << 5) - hash) + char;
 hash = hash & hash; // Convert to 32-bit integer
 }
 return Math.abs(hash);
}

/**
 * Feature flag evaluation utilities
 */
export class FeatureFlagEvaluator {
 private flags: FeatureFlags;

 constructor(flags: FeatureFlags) {
 this.flags = flags;
 }

 /**
 * Check if a feature is enabled
 */
 isEnabled(flag: keyof FeatureFlags): boolean {
 return this.flags[flag];
 }

 /**
 * Check if migration should be active
 */
 shouldUseMigration(): boolean {
 return this.flags.authoritativeRouteMigration;
 }

 /**
 * Check if component should use new implementation
 */
 shouldUseNewComponent(component: 'developmentSelector' | 'complianceStatus' | 'complianceChecklist'): boolean {
 const flagMap = {
 developmentSelector: 'newDevelopmentSelector',
 complianceStatus: 'newComplianceStatus',
 complianceChecklist: 'newComplianceChecklist',
 } as const;

 return this.flags[flagMap[component]];
 }

 /**
 * Get all enabled flags
 */
 getEnabledFlags(): Array<keyof FeatureFlags> {
 return Object.entries(this.flags)
 .filter(([_, enabled]) => enabled)
 .map(([flag, _]) => flag as keyof FeatureFlags);
 }
}