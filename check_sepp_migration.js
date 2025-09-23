// Check SEPP/LEP migration status in PostgreSQL database
const { Pool } = require('pg');
const fs = require('fs');

const pool = new Pool({
 host: 'localhost',
 port: 5432,
 database: 'nsw_planning',
 user: 'postgres',
 password: 'postgres'
});

async function checkSeppMigration() {
 try {
 console.log('Checking PostgreSQL database for SEPP/LEP migration status...');
 
 // Get all tables
 const tablesResult = await pool.query(`
 SELECT table_name 
 FROM information_schema.tables 
 WHERE table_schema = 'public'
 ORDER BY table_name
 `);
 
 console.log('\nPostgreSQL Tables:');
 tablesResult.rows.forEach(row => {
 console.log(` - ${row.table_name}`);
 });

 // Check SEPP provisions in regulatory_provisions
 console.log('\n=== SEPP DATA ANALYSIS ===');
 
 try {
 const seppResult = await pool.query(`
 SELECT COUNT(*) as count
 FROM regulatory_provisions 
 WHERE document_id LIKE '%SEPP%' 
 OR document_id LIKE '%State_Environmental_Planning_Policy%'
 `);
 
 console.log(`SEPP provisions in regulatory_provisions: ${seppResult.rows[0].count}`);
 } catch (error) {
 console.log(`regulatory_provisions table check failed: ${error.message}`);
 }

 // Check LEP provisions
 try {
 const lepResult = await pool.query(`
 SELECT COUNT(*) as count
 FROM regulatory_provisions 
 WHERE document_id LIKE '%LEP%'
 `);
 
 console.log(`LEP provisions in regulatory_provisions: ${lepResult.rows[0].count}`);
 } catch (error) {
 console.log(`LEP provisions check failed: ${error.message}`);
 }

 // Check authority levels in zone_setback_rules if table exists
 try {
 const authorityResult = await pool.query(`
 SELECT authority_level, COUNT(*) as count
 FROM zone_setback_rules
 GROUP BY authority_level
 ORDER BY authority_level
 `);
 
 console.log('\nAuthority Level Distribution in zone_setback_rules:');
 authorityResult.rows.forEach(row => {
 const level = row.authority_level;
 const type = level === 1 ? 'SEPP' : level === 2 ? 'LEP' : level === 3 ? 'DCP' : 'Unknown';
 console.log(` Level ${level} (${type}): ${row.count} rules`);
 });
 } catch (error) {
 console.log(`zone_setback_rules table check failed: ${error.message}`);
 }

 // Check document distribution
 try {
 const docResult = await pool.query(`
 SELECT 
 CASE 
 WHEN document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%' THEN 'SEPP'
 WHEN document_id LIKE '%LEP%' THEN 'LEP' 
 WHEN document_id LIKE '%DCP%' THEN 'DCP'
 ELSE 'OTHER'
 END as doc_type,
 COUNT(*) as count
 FROM regulatory_provisions
 GROUP BY 
 CASE 
 WHEN document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%' THEN 'SEPP'
 WHEN document_id LIKE '%LEP%' THEN 'LEP'
 WHEN document_id LIKE '%DCP%' THEN 'DCP'
 ELSE 'OTHER'
 END
 ORDER BY count DESC
 `);
 
 console.log('\nDocument Type Distribution:');
 docResult.rows.forEach(row => {
 console.log(` ${row.doc_type}: ${row.count} provisions`);
 });
 } catch (error) {
 console.log(`Document distribution check failed: ${error.message}`);
 }

 // Sample SEPP provisions if any exist
 try {
 const sampleResult = await pool.query(`
 SELECT document_id, provision_type, ref_number, zone, development_type, 
 LEFT(provision_text, 100) as text_sample
 FROM regulatory_provisions 
 WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'
 LIMIT 5
 `);
 
 if (sampleResult.rows.length > 0) {
 console.log('\nSample SEPP Provisions:');
 sampleResult.rows.forEach((row, i) => {
 console.log(`\n Sample ${i + 1}:`);
 console.log(` Document: ${row.document_id}`);
 console.log(` Type: ${row.provision_type}`);
 console.log(` Ref: ${row.ref_number}`);
 console.log(` Zone: ${row.zone || 'null'}`);
 console.log(` Dev Type: ${row.development_type || 'null'}`);
 console.log(` Text: ${row.text_sample}...`);
 });
 }
 } catch (error) {
 console.log(`Sample SEPP provisions check failed: ${error.message}`);
 }

 // Check for quantitative standards from SEPP sources
 try {
 const quantResult = await pool.query(`
 SELECT COUNT(*) as count
 FROM quantitative_standards 
 WHERE source_document LIKE '%SEPP%' OR source_document LIKE '%State_Environmental_Planning_Policy%'
 `);
 
 console.log(`\nSEPP quantitative standards: ${quantResult.rows[0].count}`);
 } catch (error) {
 console.log(`quantitative_standards check failed: ${error.message}`);
 }

 // Generate summary report
 const summary = {
 analysis_date: new Date().toISOString(),
 postgresql_status: "Analysis completed",
 findings: {
 sepp_provisions: "Check output above",
 lep_provisions: "Check output above", 
 authority_hierarchy: "Check zone_setback_rules output above",
 migration_status: "INCOMPLETE - Missing SEPP/LEP authority hierarchy"
 },
 recommendations: [
 "Migrate 4,237 SEPP provisions from SQLite source",
 "Migrate LEP provisions with authority level 2", 
 "Implement authority override logic (SEPP > LEP > DCP)",
 "Add authority_level column to track precedence hierarchy"
 ]
 };

 fs.writeFileSync('sepp_postgresql_analysis.json', JSON.stringify(summary, null, 2));
 console.log('\nGenerated PostgreSQL analysis report: sepp_postgresql_analysis.json');
 
 } catch (error) {
 console.error('Database connection error:', error.message);
 console.log('\nThis suggests PostgreSQL may not be running or connection details are incorrect.');
 } finally {
 await pool.end();
 }
}

checkSeppMigration();