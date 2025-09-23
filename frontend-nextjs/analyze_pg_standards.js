const { Pool } = require('pg');
const pool = new Pool({host: 'localhost', port: 5432, database: 'nsw_planning', user: 'postgres', password: 'postgres'});

async function analyzePostgreStandards() {
 console.log('PostgreSQL Quantitative Standards Analysis:');
 console.log('='.repeat(50));

 try {
 // Check sample standards with provision details
 const samples = await pool.query(`
 SELECT 
 qs.id, qs.provision_id, qs.numeric_value, qs.context,
 rp.zone, rp.development_type, rp.ref_number, 
 LEFT(rp.provision_text, 100) as text_sample
 FROM quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE qs.context LIKE '%setback%'
 ORDER BY qs.id
 LIMIT 10
 `);

 console.log('Sample setback standards:');
 samples.rows.forEach(row => {
 console.log(`ID ${row.id}: ${row.zone || 'NULL'} ${row.development_type || 'NULL'} - ${row.numeric_value}${row.context} from '${row.ref_number || 'NO-REF'}' - ${row.text_sample}...`);
 });

 // Check sources of standards
 const sources = await pool.query(`
 SELECT 
 CASE 
 WHEN rp.ref_number LIKE 'C11%' THEN 'C11_MultiDwelling'
 WHEN rp.ref_number LIKE 'C12%' THEN 'C12_RFB' 
 WHEN rp.document_id LIKE '%DCP%' THEN 'DCP'
 WHEN rp.document_id LIKE '%LEP%' THEN 'LEP'
 WHEN rp.zone IS NULL THEN 'NULL_ZONE'
 ELSE 'Other'
 END as source_type,
 COUNT(*) as count
 FROM quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE qs.context LIKE '%setback%'
 GROUP BY source_type
 ORDER BY count DESC
 `);

 console.log('\nStandards by source:');
 sources.rows.forEach(s => {
 console.log(` ${s.source_type}: ${s.count} standards`);
 });

 // Check the NULL zone standards more closely
 const nullZones = await pool.query(`
 SELECT 
 rp.document_id,
 COUNT(*) as count
 FROM quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE qs.context LIKE '%setback%'
 AND rp.zone IS NULL
 GROUP BY rp.document_id
 ORDER BY count DESC
 LIMIT 5
 `);

 console.log('\nNull zone standards by document:');
 nullZones.rows.forEach(n => {
 console.log(` ${n.document_id}: ${n.count} standards`);
 });

 // Check how standards are actually created
 const recentStandards = await pool.query(`
 SELECT 
 qs.created_timestamp,
 rp.zone,
 rp.development_type,
 rp.document_id,
 COUNT(*) as count
 FROM quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE qs.context LIKE '%setback%'
 AND qs.created_timestamp IS NOT NULL
 GROUP BY qs.created_timestamp, rp.zone, rp.development_type, rp.document_id
 ORDER BY qs.created_timestamp DESC
 LIMIT 10
 `);

 console.log('\nRecent standards creation:');
 if (recentStandards.rows.length === 0) {
 console.log(' No timestamps found - standards created without timestamps');
 } else {
 recentStandards.rows.forEach(r => {
 console.log(` ${r.created_timestamp}: ${r.zone || 'NULL'} ${r.development_type || 'NULL'} - ${r.count} standards from ${r.document_id}`);
 });
 }

 } catch (error) {
 console.error('Analysis failed:', error.message);
 } finally {
 await pool.end();
 }
}

analyzePostgreStandards();