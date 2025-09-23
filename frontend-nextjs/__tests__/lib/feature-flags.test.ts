import { getFeatureFlags, isFeatureEnabled } from '@/lib/feature-flags';

describe('Feature Flags', () => {
 beforeEach(() => {
 // Clear localStorage before each test
 localStorage.clear();
 // Reset environment variables
 delete process.env.FEATURE_NEW_DEVELOPMENT_SELECTOR;
 delete process.env.FEATURE_ENHANCED_COMPLIANCE_STATUS;
 });

 describe('getFeatureFlags', () => {
 test('returns default flags when no configuration exists', () => {
 const flags = getFeatureFlags();

 expect(flags).toEqual({
 newDevelopmentSelector: false,
 enhancedComplianceStatus: false,
 advancedComplianceChecklist: false,
 realTimeValidation: false,
 debugMode: false,
 });
 });

 test('reads flags from environment variables', () => {
 process.env.FEATURE_NEW_DEVELOPMENT_SELECTOR = 'true';
 process.env.FEATURE_ENHANCED_COMPLIANCE_STATUS = 'true';

 const flags = getFeatureFlags();

 expect(flags.newDevelopmentSelector).toBe(true);
 expect(flags.enhancedComplianceStatus).toBe(true);
 });

 test('reads flags from localStorage', () => {
 localStorage.setItem('nsw-compliance-feature-flags', JSON.stringify({
 newDevelopmentSelector: true,
 enhancedComplianceStatus: false,
 }));

 const flags = getFeatureFlags();

 expect(flags.newDevelopmentSelector).toBe(true);
 expect(flags.enhancedComplianceStatus).toBe(false);
 });

 test('environment variables override localStorage', () => {
 localStorage.setItem('nsw-compliance-feature-flags', JSON.stringify({
 newDevelopmentSelector: false,
 }));
 process.env.FEATURE_NEW_DEVELOPMENT_SELECTOR = 'true';

 const flags = getFeatureFlags();

 expect(flags.newDevelopmentSelector).toBe(true);
 });
 });

 describe('isFeatureEnabled', () => {
 test('returns correct boolean for existing flags', () => {
 process.env.FEATURE_NEW_DEVELOPMENT_SELECTOR = 'true';

 expect(isFeatureEnabled('newDevelopmentSelector')).toBe(true);
 expect(isFeatureEnabled('enhancedComplianceStatus')).toBe(false);
 });

 test('returns false for non-existent flags', () => {
 expect(isFeatureEnabled('nonExistentFlag' as any)).toBe(false);
 });

 test('handles invalid localStorage data gracefully', () => {
 localStorage.setItem('nsw-compliance-feature-flags', 'invalid json');

 expect(() => isFeatureEnabled('newDevelopmentSelector')).not.toThrow();
 expect(isFeatureEnabled('newDevelopmentSelector')).toBe(false);
 });
 });
});