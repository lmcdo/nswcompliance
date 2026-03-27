// lib/database/postgres-client.ts
import { Pool, PoolClient } from 'pg';
import type { 
 DevelopmentControl, 
 QuantitativeStandard, 
 KGRelationship,
 RegulatoryProvision,
 DevelopmentPathway
} from '@/types/database';

export class PostgresClient {
 private pool: Pool;

 constructor() {
 this.pool = new Pool({
 host: process.env.DATABASE_HOST || 'localhost',
 port: parseInt(process.env.DATABASE_PORT || '5432'),
 database: process.env.DATABASE_NAME || 'nsw_planning',
 user: process.env.DATABASE_USER || 'postgres',
 password: process.env.DATABASE_PASSWORD || 'postgres',
 max: 20,
 idleTimeoutMillis: 30000,
 connectionTimeoutMillis: 2000,
 });
 }

 // Execute raw SQL query
 async execute(sql: string, params: any[] = []): Promise<any[]> {
 const client = await this.pool.connect();
 try {
 const result = await client.query(sql, params);
 return result.rows;
 } finally {
 client.release();
 }
 }

 // Get hierarchical setback controls (simplified version for NextJS)
 async getHierarchicalSetbackControls(zone: string, propertyLocation?: { lga?: string, suburb?: string }): Promise<DevelopmentControl[]> {
 const sql = `
 SELECT 
 dc.*,
 rpc.provision_text,
 rpc.document_id,
 d.pdf_name,
 d.document_type
 FROM development_controls dc
 JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
 LEFT JOIN documents d ON rpc.document_id = d.id
 WHERE dc.control_type = 'setback'
 AND (dc.zone_applicable = $1 OR dc.zone_applicable = 'general')
 ORDER BY dc.confidence_score DESC
 LIMIT 5
 `;
 
 return await this.execute(sql, [zone]);
 }

 // Get quantitative standards
 async getQuantitativeStandards(context: string, zone?: string): Promise<QuantitativeStandard[]> {
 let sql = `
 SELECT qs.*, rpc.provision_text, rpc.document_id
 FROM quantitative_standards qs
 JOIN regulatory_provisions_clean rpc ON qs.provision_id = rpc.id
 WHERE qs.context = $1
 AND qs.numeric_value IS NOT NULL
 `;
 
 const params = [context];
 
 if (zone) {
 sql += ` AND (rpc.document_id ILIKE $2 OR rpc.document_id ILIKE '%general%')`;
 params.push(`%${zone}%`);
 }
 
 sql += ` ORDER BY qs.confidence_score DESC LIMIT 20`;
 
 return await this.execute(sql, params);
 }

 // Get KG relationships
 async getKGRelationships(predicate: string, subjectContains?: string, limit = 10): Promise<KGRelationship[]> {
 let sql = `
 SELECT subject_text, predicate, object_text, confidence_score, document_id
 FROM kg_relationships
 WHERE predicate = $1
 `;
 
 const params = [predicate];
 
 if (subjectContains) {
 sql += ` AND subject_text ILIKE $2`;
 params.push(`%${subjectContains}%`);
 }
 
 // Sanitize and parameterize limit to prevent SQL injection
 const safeLimit = Math.min(Math.max(1, Math.floor(Number(limit) || 10)), 100);
 const paramIndex = subjectContains ? 3 : 2;
 sql += ` ORDER BY confidence_score DESC LIMIT $${paramIndex}`;
 params.push(String(safeLimit));

 return await this.execute(sql, params);
 }

 // Search regulatory provisions
 async searchProvisions(searchTerm: string, documentType?: string): Promise<RegulatoryProvision[]> {
 let sql = `
 SELECT *
 FROM regulatory_provisions_clean
 WHERE provision_text ILIKE $1
 `;
 
 const params = [`%${searchTerm}%`];
 
 if (documentType) {
 sql += ` AND document_id ILIKE $2`;
 params.push(`%${documentType}%`);
 }
 
 sql += ` ORDER BY confidence_score DESC LIMIT 15`;
 
 return await this.execute(sql, params);
 }

 // Get database statistics
 async getDatabaseStats() {
 const queries = [
 'SELECT COUNT(*) as count FROM development_controls',
 'SELECT COUNT(*) as count FROM quantitative_standards',
 'SELECT COUNT(*) as count FROM kg_relationships',
 'SELECT COUNT(*) as count FROM regulatory_provisions_clean'
 ];

 const results = await Promise.all(
 queries.map(query => this.execute(query))
 );

 return {
 development_controls: results[0][0].count,
 quantitative_standards: results[1][0].count,
 kg_relationships: results[2][0].count,
 regulatory_provisions: results[3][0].count,
 total_records: results.reduce((sum, result) => sum + parseInt(result[0].count), 0)
 };
 }

 // Test database connection
 async testConnection(): Promise<boolean> {
 try {
 const result = await this.execute('SELECT 1 as test');
 return result[0].test === 1;
 } catch (error) {
 console.error('Database connection test failed:', error);
 return false;
 }
 }

 // Close database connection
 async close() {
 await this.pool.end();
 }
}

// Export singleton instance
export const postgresClient = new PostgresClient();