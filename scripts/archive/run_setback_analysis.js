/**
 * Setback Provisions Analysis Script
 *
 * Queries the database to analyze setback provisions across all 3 Inner West councils.
 * Outputs results to console and saves to JSON for further analysis.
 *
 * Usage: node scripts/run_setback_analysis.js
 */

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config({ path: path.join(__dirname, '../frontend-nextjs/.env.local') });

// Create database connection
const pool = new Pool({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

async function runAnalysis() {
  const results = {
    timestamp: new Date().toISOString(),
    overview: null,
    marrickville: { numerical: [], interpretive: [] },
    ashfield: { numerical: [], interpretive: [] },
    leichhardt: { numerical: [], interpretive: [] },
    patterns: {
      byCategory: [],
      formulaBased: [],
      streetscapeCharacter: [],
    },
    zoneSpecific: [],
    precinctSpecific: [],
    summary: null,
  };

  console.log('='.repeat(80));
  console.log('SETBACK PROVISIONS ANALYSIS');
  console.log('='.repeat(80));
  console.log('');

  try {
    // 1. Overview
    console.log('>>> SECTION 1: Overview');
    const overviewResult = await pool.query(`
      SELECT
        former_council,
        COUNT(*) as total_setback_provisions,
        COUNT(CASE WHEN value_numeric IS NOT NULL THEN 1 END) as with_numeric_value,
        COUNT(CASE WHEN value_numeric IS NULL THEN 1 END) as without_numeric_value,
        ROUND(100.0 * COUNT(CASE WHEN value_numeric IS NOT NULL THEN 1 END) / NULLIF(COUNT(*), 0), 1) as pct_numeric
      FROM dcp_general_requirements
      WHERE category ILIKE '%setback%'
      GROUP BY former_council
      ORDER BY former_council
    `);
    results.overview = overviewResult.rows;
    console.table(overviewResult.rows);
    console.log('');

    // 2. Marrickville
    console.log('>>> SECTION 2: MARRICKVILLE');

    // 2a. Numerical
    const mvilleNumResult = await pool.query(`
      SELECT
        category,
        subcategory,
        requirement_text,
        value_numeric,
        value_min,
        value_max,
        unit,
        has_conditionals,
        conditional_text,
        confidence,
        pdf_page
      FROM dcp_general_requirements
      WHERE former_council = 'Marrickville'
      AND category ILIKE '%setback%'
      AND value_numeric IS NOT NULL
      ORDER BY category, value_numeric
    `);
    results.marrickville.numerical = mvilleNumResult.rows;
    console.log(`Marrickville NUMERICAL: ${mvilleNumResult.rows.length} provisions`);
    if (mvilleNumResult.rows.length > 0) {
      console.table(mvilleNumResult.rows.slice(0, 10).map(r => ({
        category: r.category,
        value: `${r.value_numeric}${r.unit || 'm'}`,
        conditional: r.has_conditionals ? 'Yes' : 'No',
        text: r.requirement_text?.substring(0, 80) + '...'
      })));
    }

    // 2b. Interpretive
    const mvilleInterpResult = await pool.query(`
      SELECT
        category,
        subcategory,
        requirement_text,
        has_conditionals,
        conditional_text,
        confidence,
        pdf_page
      FROM dcp_general_requirements
      WHERE former_council = 'Marrickville'
      AND category ILIKE '%setback%'
      AND value_numeric IS NULL
      ORDER BY category
      LIMIT 30
    `);
    results.marrickville.interpretive = mvilleInterpResult.rows;
    console.log(`Marrickville INTERPRETIVE: ${mvilleInterpResult.rows.length} provisions`);
    console.log('');

    // 3. Ashfield
    console.log('>>> SECTION 3: ASHFIELD');

    const ashfieldNumResult = await pool.query(`
      SELECT
        category,
        subcategory,
        requirement_text,
        value_numeric,
        value_min,
        value_max,
        unit,
        has_conditionals,
        conditional_text,
        confidence,
        pdf_page
      FROM dcp_general_requirements
      WHERE former_council = 'Ashfield'
      AND category ILIKE '%setback%'
      AND value_numeric IS NOT NULL
      ORDER BY category, value_numeric
    `);
    results.ashfield.numerical = ashfieldNumResult.rows;
    console.log(`Ashfield NUMERICAL: ${ashfieldNumResult.rows.length} provisions`);
    if (ashfieldNumResult.rows.length > 0) {
      console.table(ashfieldNumResult.rows.slice(0, 10).map(r => ({
        category: r.category,
        value: `${r.value_numeric}${r.unit || 'm'}`,
        conditional: r.has_conditionals ? 'Yes' : 'No',
        text: r.requirement_text?.substring(0, 80) + '...'
      })));
    }

    const ashfieldInterpResult = await pool.query(`
      SELECT
        category,
        subcategory,
        requirement_text,
        has_conditionals,
        conditional_text,
        confidence,
        pdf_page
      FROM dcp_general_requirements
      WHERE former_council = 'Ashfield'
      AND category ILIKE '%setback%'
      AND value_numeric IS NULL
      ORDER BY category
      LIMIT 30
    `);
    results.ashfield.interpretive = ashfieldInterpResult.rows;
    console.log(`Ashfield INTERPRETIVE: ${ashfieldInterpResult.rows.length} provisions`);
    console.log('');

    // 4. Leichhardt
    console.log('>>> SECTION 4: LEICHHARDT');

    const leichNumResult = await pool.query(`
      SELECT
        category,
        subcategory,
        requirement_text,
        value_numeric,
        value_min,
        value_max,
        unit,
        has_conditionals,
        conditional_text,
        confidence,
        pdf_page
      FROM dcp_general_requirements
      WHERE former_council = 'Leichhardt'
      AND category ILIKE '%setback%'
      AND value_numeric IS NOT NULL
      ORDER BY category, value_numeric
    `);
    results.leichhardt.numerical = leichNumResult.rows;
    console.log(`Leichhardt NUMERICAL: ${leichNumResult.rows.length} provisions`);
    if (leichNumResult.rows.length > 0) {
      console.table(leichNumResult.rows.slice(0, 10).map(r => ({
        category: r.category,
        value: `${r.value_numeric}${r.unit || 'm'}`,
        conditional: r.has_conditionals ? 'Yes' : 'No',
        text: r.requirement_text?.substring(0, 80) + '...'
      })));
    }

    const leichInterpResult = await pool.query(`
      SELECT
        category,
        subcategory,
        requirement_text,
        has_conditionals,
        conditional_text,
        confidence,
        pdf_page
      FROM dcp_general_requirements
      WHERE former_council = 'Leichhardt'
      AND category ILIKE '%setback%'
      AND value_numeric IS NULL
      ORDER BY category
      LIMIT 30
    `);
    results.leichhardt.interpretive = leichInterpResult.rows;
    console.log(`Leichhardt INTERPRETIVE: ${leichInterpResult.rows.length} provisions`);
    console.log('');

    // 5. Pattern Analysis
    console.log('>>> SECTION 5: PATTERN ANALYSIS');

    // Categories breakdown
    const categoryResult = await pool.query(`
      SELECT
        former_council,
        category,
        COUNT(*) as count
      FROM dcp_general_requirements
      WHERE category ILIKE '%setback%'
      GROUP BY former_council, category
      ORDER BY former_council, count DESC
    `);
    results.patterns.byCategory = categoryResult.rows;
    console.log('Categories by council:');
    console.table(categoryResult.rows);

    // Formula-based provisions
    const formulaResult = await pool.query(`
      SELECT
        former_council,
        category,
        requirement_text,
        value_numeric,
        unit
      FROM dcp_general_requirements
      WHERE category ILIKE '%setback%'
      AND (
        requirement_text ILIKE '%% of%'
        OR requirement_text ILIKE '%times%'
        OR requirement_text ILIKE '%x height%'
        OR requirement_text ILIKE '%or greater%'
        OR requirement_text ILIKE '%whichever%'
      )
      ORDER BY former_council
      LIMIT 30
    `);
    results.patterns.formulaBased = formulaResult.rows;
    console.log(`\nFormula-based provisions: ${formulaResult.rows.length}`);
    if (formulaResult.rows.length > 0) {
      formulaResult.rows.slice(0, 5).forEach(r => {
        console.log(`  [${r.former_council}] ${r.requirement_text?.substring(0, 100)}...`);
      });
    }

    // Streetscape/character provisions
    const streetscapeResult = await pool.query(`
      SELECT
        former_council,
        category,
        requirement_text
      FROM dcp_general_requirements
      WHERE category ILIKE '%setback%'
      AND (
        requirement_text ILIKE '%streetscape%'
        OR requirement_text ILIKE '%character%'
        OR requirement_text ILIKE '%consistent with%'
        OR requirement_text ILIKE '%in keeping%'
        OR requirement_text ILIKE '%established%'
      )
      ORDER BY former_council
      LIMIT 20
    `);
    results.patterns.streetscapeCharacter = streetscapeResult.rows;
    console.log(`\nStreetscape/character provisions: ${streetscapeResult.rows.length}`);
    if (streetscapeResult.rows.length > 0) {
      streetscapeResult.rows.slice(0, 5).forEach(r => {
        console.log(`  [${r.former_council}] ${r.requirement_text?.substring(0, 100)}...`);
      });
    }
    console.log('');

    // 6. Zone-specific
    console.log('>>> SECTION 6: ZONE-SPECIFIC SETBACKS');
    const zoneResult = await pool.query(`
      SELECT
        former_council,
        category,
        applicable_zones,
        requirement_text,
        value_numeric,
        unit
      FROM dcp_general_requirements
      WHERE category ILIKE '%setback%'
      AND applicable_zones IS NOT NULL
      AND array_length(applicable_zones, 1) > 0
      ORDER BY former_council, applicable_zones
      LIMIT 30
    `);
    results.zoneSpecific = zoneResult.rows;
    console.log(`Zone-specific setbacks: ${zoneResult.rows.length}`);
    if (zoneResult.rows.length > 0) {
      console.table(zoneResult.rows.slice(0, 10).map(r => ({
        council: r.former_council,
        zones: r.applicable_zones?.join(', '),
        value: r.value_numeric ? `${r.value_numeric}${r.unit || 'm'}` : 'N/A',
        text: r.requirement_text?.substring(0, 60) + '...'
      })));
    }
    console.log('');

    // 7. Precinct-specific
    console.log('>>> SECTION 7: PRECINCT-SPECIFIC SETBACKS');
    const precinctResult = await pool.query(`
      SELECT
        precinct_name,
        category,
        requirement_text,
        value_numeric,
        unit,
        confidence
      FROM dcp_precinct_requirements
      WHERE category ILIKE '%setback%'
      ORDER BY precinct_name
      LIMIT 40
    `);
    results.precinctSpecific = precinctResult.rows;
    console.log(`Precinct-specific setbacks: ${precinctResult.rows.length}`);
    if (precinctResult.rows.length > 0) {
      console.table(precinctResult.rows.slice(0, 10).map(r => ({
        precinct: r.precinct_name?.substring(0, 25),
        category: r.category,
        value: r.value_numeric ? `${r.value_numeric}${r.unit || 'm'}` : 'N/A',
        text: r.requirement_text?.substring(0, 50) + '...'
      })));
    }
    console.log('');

    // 8. Summary
    console.log('>>> SECTION 8: SUMMARY');
    const summaryResult = await pool.query(`
      SELECT
        former_council,
        COUNT(*) FILTER (WHERE category = 'setbacks') as general_setbacks,
        COUNT(*) FILTER (WHERE category = 'setback_front') as front_setbacks,
        COUNT(*) FILTER (WHERE category = 'setback_side') as side_setbacks,
        COUNT(*) FILTER (WHERE category = 'setback_rear') as rear_setbacks,
        COUNT(*) FILTER (WHERE value_numeric IS NOT NULL) as calculable,
        COUNT(*) FILTER (WHERE requirement_text ILIKE '%streetscape%' OR requirement_text ILIKE '%character%') as interpretive,
        COUNT(*) FILTER (WHERE requirement_text ILIKE '%% of%' OR requirement_text ILIKE '%times%') as formula_based
      FROM dcp_general_requirements
      WHERE category ILIKE '%setback%'
      GROUP BY former_council
      ORDER BY former_council
    `);
    results.summary = summaryResult.rows;
    console.table(summaryResult.rows);

    // Save to JSON
    const outputPath = path.join(__dirname, '../setback_analysis_results.json');
    fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
    console.log(`\n✓ Results saved to: ${outputPath}`);

    console.log('\n' + '='.repeat(80));
    console.log('ANALYSIS COMPLETE');
    console.log('='.repeat(80));

  } catch (error) {
    console.error('Error running analysis:', error);
    throw error;
  } finally {
    await pool.end();
  }
}

runAnalysis().catch(console.error);
