// lib/database/mock-client.ts - Temporary mock client until PostgreSQL is set up
export class MockDatabaseClient {
 // Mock methods that return sample data for development
 async getHierarchicalSetbackControls(zone: string) {
 return [
 {
 id: 1,
 control_type: 'setback',
 zone_applicable: zone,
 value_text: '3.0m front setback',
 confidence_score: 0.97,
 provision_text: 'Buildings must be set back 3.0 metres from the front boundary',
 document_id: 'Inner_West_LEP_2022',
 authority_level: 'LEP - Local Environmental Plan',
 legal_precedence: 2,
 can_be_varied: true
 }
 ];
 }

 async getQuantitativeStandards(context: string, zone?: string) {
 return [
 {
 id: 1,
 context,
 numeric_value: 3.0,
 unit: 'm',
 confidence_score: 0.97,
 provision_text: 'Minimum setback requirement for residential buildings'
 }
 ];
 }

 async searchProvisions(searchTerm: string) {
 return [
 {
 id: 1,
 provision_text: `Sample provision containing ${searchTerm}`,
 document_id: 'Mock_Document',
 confidence_score: 0.9
 }
 ];
 }

 async getDatabaseStats() {
 return {
 development_controls: 1500,
 quantitative_standards: 800,
 kg_relationships: 2200,
 regulatory_provisions: 22000,
 total_records: 26500
 };
 }

 async testConnection(): Promise<boolean> {
 return true; // Mock always returns true
 }

 async close() {
 // Mock close does nothing
 }

 async execute(sql: string, params: any[] = []): Promise<any[]> {
 // Return mock data
 return [{ mock: 'data', sql_executed: sql }];
 }
}

// Export singleton instance
export const mockClient = new MockDatabaseClient();