export interface ABTestConfig {
 id: string;
 name: string;
 description: string;
 enabled: boolean;
 variants: ABTestVariant[];
 allocation: Record<string, number>;
 startDate: string;
 endDate?: string;
 targetAudience?: {
 userPercentage: number;
 criteria?: string[];
 };
}

export interface ABTestVariant {
 id: string;
 name: string;
 description: string;
 weight: number;
 config: Record<string, any>;
}

export interface ABTestResult {
 testId: string;
 variant: string;
 userId: string;
 timestamp: string;
 metrics: Record<string, number>;
}

export class MigrationABTest {
 private tests: Map<string, ABTestConfig> = new Map();
 private userAssignments: Map<string, Map<string, string>> = new Map();
 private results: Map<string, ABTestResult[]> = new Map();

 constructor() {
 this.initializeDefaultTests();
 }

 private initializeDefaultTests() {
 const migrationRolloutTest: ABTestConfig = {
 id: 'migration-rollout',
 name: 'Migration Rollout',
 description: 'Gradual rollout of new migration features',
 enabled: true,
 variants: [
 {
 id: 'control',
 name: 'Legacy System',
 description: 'Keep using legacy components',
 weight: 50,
 config: {
 useNewDevelopmentSelector: false,
 useEnhancedCompliance: false,
 useAdvancedChecklist: false,
 }
 },
 {
 id: 'treatment',
 name: 'New System',
 description: 'Use new migrated components',
 weight: 50,
 config: {
 useNewDevelopmentSelector: true,
 useEnhancedCompliance: true,
 useAdvancedChecklist: true,
 }
 }
 ],
 allocation: { control: 50, treatment: 50 },
 startDate: new Date().toISOString(),
 targetAudience: {
 userPercentage: 100,
 criteria: ['beta-users', 'internal-staff']
 }
 };

 this.tests.set(migrationRolloutTest.id, migrationRolloutTest);
 }

 /**
 * Get variant for user and test
 */
 getVariant(testId: string, userId: string): string | null {
 const test = this.tests.get(testId);
 if (!test || !test.enabled) {
 return null;
 }

 // Check if user already assigned
 if (!this.userAssignments.has(userId)) {
 this.userAssignments.set(userId, new Map());
 }

 const userTests = this.userAssignments.get(userId)!;
 if (userTests.has(testId)) {
 return userTests.get(testId)!;
 }

 // Assign user to variant
 const variant = this.assignVariant(test, userId);
 userTests.set(testId, variant);

 return variant;
 }

 /**
 * Assign user to variant based on allocation
 */
 private assignVariant(test: ABTestConfig, userId: string): string {
 // Use consistent hashing for stable assignment
 const hash = this.hashString(userId + test.id);
 const percentage = hash % 100;

 let cumulative = 0;
 for (const [variantId, weight] of Object.entries(test.allocation)) {
 cumulative += weight;
 if (percentage < cumulative) {
 return variantId;
 }
 }

 return test.variants[0].id; // Fallback
 }

 /**
 * Simple hash function for consistent assignment
 */
 private hashString(str: string): number {
 let hash = 0;
 for (let i = 0; i < str.length; i++) {
 const char = str.charCodeAt(i);
 hash = ((hash << 5) - hash) + char;
 hash = hash & hash; // Convert to 32-bit integer
 }
 return Math.abs(hash);
 }

 /**
 * Record test result/metric
 */
 recordResult(testId: string, userId: string, metrics: Record<string, number>) {
 const variant = this.getVariant(testId, userId);
 if (!variant) return;

 const result: ABTestResult = {
 testId,
 variant,
 userId,
 timestamp: new Date().toISOString(),
 metrics
 };

 if (!this.results.has(testId)) {
 this.results.set(testId, []);
 }

 this.results.get(testId)!.push(result);
 }

 /**
 * Get test configuration for user
 */
 getTestConfig(testId: string, userId: string): Record<string, any> | null {
 const test = this.tests.get(testId);
 const variant = this.getVariant(testId, userId);

 if (!test || !variant) return null;

 const variantConfig = test.variants.find(v => v.id === variant);
 return variantConfig?.config || null;
 }

 /**
 * Get test results summary
 */
 getTestResults(testId: string): {
 test: ABTestConfig;
 results: {
 [variantId: string]: {
 users: number;
 metrics: Record<string, { mean: number; count: number }>;
 };
 };
 } | null {
 const test = this.tests.get(testId);
 const results = this.results.get(testId) || [];

 if (!test) return null;

 const variantResults: any = {};

 test.variants.forEach(variant => {
 const variantData = results.filter(r => r.variant === variant.id);
 const users = new Set(variantData.map(r => r.userId)).size;

 const metrics: Record<string, { values: number[]; mean: number; count: number }> = {};

 variantData.forEach(result => {
 Object.entries(result.metrics).forEach(([metric, value]) => {
 if (!metrics[metric]) {
 metrics[metric] = { values: [], mean: 0, count: 0 };
 }
 metrics[metric].values.push(value);
 });
 });

 // Calculate means
 Object.keys(metrics).forEach(metric => {
 const values = metrics[metric].values;
 metrics[metric].mean = values.reduce((a, b) => a + b, 0) / values.length;
 metrics[metric].count = values.length;
 });

 variantResults[variant.id] = { users, metrics };
 });

 return { test, results: variantResults };
 }

 /**
 * Check if user should see migration features
 */
 shouldShowMigrationFeatures(userId: string): boolean {
 const config = this.getTestConfig('migration-rollout', userId);
 return config?.useNewDevelopmentSelector || false;
 }

 /**
 * Get all active tests
 */
 getActiveTests(): ABTestConfig[] {
 return Array.from(this.tests.values()).filter(test => test.enabled);
 }

 /**
 * Create new test
 */
 createTest(config: ABTestConfig): void {
 this.tests.set(config.id, config);
 }

 /**
 * Stop test
 */
 stopTest(testId: string): boolean {
 const test = this.tests.get(testId);
 if (test) {
 test.enabled = false;
 test.endDate = new Date().toISOString();
 return true;
 }
 return false;
 }
}

// Singleton instance
export const migrationABTest = new MigrationABTest();