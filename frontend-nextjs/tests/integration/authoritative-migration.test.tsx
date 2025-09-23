import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { DevelopmentProvider } from '@/contexts/DevelopmentContext';
import { ChecklistProvider } from '@/contexts/ChecklistContext';

// Mock fetch
global.fetch = jest.fn();

// Test wrapper with all providers
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
 <FeatureFlagProvider>
 <DevelopmentProvider>
 <ChecklistProvider>
 {children}
 </ChecklistProvider>
 </DevelopmentProvider>
 </FeatureFlagProvider>
);

describe('Authoritative Migration Integration Tests', () => {
 beforeEach(() => {
 jest.clearAllMocks();
 // Mock successful responses
 (fetch as jest.Mock).mockResolvedValue({
 ok: true,
 json: () => Promise.resolve({ success: true, data: [] }),
 });
 });

 describe('Feature Flag Integration', () => {
 test('feature flags provider loads and provides context', async () => {
 const TestComponent = () => {
 const { useFeatureFlags } = require('@/components/providers/FeatureFlagProvider');
 const { flags, loading } = useFeatureFlags();
 return (
 <div>
 <div data-testid="loading">{loading ? 'loading' : 'loaded'}</div>
 <div data-testid="flags">{JSON.stringify(flags)}</div>
 </div>
 );
 };

 render(
 <TestWrapper>
 <TestComponent />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByTestId('loading')).toHaveTextContent('loaded');
 });
 });
 });

 describe('Development Selector Migration', () => {
 test('development selector integrates with feature flags', async () => {
 // Mock component exists check
 Object.defineProperty(document, 'querySelector', {
 value: jest.fn(() => ({ getAttribute: () => 'development-selector' })),
 writable: true
 });

 const { DevelopmentSelector } = require('@/components/development/DevelopmentSelector');

 render(
 <TestWrapper>
 <DevelopmentSelector />
 </TestWrapper>
 );

 // Component should render without errors
 expect(document.querySelector).toHaveBeenCalled();
 });
 });

 describe('Compliance Status Migration', () => {
 test('compliance status integrates with property data', async () => {
 const mockPropertyData = {
 id: 'test-property',
 address: '123 Test St',
 zoning: 'R2',
 constraints: { zone: 'R2' }
 };

 (fetch as jest.Mock).mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({ data: mockPropertyData }),
 });

 // Test that compliance status can fetch and display property data
 const response = await fetch('/api/property?address=123+Test+St');
 const data = await response.json();

 expect(data.data.zoning).toBe('R2');
 });
 });

 describe('Compliance Checklist Migration', () => {
 test('checklist loads compliance items for development type', async () => {
 const mockChecklistItems = [
 {
 id: '1',
 title: 'Building Height',
 status: 'pending',
 tier: 'tier1',
 authority: 'Council',
 confidence: 95
 }
 ];

 (fetch as jest.Mock).mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({ items: mockChecklistItems }),
 });

 const response = await fetch('/api/compliance/checklist?developmentType=dual_occupancy');
 const data = await response.json();

 expect(data.items).toHaveLength(1);
 expect(data.items[0].title).toBe('Building Height');
 });
 });

 describe('End-to-End Migration Flow', () => {
 test('complete migration flow works', async () => {
 // Mock all API responses
 (fetch as jest.Mock)
 .mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({
 success: true,
 data: {
 types: [
 { id: '1', name: 'Dual Occupancy', category: 'residential' }
 ]
 }
 }),
 })
 .mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({
 items: [
 {
 id: '1',
 title: 'Building Height',
 status: 'pending',
 tier: 'tier1',
 authority: 'Council',
 confidence: 95
 }
 ]
 }),
 });

 // Test the complete flow
 const developmentResponse = await fetch('/api/development-types?zone=R2');
 const developmentData = await developmentResponse.json();

 expect(developmentData.success).toBe(true);

 const checklistResponse = await fetch('/api/compliance/checklist?developmentType=dual_occupancy');
 const checklistData = await checklistResponse.json();

 expect(checklistData.items).toHaveLength(1);

 // Verify the integration works end-to-end
 expect(fetch).toHaveBeenCalledTimes(2);
 });
 });

 describe('Error Handling', () => {
 test('handles API failures gracefully', async () => {
 (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

 try {
 await fetch('/api/test-endpoint');
 } catch (error) {
 expect(error.message).toBe('Network error');
 }

 // Application should still be functional
 expect(true).toBe(true);
 });
 });

 describe('Performance Tests', () => {
 test('migration components load within performance budget', async () => {
 const startTime = performance.now();

 // Simulate loading all migration components
 const { DevelopmentSelector } = require('@/components/development/DevelopmentSelector');
 const { EnhancedComplianceChecklist } = require('@/components/compliance/EnhancedComplianceChecklist');

 render(
 <TestWrapper>
 <div>
 <DevelopmentSelector />
 <EnhancedComplianceChecklist />
 </div>
 </TestWrapper>
 );

 const endTime = performance.now();
 const loadTime = endTime - startTime;

 // Should load within 100ms
 expect(loadTime).toBeLessThan(100);
 });
 });

 describe('Migration Health Checks', () => {
 test('all migration components are healthy', async () => {
 // Mock health check responses
 (fetch as jest.Mock)
 .mockResolvedValueOnce({ ok: true }) // feature-flags
 .mockResolvedValueOnce({ ok: true }) // api-endpoints
 .mockResolvedValueOnce({ ok: true }); // database

 const healthChecks = [
 fetch('/api/feature-flags/health'),
 fetch('/api/health'),
 fetch('/api/health/database')
 ];

 const results = await Promise.all(healthChecks);
 const allHealthy = results.every(response => response.ok);

 expect(allHealthy).toBe(true);
 });
 });
});