// lib/database/client.ts - PRP-K2 Bulletproof PostgreSQL Integration
import { Pool, PoolClient } from 'pg';
import type { 
 DevelopmentControl, 
 QuantitativeStandard, 
 KGRelationship,
 RegulatoryProvision,
 DevelopmentPathway
} from '@/types/database';

interface PostgreSQLConfig {
 host: string;
 port: number;
 database: string;
 user: string;
 password: string;
 max: number;
 idleTimeoutMillis: number;
 connectionTimeoutMillis: number;
}

export class DatabaseClient {
 private pool: Pool;
 private config: PostgreSQLConfig;

 constructor(config?: Partial<PostgreSQLConfig>) {
 this.config = {
 host: process.env.DATABASE_HOST || 'localhost',
 port: parseInt(process.env.DATABASE_PORT || '5432'),
 database: process.env.DATABASE_NAME || 'nsw_planning',
 user: process.env.DATABASE_USER || 'postgres',
 password: process.env.DATABASE_PASSWORD || 'postgres',
 max: 20,
 idleTimeoutMillis: 30000,
 connectionTimeoutMillis: 10000,
 ...config
 };

 this.pool = new Pool(this.config);
 
 // Handle pool errors
 this.pool.on('error', (err) => {
 console.error('PostgreSQL pool error:', err);
 });
 }

 /**
 * PRP-K2: Domain-Aware Hierarchical Setback Query
 * Prevents cross-contamination by filtering on domain_classification
 */
 async getHierarchicalSetbackControls(
 zone: string, 
 propertyLocation?: { lga?: string, suburb?: string },
 queryDomain: string = 'RESIDENTIAL_BUILDINGS'
 ): Promise<DevelopmentControl[]> {
 console.log(`[PostgreSQL] Domain-aware setback query for zone: ${zone}, domain: ${queryDomain}`);
 
 const client = await this.pool.connect();
 try {
 // Step 1: Check SEPP overrides (highest authority) with domain classification
 const seppQuery = `
 SELECT dc.*, rp.provision_text, rp.document_id, rp.domain_classification,
 'SEPP - State Policy' as authority_level, 1 as legal_precedence, false as can_be_varied
 FROM development_controls dc
 JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id
 WHERE dc.control_type = 'setback'
 AND (dc.zone_applicable = $1 OR dc.zone_applicable = 'general')
 AND rp.domain_classification = $2
 AND (rp.document_id LIKE '%SEPP%' OR rp.document_id LIKE '%State Environmental Planning Policy%')
 ORDER BY dc.confidence_score DESC
 LIMIT 5
 `;
 
 const seppResult = await client.query(seppQuery, [zone, queryDomain]);
 if (seppResult.rows.length > 0) {
 console.log(`[PostgreSQL] Found ${seppResult.rows.length} SEPP controls for domain ${queryDomain}`);
 return seppResult.rows.map(row => ({
 ...row,
 authority_level: 'SEPP - State Policy',
 legal_precedence: 1,
 can_be_varied: false
 }));
 }

 // Step 2: Check LEP controls with domain classification
 const lepQuery = `
 SELECT dc.*, rp.provision_text, rp.document_id, rp.domain_classification,
 'LEP - Local Environmental Plan' as authority_level, 2 as legal_precedence, true as can_be_varied
 FROM development_controls dc
 JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id
 WHERE dc.control_type = 'setback'
 AND (dc.zone_applicable = $1 OR dc.zone_applicable = 'general')
 AND rp.domain_classification = $2
 AND rp.document_id LIKE '%LEP%'
 ORDER BY dc.confidence_score DESC
 LIMIT 5
 `;
 
 const lepResult = await client.query(lepQuery, [zone, queryDomain]);
 if (lepResult.rows.length > 0) {
 console.log(`[PostgreSQL] Found ${lepResult.rows.length} LEP controls for domain ${queryDomain}`);
 return lepResult.rows.map(row => ({
 ...row,
 authority_level: 'LEP - Local Environmental Plan',
 legal_precedence: 2,
 can_be_varied: true,
 variation_clause: 'Clause 4.6 variation may apply'
 }));
 }

 // Step 3: Fallback to DCP controls with domain classification
 const dcpQuery = `
 SELECT dc.*, rp.provision_text, rp.document_id, rp.domain_classification,
 'DCP - Development Control Plan' as authority_level, 3 as legal_precedence, true as can_be_varied
 FROM development_controls dc
 JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id
 WHERE dc.control_type = 'setback'
 AND (dc.zone_applicable = $1 OR dc.zone_applicable = 'general')
 AND rp.domain_classification = $2
 AND rp.document_id LIKE '%DCP%'
 ORDER BY dc.confidence_score DESC
 LIMIT 3
 `;
 
 const dcpResult = await client.query(dcpQuery, [zone, queryDomain]);
 console.log(`[PostgreSQL] Found ${dcpResult.rows.length} DCP controls for domain ${queryDomain}`);
 
 return dcpResult.rows.map(row => ({
 ...row,
 authority_level: 'DCP - Development Control Plan',
 legal_precedence: 3,
 can_be_varied: true,
 note: 'Guidance only - cannot override SEPP/LEP'
 }));
 } finally {
 client.release();
 }
 }

