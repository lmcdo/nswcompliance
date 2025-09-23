import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { FeatureFlagProvider, useFeatureFlags } from '@/components/providers/FeatureFlagProvider';

// Mock the feature flag service
jest.mock('@/lib/feature-flag-service', () => ({
 featureFlagService: {
 getFlags: jest.fn(),
 getFlag: jest.fn(),
 updateFlag: jest.fn(),
 resetFlags: jest.fn(),
 },
}));

const TestComponent: React.FC = () => {
 const { flags, loading, error, updateFlag } = useFeatureFlags();

 if (loading) return <div>Loading...</div>;
 if (error) return <div>Error: {error}</div>;

 return (
 <div>
 <div data-testid="new-selector">{flags.newDevelopmentSelector.toString()}</div>
 <div data-testid="enhanced-status">{flags.enhancedComplianceStatus.toString()}</div>
 <button onClick={() => updateFlag('newDevelopmentSelector', true)}>
 Enable New Selector
 </button>
 </div>
 );
};

describe('FeatureFlagProvider', () => {
 const mockService = require('@/lib/feature-flag-service').featureFlagService;

 beforeEach(() => {
 jest.clearAllMocks();
 mockService.getFlags.mockResolvedValue({
 newDevelopmentSelector: false,
 enhancedComplianceStatus: true,
 advancedComplianceChecklist: false,
 realTimeValidation: false,
 debugMode: false,
 });
 });

 test('provides feature flags context', async () => {
 render(
 <FeatureFlagProvider>
 <TestComponent />
 </FeatureFlagProvider>
 );

 expect(screen.getByText('Loading...')).toBeInTheDocument();

 await waitFor(() => {
 expect(screen.getByTestId('new-selector')).toHaveTextContent('false');
 expect(screen.getByTestId('enhanced-status')).toHaveTextContent('true');
 });
 });

 test('handles service errors gracefully', async () => {
 mockService.getFlags.mockRejectedValue(new Error('Service unavailable'));

 render(
 <FeatureFlagProvider>
 <TestComponent />
 </FeatureFlagProvider>
 );

 await waitFor(() => {
 expect(screen.getByText(/Error:/)).toBeInTheDocument();
 });
 });

 test('updateFlag calls service and updates state', async () => {
 mockService.updateFlag.mockResolvedValue(undefined);
 mockService.getFlags.mockResolvedValueOnce({
 newDevelopmentSelector: false,
 enhancedComplianceStatus: true,
 advancedComplianceChecklist: false,
 realTimeValidation: false,
 debugMode: false,
 }).mockResolvedValueOnce({
 newDevelopmentSelector: true,
 enhancedComplianceStatus: true,
 advancedComplianceChecklist: false,
 realTimeValidation: false,
 debugMode: false,
 });

 render(
 <FeatureFlagProvider>
 <TestComponent />
 </FeatureFlagProvider>
 );

 await waitFor(() => {
 expect(screen.getByTestId('new-selector')).toHaveTextContent('false');
 });

 screen.getByText('Enable New Selector').click();

 await waitFor(() => {
 expect(mockService.updateFlag).toHaveBeenCalledWith('newDevelopmentSelector', true);
 });
 });

 test('throws error when used outside provider', () => {
 // Suppress console.error for this test
 const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

 expect(() => {
 render(<TestComponent />);
 }).toThrow('useFeatureFlags must be used within a FeatureFlagProvider');

 consoleSpy.mockRestore();
 });
});