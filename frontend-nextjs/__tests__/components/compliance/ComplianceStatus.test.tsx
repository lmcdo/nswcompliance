import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { ComplianceProvider } from '@/contexts/ComplianceContext';
import { EnhancedComplianceStatus } from '@/components/compliance/EnhancedComplianceStatus';

// Mock fetch
global.fetch = jest.fn();

const mockComplianceStatus = {
 overallStatus: 'conditional' as const,
 checks: [
 {
 id: '1',
 provision: '4.6.1',
 requirement: 'Building height must not exceed 24m',
 status: 'compliant' as const,
 severity: 'critical' as const,
 evidence: [],
 recommendations: [],
 lastChecked: new Date(),
 autoCheckEnabled: true,
 },
 {
 id: '2',
 provision: '4.6.2',
 requirement: 'Floor space ratio must not exceed 1.2:1',
 status: 'non-compliant' as const,
 severity: 'major' as const,
 evidence: [],
 recommendations: ['Submit architectural plans'],
 lastChecked: new Date(),
 autoCheckEnabled: true,
 },
 ],
 progress: { completed: 2, total: 2, percentage: 100 },
 criticalIssues: [],
 warnings: [],
 lastUpdated: new Date(),
 autoRefreshEnabled: false,
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
 <FeatureFlagProvider>
 <ComplianceProvider>
 {children}
 </ComplianceProvider>
 </FeatureFlagProvider>
);

const defaultProps = {
 propertyId: 'test-property',
 developmentType: { id: '1', name: 'Test Development' },
};

describe('EnhancedComplianceStatus', () => {
 beforeEach(() => {
 jest.clearAllMocks();
 (fetch as jest.Mock).mockResolvedValue({
 ok: true,
 json: () => Promise.resolve(mockComplianceStatus),
 });
 });

 test('renders compliance status', async () => {
 render(
 <TestWrapper>
 <EnhancedComplianceStatus {...defaultProps} />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Compliance Status')).toBeInTheDocument();
 });
 });

 test('displays progress metrics', async () => {
 render(
 <TestWrapper>
 <EnhancedComplianceStatus {...defaultProps} />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Overall Status')).toBeInTheDocument();
 expect(screen.getByText('Progress')).toBeInTheDocument();
 expect(screen.getByText('100%')).toBeInTheDocument();
 });
 });

 test('shows compliance checks when expanded', async () => {
 render(
 <TestWrapper>
 <EnhancedComplianceStatus {...defaultProps} showDetails />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Building height must not exceed 24m')).toBeInTheDocument();
 });
 });

 test('filters issues when toggle is enabled', async () => {
 render(
 <TestWrapper>
 <EnhancedComplianceStatus {...defaultProps} showDetails />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Show only issues')).toBeInTheDocument();
 });

 fireEvent.click(screen.getByLabelText('Show only issues'));

 // Should only show non-compliant items
 await waitFor(() => {
 expect(screen.getByText('Floor space ratio must not exceed 1.2:1')).toBeInTheDocument();
 });
 });

 test('renders minimal variant', () => {
 render(
 <TestWrapper>
 <EnhancedComplianceStatus {...defaultProps} variant="minimal" />
 </TestWrapper>
 );

 expect(screen.getByText(/checks complete/)).toBeInTheDocument();
 });
});