 /**
 * Get quantitative standards with domain awareness
 */
 async getQuantitativeStandards(
 context: string, 
 zone?: string,
 queryDomain: string = 'RESIDENTIAL_BUILDINGS'
 ): Promise<QuantitativeStandard[]> {
 const client = await this.pool.connect();
 try {
 let query = `
 SELECT qs.*, rp.provision_text, rp.document_id, rp.domain_classification
 FROM quantitative_standards qs
 JOIN regulatory_provisions_canonical rp ON qs.provision_id = rp.id
 WHERE qs.context = $1
 AND qs.numeric_value IS NOT NULL
 AND rp.domain_classification = $2
 `;
 
 const params = [context, queryDomain];
 
 if (zone) {
 query += ` AND (rp.provision_text LIKE $3 OR rp.document_id LIKE $3)`;
 params.push(`%${zone}%`);
 }
 
 query += ` ORDER BY qs.confidence_score DESC LIMIT 20`;
 
 const result = await client.query(query, params);
 return result.rows as QuantitativeStandard[];
 } finally {
 client.release();
 }
 }

 /**
 * Search provisions with domain filtering
 */
 async searchProvisions(
 searchTerm: string, 
 documentType?: string,
 queryDomain?: string
 ): Promise<RegulatoryProvision[]> {
 const client = await this.pool.connect();
 try {
 let query = `
 SELECT *
 FROM regulatory_provisions_canonical
 WHERE provision_text ILIKE $1
 `;
 
 const params = [`%${searchTerm}%`];
 
 if (documentType) {
 query += ` AND document_id ILIKE $${params.length + 1}`;
 params.push(`%${documentType}%`);
 }
 
 if (queryDomain) {
 query += ` AND domain_classification = $${params.length + 1}`;
 params.push(queryDomain);
 }
 
 query += ` ORDER BY created_at DESC LIMIT 15`;
 
 const result = await client.query(query, params);
 return result.rows as RegulatoryProvision[];
 } finally {
 client.release();
 }
 }



 /**
 * Explain the authority level and legal significance
 */
 private getAuthorityExplanation(authority: string, precedence: number): string {
 switch (precedence) {
 case 1:
 return `${authority} - Highest legal authority. Cannot be varied by councils. Overrides all other planning instruments.`;
 case 2:
 return `${authority} - Local law with statutory force. Can only be varied through formal Clause 4.6 variation process with consent authority approval.`;
 case 3:
 return `${authority} - Planning guidance document. Provides detailed design standards but cannot override SEPP or LEP requirements.`;
 default:
 return `${authority} - Planning document with precedence level ${precedence}.`;
 }
 }

 /**
 * Provide context about what the setback requirement means
 */
 private getLegalContext(boundaryType: string, authority: string): string {
 const contexts: { [key: string]: string } = {
 'front': 'Controls the distance between the building facade and the street boundary, affecting streetscape character and privacy.',
 'rear': 'Maintains privacy between neighboring properties and provides private open space access.',
 'side': 'Ensures adequate separation between buildings on adjacent lots for fire safety, privacy, and amenity.',
 'side_left': 'Left side boundary setback when facing the property from the street.',
 'side_right': 'Right side boundary setback when facing the property from the street.'
 };
 
 const baseContext = contexts[boundaryType] || `${boundaryType.replace('_', ' ')} boundary setback requirement.`;
 
 if (authority === 'SEPP') {
 return `${baseContext} This is a state-mandated requirement that applies across NSW.`;
 } else if (authority === 'LEP') {
 return `${baseContext} This is a local statutory requirement specific to this council area.`;
 } else {
 return `${baseContext} This provides detailed design guidance for development in this zone.`;
 }
 }

 /**
 * Get database statistics
 */
 async getDatabaseStats() {
 const client = await this.pool.connect();
 try {
 const queries = [
 'SELECT COUNT(*) as count FROM development_controls',
 'SELECT COUNT(*) as count FROM quantitative_standards',
 'SELECT COUNT(*) as count FROM kg_relationships',
 'SELECT COUNT(*) as count FROM regulatory_provisions_canonical'
 ];

 const results = await Promise.all(
 queries.map(query => client.query(query))
 );

 const [dev_controls, quant_standards, kg_relationships, reg_provisions] = results;

 return {
 development_controls: parseInt(dev_controls.rows[0].count),
 quantitative_standards: parseInt(quant_standards.rows[0].count),
 kg_relationships: parseInt(kg_relationships.rows[0].count),
 regulatory_provisions: parseInt(reg_provisions.rows[0].count),
 total_records: results.reduce((sum, result) => sum + parseInt(result.rows[0].count), 0)
 };
 } finally {
 client.release();
 }
 }

 /**
 * Test database connection
 */
 async testConnection(): Promise<boolean> {
 try {
 const client = await this.pool.connect();
 try {
 const result = await client.query('SELECT 1 as test');
 return result.rows[0].test === 1;
 } finally {
 client.release();
 }
 } catch (error) {
 console.error('PostgreSQL connection test failed:', error);
 return false;
 }
 }

 /**
 * Execute raw SQL query
 */
 async execute(sql: string, params: any[] = []): Promise<any[]> {
 const client = await this.pool.connect();
 try {
 const result = await client.query(sql, params);
 return result.rows;
 } finally {
 client.release();
 }
 }

 /**
 * Close all connections
 */
 async close() {
 await this.pool.end();
 }

 /**
 * Destructor to ensure connections are closed
 */
 async [Symbol.asyncDispose]() {
 await this.close();
 }
}

// Export singleton instance with environment configuration
export const client = new DatabaseClient();