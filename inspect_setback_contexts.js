const { Pool } = require('pg');

const pool = new Pool({
 host: 'localhost',
 port: 5432,
 database: 'nsw_planning',
 user: 'postgres',
 password: 'postgres'
});

async function inspectSetbackContexts() {
 console.log('='.repeat(60));
 console.log('QUANTITATIVE STANDARDS CONTEXT INSPECTION');
 console.log('='.repeat(60));

 try {
 // 1. Check what distinct context values exist in quantitative_standards table
 console.log('\n1. DISTINCT CONTEXT VALUES IN QUANTITATIVE_STANDARDS:');
 console.log('-'.repeat(50));
 const allContexts = await pool.query(`
 SELECT DISTINCT context, COUNT(*) as count
 FROM public.quantitative_standards 
 WHERE context IS NOT NULL
 GROUP BY context
 ORDER BY context
 `);
 
 allContexts.rows.forEach(row => {
 console.log(` ${row.context}: ${row.count} records`);
 });

 // 2. See specifically what contexts are available for zone R2
 console.log('\n2. CONTEXTS AVAILABLE FOR ZONE R2:');
 console.log('-'.repeat(50));
 const r2Contexts = await pool.query(`
 SELECT DISTINCT qs.context, COUNT(*) as count
 FROM public.quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE rp.zone = 'R2' AND qs.context IS NOT NULL
 GROUP BY qs.context
 ORDER BY qs.context
 `);
 
 if (r2Contexts.rows.length === 0) {
 console.log(' No records found for zone R2');
 } else {
 r2Contexts.rows.forEach(row => {
 console.log(` ${row.context}: ${row.count} records`);
 });
 }

 // 3. Check setback-related contexts specifically
 console.log('\n3. SETBACK-RELATED CONTEXTS (containing "setback"):');
 console.log('-'.repeat(50));
 const setbackContexts = await pool.query(`
 SELECT DISTINCT context, COUNT(*) as count
 FROM public.quantitative_standards 
 WHERE context ILIKE '%setback%'
 GROUP BY context
 ORDER BY context
 `);
 
 if (setbackContexts.rows.length === 0) {
 console.log(' No setback-related contexts found');
 } else {
 setbackContexts.rows.forEach(row => {
 console.log(` ${row.context}: ${row.count} records`);
 });
 }

 // 4. Check for front/side/rear setback patterns
 console.log('\n4. FRONT/SIDE/REAR SETBACK PATTERNS:');
 console.log('-'.repeat(50));
 const setbackTypes = await pool.query(`
 SELECT DISTINCT context, COUNT(*) as count
 FROM public.quantitative_standards 
 WHERE context ILIKE '%front%' 
 OR context ILIKE '%side%' 
 OR context ILIKE '%rear%'
 OR context ILIKE '%boundary%'
 GROUP BY context
 ORDER BY context
 `);
 
 if (setbackTypes.rows.length === 0) {
 console.log(' No front/side/rear setback patterns found');
 } else {
 setbackTypes.rows.forEach(row => {
 console.log(` ${row.context}: ${row.count} records`);
 });
 }

 // 5. Sample records for R2 zone if any exist
 console.log('\n5. SAMPLE RECORDS FOR R2 ZONE:');
 console.log('-'.repeat(50));
 const r2Samples = await pool.query(`
 SELECT 
 qs.id,
 qs.numeric_value,
 qs.context,
 rp.zone,
 rp.development_type,
 rp.ref_number,
 LEFT(rp.provision_text, 80) as text_sample
 FROM public.quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE rp.zone = 'R2'
 ORDER BY qs.context, qs.id
 LIMIT 10
 `);
 
 if (r2Samples.rows.length === 0) {
 console.log(' No records found for zone R2');
 } else {
 r2Samples.rows.forEach(row => {
 console.log(` ID ${row.id}: ${row.numeric_value} ${row.context || 'NO_CONTEXT'} | ${row.development_type || 'NO_DEV_TYPE'} | ${row.ref_number || 'NO_REF'}`);
 if (row.text_sample) {
 console.log(` Text: ${row.text_sample}...`);
 }
 });
 }

 // 6. Check all zones that have setback-related data
 console.log('\n6. ZONES WITH SETBACK DATA:');
 console.log('-'.repeat(50));
 const zonesWithSetbacks = await pool.query(`
 SELECT 
 rp.zone,
 COUNT(DISTINCT qs.context) as context_types,
 COUNT(*) as total_records
 FROM public.quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE qs.context ILIKE '%setback%'
 OR qs.context ILIKE '%front%' 
 OR qs.context ILIKE '%side%' 
 OR qs.context ILIKE '%rear%'
 OR qs.context ILIKE '%boundary%'
 GROUP BY rp.zone
 ORDER BY total_records DESC, rp.zone
 `);
 
 if (zonesWithSetbacks.rows.length === 0) {
 console.log(' No zones found with setback data');
 } else {
 zonesWithSetbacks.rows.forEach(row => {
 console.log(` ${row.zone || 'NULL_ZONE'}: ${row.context_types} different contexts, ${row.total_records} total records`);
 });
 }

 } catch (error) {
 console.error('Error:', error.message);
 } finally {
 await pool.end();
 }
}

inspectSetbackContexts();