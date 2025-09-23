import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DevelopmentProvider, useDevelopmentContext } from '@/contexts/DevelopmentContext';

global.fetch = jest.fn();

const TestComponent: React.FC = () => {
 const {
 availableDevelopments,
 selectedDevelopment,
 isLoading,
 loadDevelopmentTypes,
 setSelectedDevelopment,
 } = useDevelopmentContext();

 return (
 <div>
 <div data-testid="loading">{isLoading ? 'Loading' : 'Loaded'}</div>
 <div data-testid="count">{availableDevelopments.length}</div>
 <div data-testid="selected">
 {selectedDevelopment ? selectedDevelopment.name : 'None'}
 </div>
 <button onClick={() => loadDevelopmentTypes()}>Load</button>
 <button onClick={() => setSelectedDevelopment(availableDevelopments[0])}>
 Select First
 </button>
 </div>
 );
};

const mockDevelopmentTypes = [
 {
 id: '1',
 code: 'RFB',
 name: 'Residential Flat Building',
 description: 'Test description',
 category: 'residential' as const,
 complianceRequirements: [],
 applicableZones: [],
 isEnabled: true,
 },
];

describe('DevelopmentContext', () => {
 beforeEach(() => {
 jest.clearAllMocks();
 (fetch as jest.Mock).mockResolvedValue({
 ok: true,
 json: () => Promise.resolve(mockDevelopmentTypes),
 });
 });

 test('provides development context', () => {
 render(
 <DevelopmentProvider>
 <TestComponent />
 </DevelopmentProvider>
 );

 expect(screen.getByTestId('loading')).toHaveTextContent('Loaded');
 expect(screen.getByTestId('count')).toHaveTextContent('0');
 expect(screen.getByTestId('selected')).toHaveTextContent('None');
 });

 test('loads development types', async () => {
 render(
 <DevelopmentProvider>
 <TestComponent />
 </DevelopmentProvider>
 );

 fireEvent.click(screen.getByText('Load'));

 await waitFor(() => {
 expect(screen.getByTestId('count')).toHaveTextContent('1');
 });
 });

 test('sets selected development', async () => {
 render(
 <DevelopmentProvider>
 <TestComponent />
 </DevelopmentProvider>
 );

 fireEvent.click(screen.getByText('Load'));

 await waitFor(() => {
 expect(screen.getByTestId('count')).toHaveTextContent('1');
 });

 fireEvent.click(screen.getByText('Select First'));

 expect(screen.getByTestId('selected')).toHaveTextContent('Residential Flat Building');
 });
});
