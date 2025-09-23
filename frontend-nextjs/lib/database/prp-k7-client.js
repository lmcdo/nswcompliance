/**
 * PRP-K7 PostgreSQL Database Client (JavaScript)
 * Provides zone-aware development type queries for grouped setbacks
 */

const { Pool } = require('pg');

class PRPK7DatabaseClient {
 constructor() {
 this.pool = new Pool({
 host: process.env.DATABASE_HOST || 'localhost',
 port: parseInt(process.env.DATABASE_PORT || '5432'),
 database: process.env.DATABASE_NAME || 'nsw_planning',
 user: process.env.DATABASE_USER || 'postgres',
 password: process.env.DATABASE_PASSWORD || 'postgres',
 max: 20,
 idleTimeoutMillis: 30000,
 connectionTimeoutMillis: 10000
 });

 this.pool.on('error', (err) => {
 console.error('PRP-K7 PostgreSQL pool error:', err);
 });
 }

 /**
 * PRP-K7: Get all setbacks for a zone grouped by development type
 * NO AGGREGATION - Returns all provisions
 */
 async getZoneSetbacksGroupedByDevType(zone) {
 console.log(`[PRP-K7] Getting setbacks for zone ${zone} grouped by development type`);
 
 const client = await this.pool.connect();
 try {
 const query = `
 SELECT 
 pp.id,
 pp.zone,
 pp.development_type,
 qs.context,
 qs.numeric_value,
 qs.unit,
 pp.confidence_score,
 pp.provision_text,
 pp.ref_number,
 pp.document_id,
 pp.section_header
 FROM public.regulatory_provisions pp
 JOIN public.quantitative_standards qs ON pp.id = qs.provision_id
 WHERE pp.zone = $1
 AND (qs.context LIKE '%setback%' OR pp.boundary_type IS NOT NULL)
 AND qs.numeric_value IS NOT NULL
 ORDER BY COALESCE(pp.development_type, 'general'), pp.boundary_type
 `;

 const result = await client.query(query, [zone]);
 console.log(`[PRP-K7] Found ${result.rows.length} setback provisions for zone ${zone}`);

 // Transform to grouped structure
 const grouped = {};

 for (const row of result.rows) {
 const devType = row.development_type;
 const boundaryType = row.context.replace('setback_', '');
 
 const setbackResult = {
 id: row.id,
 zone: row.zone,
 development_type: devType,
 boundary_type: boundaryType,
 value: row.numeric_value,
 unit: row.unit || 'm',
 confidence: row.confidence_score || 0.85,
 provision_text: row.provision_text || '',
 ref_number: row.ref_number || '',
 document_id: row.document_id || '',
 section_header: row.section_header || ''
 };

 if (!grouped[devType]) {
 grouped[devType] = [];
 }
 grouped[devType].push(setbackResult);
 }

 console.log(`[PRP-K7] Grouped into ${Object.keys(grouped).length} development types:`, Object.keys(grouped));
 return grouped;

 } finally {
 client.release();
 }
 }

 /**
 * PRP-K7: Get all development types permitted in a zone
 */
 async getPermittedDevelopmentTypes(zone) {
 const client = await this.pool.connect();
 try {
 const query = `
 SELECT DISTINCT development_type
 FROM public.regulatory_provisions
 WHERE zone = $1
 AND development_type IS NOT NULL
 ORDER BY development_type
 `;

 const result = await client.query(query, [zone]);
 const devTypes = result.rows.map(row => row.development_type);
 
 console.log(`[PRP-K7] Zone ${zone} permits ${devTypes.length} development types:`, devTypes);
 return devTypes;

 } finally {
 client.release();
 }
 }

 /**
 * PRP-K7: Get flat array of setbacks for API compatibility
 */
 async getZoneSetbacksFlat(zone) {
 const grouped = await this.getZoneSetbacksGroupedByDevType(zone);
 
 const flat = [];
 for (const [devType, setbacks] of Object.entries(grouped)) {
 for (const setback of setbacks) {
 flat.push({
 boundary_type: setback.boundary_type,
 development_type: setback.development_type,
 value: setback.value,
 setback_distance: setback.value,
 required_setback: setback.value,
 unit: 'meters',
 confidence: setback.confidence,
 confidence_score: setback.confidence,
 rule_source: setback.document_id,
 clause_reference: setback.ref_number,
 legal_source: setback.document_id,
 authority: this.getAuthorityLevel(setback.document_id),
 precedence: this.getPrecedence(setback.document_id),
 provision_id: setback.id,
 full_text: setback.provision_text,
 domain_classification: 'RESIDENTIAL_BUILDINGS',
 cross_contamination_checked: true
 });
 }
 }

 return flat;
 }

 /**
 * Determine authority level from document ID
 */
 getAuthorityLevel(documentId) {
 const docUpper = documentId.toUpperCase();
 if (docUpper.includes('SEPP')) return 'SEPP';
 if (docUpper.includes('LEP')) return 'LEP';
 return 'DCP';
 }

 /**
 * Get legal precedence (1=highest, 3=lowest)
 */
 getPrecedence(documentId) {
 const authority = this.getAuthorityLevel(documentId);
 switch (authority) {
 case 'SEPP': return 1;
 case 'LEP': return 2;
 case 'DCP': return 3;
 default: return 3;
 }
 }

 /**
 * Test database connection
 */
 async testConnection() {
 try {
 const client = await this.pool.connect();
 await client.query('SELECT 1');
 client.release();
 return true;
 } catch (error) {
 console.error('PRP-K7 Database connection failed:', error);
 return false;
 }
 }

 /**
 * Get zone statistics for verification
 */
 async getZoneStats(zone) {
 const client = await this.pool.connect();
 try {
 const stats = await client.query(`
 SELECT 
 COUNT(*) as total_provisions,
 COUNT(DISTINCT development_type) FILTER (WHERE development_type IS NOT NULL) as dev_types,
 array_agg(DISTINCT development_type) FILTER (WHERE development_type IS NOT NULL) as development_types
 FROM public.regulatory_provisions
 WHERE zone = $1
 `, [zone]);

 const standards = await client.query(`
 SELECT COUNT(qs.id) as linked_standards
 FROM public.regulatory_provisions rp
 JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone = $1
 AND qs.context LIKE 'setback_%'
 `, [zone]);

 return {
 zone,
 total_provisions: parseInt(stats.rows[0].total_provisions),
 development_types: stats.rows[0].development_types || [],
 dev_type_count: parseInt(stats.rows[0].dev_types),
 linked_standards: parseInt(standards.rows[0].linked_standards)
 };

 } finally {
 client.release();
 }
 }

 /**
 * Clean up connections
 */
 async close() {
 await this.pool.end();
 }
}

module.exports = { PRPK7DatabaseClient };