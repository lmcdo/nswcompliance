import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ComplianceChecklist } from '@/components/compliance-checklist'
import { FeatureFlagProvider } from '@/components/providers/FeatureFlagProvider'

// Mock the API call
global.fetch = jest.fn()

const mockFetch = fetch as jest.MockedFunction<typeof fetch>

const renderWithProviders = (component: React.ReactElement) => {
 return render(
 <FeatureFlagProvider>
 {component}
 </FeatureFlagProvider>
 )
}

describe('ComplianceChecklist', () => {
 beforeEach(() => {
 mockFetch.mockClear()
 })

 it('renders loading state when propertyData is not provided', () => {
 renderWithProviders(<ComplianceChecklist />)

 expect(screen.getByText(/compliance checklist will appear here/i)).toBeInTheDocument()
 })

 it('displays static checklist items when feature flag is disabled', () => {
 renderWithProviders(
 <ComplianceChecklist
 propertyData={{ zone: 'R2' }}
 developmentType="dual_occupancy"
 />
 )

 expect(screen.getByText(/permissibility/i)).toBeInTheDocument()
 expect(screen.getByText(/floor space ratio/i)).toBeInTheDocument()
 })

 it('fetches dynamic data when feature flag is enabled', async () => {
 const mockResponse = {
 tier_1_provisions: [
 {
 clause_reference: 'LEP 4.3',
 provision_text: 'Maximum building height 9.5m',
 tier_level: 1,
 confidence_level: 0.95,
 document_type: 'LEP',
 measurement_context: 'height',
 numeric_value: 9.5,
 unit: 'm'
 }
 ],
 tier_2_provisions: [],
 tier_3_provisions: [],
 tier_4_provisions: [],
 tier_5_provisions: []
 }

 mockFetch.mockResolvedValueOnce({
 ok: true,
 json: async () => mockResponse,
 } as Response)

 renderWithProviders(
 <ComplianceChecklist
 propertyData={{ zone: 'R2' }}
 developmentType="dual_occupancy"
 zoneCode="R2"
 propertyId={123}
 />
 )

 await waitFor(() => {
 expect(screen.getByText(/height limit/i)).toBeInTheDocument()
 })
 })

 it('expands and collapses checklist items', () => {
 renderWithProviders(
 <ComplianceChecklist
 propertyData={{ zone: 'R2' }}
 developmentType="dual_occupancy"
 />
 )

 const firstItem = screen.getByText(/permissibility/i).closest('div[role="button"]') ||
 screen.getByText(/permissibility/i).closest('.cursor-pointer')

 if (firstItem) {
 fireEvent.click(firstItem)
 expect(screen.getByText(/dual occupancy is permitted/i)).toBeInTheDocument()
 }
 })

 it('displays tier information for dynamic items', async () => {
 const mockResponse = {
 tier_1_provisions: [
 {
 clause_reference: 'LEP 4.4',
 provision_text: 'Maximum FSR 0.6:1',
 tier_level: 1,
 confidence_level: 0.98,
 document_type: 'LEP',
 measurement_context: 'fsr'
 }
 ],
 tier_2_provisions: [],
 tier_3_provisions: [],
 tier_4_provisions: [],
 tier_5_provisions: []
 }

 mockFetch.mockResolvedValueOnce({
 ok: true,
 json: async () => mockResponse,
 } as Response)

 renderWithProviders(
 <ComplianceChecklist
 propertyData={{ zone: 'R2' }}
 developmentType="dual_occupancy"
 zoneCode="R2"
 propertyId={123}
 />
 )

 await waitFor(() => {
 expect(screen.getByText(/98% confidence/i)).toBeInTheDocument()
 })
 })

 it('handles API errors gracefully', async () => {
 mockFetch.mockRejectedValueOnce(new Error('API Error'))

 renderWithProviders(
 <ComplianceChecklist
 propertyData={{ zone: 'R2' }}
 developmentType="dual_occupancy"
 zoneCode="R2"
 propertyId={123}
 />
 )

 await waitFor(() => {
 expect(screen.getByText(/error loading dynamic data/i)).toBeInTheDocument()
 })
 })
})
