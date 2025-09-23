import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider';
import { DevelopmentProvider } from '@/contexts/DevelopmentContext';
import { EnhancedDevelopmentSelector } from '@/components/development/EnhancedDevelopmentSelector';
import developmentReducer from '@/store/slices/developmentSlice';

// Mock fetch
global.fetch = jest.fn();

const mockDevelopmentTypes = [
 {
 id: '1',
 code: 'RFB',
 name: 'Residential Flat Building',
 description: 'A building containing multiple dwellings',
 category: 'residential' as const,
 complianceRequirements: ['Building Height', 'Floor Space Ratio'],
 applicableZones: ['R3', 'R4'],
 minimumLotSize: 600,
 isEnabled: true,
 },
 {
 id: '2',
 code: 'SFD',
 name: 'Single Family Dwelling',
 description: 'A detached house',
 category: 'residential' as const,
 complianceRequirements: ['Building Height', 'Setbacks'],
 applicableZones: ['R1', 'R2'],
 minimumLotSize: 450,
 isEnabled: true,
 },
];

const createTestStore = () => {
 return configureStore({
 reducer: {
 development: developmentReducer,
 },
 });
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
 const store = createTestStore();

 return (
 <Provider store={store}>
 <FeatureFlagProvider>
 <DevelopmentProvider>
 {children}
 </DevelopmentProvider>
 </FeatureFlagProvider>
 </Provider>
 );
};

const defaultProps = {
 onDevelopmentChange: jest.fn(),
 propertyId: 'test-property',
};

describe('EnhancedDevelopmentSelector', () => {
 beforeEach(() => {
 jest.clearAllMocks();
 (fetch as jest.Mock).mockResolvedValue({
 ok: true,
 json: () => Promise.resolve(mockDevelopmentTypes),
 });
 });

 test('renders development types', async () => {
 render(
 <TestWrapper>
 <EnhancedDevelopmentSelector {...defaultProps} />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
 expect(screen.getByText('Single Family Dwelling')).toBeInTheDocument();
 });
 });

 test('filters by search term', async () => {
 render(
 <TestWrapper>
 <EnhancedDevelopmentSelector {...defaultProps} />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
 });

 fireEvent.change(screen.getByPlaceholderText('Search development types...'), {
 target: { value: 'single' }
 });

 await waitFor(() => {
 expect(screen.getByText('Single Family Dwelling')).toBeInTheDocument();
 expect(screen.queryByText('Residential Flat Building')).not.toBeInTheDocument();
 });
 });

 test('calls onDevelopmentChange when selection is made', async () => {
 const onDevelopmentChange = jest.fn();

 render(
 <TestWrapper>
 <EnhancedDevelopmentSelector {...defaultProps} onDevelopmentChange={onDevelopmentChange} />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
 });

 fireEvent.click(screen.getByText('Residential Flat Building'));

 expect(onDevelopmentChange).toHaveBeenCalledWith(mockDevelopmentTypes[0]);
 });

 test('validates property constraints', async () => {
 render(
 <TestWrapper>
 <EnhancedDevelopmentSelector
 {...defaultProps}
 zoning="R1"
 lotSize={300}
 />
 </TestWrapper>
 );

 await waitFor(() => {
 expect(screen.getByText('Residential Flat Building')).toBeInTheDocument();
 });

 fireEvent.click(screen.getByText('Residential Flat Building'));

 await waitFor(() => {
 expect(screen.getByText('Development Compatibility Warnings:')).toBeInTheDocument();
 });
 });
});
