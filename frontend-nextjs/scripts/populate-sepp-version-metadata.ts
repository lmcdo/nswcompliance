#!/usr/bin/env tsx
import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function populateMetadata() {
  try {
    console.log('=== Populating SEPP Version Metadata ===\n');

    // Step 1: Extract regulation_year from pdf_name where NULL
    console.log('Step 1: Extracting regulation year from pdf_name...');
    const yearUpdate = await pool.query(`
      UPDATE documents
      SET regulation_year = (regexp_match(pdf_name, '(20\\d{2})'))[1]::integer
      WHERE document_type = 'SEPP'
        AND pdf_name IS NOT NULL
        AND regulation_year IS NULL
        AND pdf_name ~ '20\\d{2}'
      RETURNING id, pdf_name, regulation_year;
    `);

    console.log(`✅ Updated ${yearUpdate.rows.length} documents with regulation_year`);
    if (yearUpdate.rows.length > 0) {
      yearUpdate.rows.slice(0, 3).forEach((row: any) => {
        console.log(`  - ${row.pdf_name.substring(0, 60)}... → ${row.regulation_year}`);
      });
      if (yearUpdate.rows.length > 3) {
        console.log(`  ... and ${yearUpdate.rows.length - 3} more`);
      }
    }
    console.log('');

    // Step 2: Set consolidated_as_of_date = last_verified_date for initial state
    console.log('Step 2: Setting consolidated_as_of_date from last_verified_date...');
    const dateUpdate = await pool.query(`
      UPDATE documents
      SET consolidated_as_of_date = last_verified_date
      WHERE document_type = 'SEPP'
        AND last_verified_date IS NOT NULL
        AND consolidated_as_of_date IS NULL
      RETURNING id, pdf_name, consolidated_as_of_date;
    `);

    console.log(`✅ Updated ${dateUpdate.rows.length} documents with consolidated_as_of_date`);
    if (dateUpdate.rows.length > 0) {
      dateUpdate.rows.slice(0, 3).forEach((row: any) => {
        const date = new Date(row.consolidated_as_of_date).toLocaleDateString();
        console.log(`  - ${row.pdf_name.substring(0, 60)}... → ${date}`);
      });
      if (dateUpdate.rows.length > 3) {
        console.log(`  ... and ${dateUpdate.rows.length - 3} more`);
      }
    }
    console.log('');

    // Step 3: Populate consolidation_url using NSW Legislation pattern
    console.log('Step 3: Generating consolidation URLs...');

    const urlUpdate = await pool.query(`
      UPDATE documents
      SET consolidation_url = CASE
        -- Housing SEPP 2021
        WHEN pdf_name LIKE '%Housing%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0714'

        -- Transport & Infrastructure SEPP 2021
        WHEN pdf_name LIKE '%Transport%Infrastructure%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0732'

        -- Biodiversity & Conservation SEPP 2021
        WHEN pdf_name LIKE '%Biodiversity%Conservation%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0722'

        -- Resilience & Hazards SEPP 2021
        WHEN pdf_name LIKE '%Resilience%Hazards%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0730'

        -- Planning Systems SEPP 2021
        WHEN pdf_name LIKE '%Planning Systems%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0728'

        -- Industry & Employment SEPP 2021
        WHEN pdf_name LIKE '%Industry%Employment%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0726'

        -- Primary Production SEPP 2021
        WHEN pdf_name LIKE '%Primary Production%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2021-0733'

        -- Sustainable Buildings SEPP 2022
        WHEN pdf_name LIKE '%Sustainable Buildings%2022%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2022-0214'

        -- Exempt & Complying Codes SEPP 2008
        WHEN pdf_name LIKE '%Exempt%Complying%2008%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(COALESCE(consolidated_as_of_date, last_verified_date, CURRENT_DATE), 'YYYY-MM-DD') ||
          '/epi-2008-0572'

        ELSE NULL
      END
      WHERE document_type = 'SEPP'
        AND consolidation_url IS NULL
        AND is_superseded = false
      RETURNING id, pdf_name, consolidation_url;
    `);

    console.log(`✅ Updated ${urlUpdate.rows.length} documents with consolidation_url`);
    if (urlUpdate.rows.length > 0) {
      urlUpdate.rows.slice(0, 2).forEach((row: any) => {
        console.log(`  - ${row.pdf_name.substring(0, 40)}...`);
        console.log(`    ${row.consolidation_url}`);
      });
      if (urlUpdate.rows.length > 2) {
        console.log(`  ... and ${urlUpdate.rows.length - 2} more`);
      }
    }
    console.log('');

    // Step 4: Set next_check_date = consolidated_as_of_date + 90 days
    console.log('Step 4: Setting next check dates (90 days from consolidation)...');
    const checkDateUpdate = await pool.query(`
      UPDATE documents
      SET next_check_date = consolidated_as_of_date + INTERVAL '90 days'
      WHERE document_type = 'SEPP'
        AND consolidated_as_of_date IS NOT NULL
        AND next_check_date IS NULL
      RETURNING id, pdf_name, consolidated_as_of_date, next_check_date;
    `);

    console.log(`✅ Updated ${checkDateUpdate.rows.length} documents with next_check_date`);
    if (checkDateUpdate.rows.length > 0) {
      checkDateUpdate.rows.slice(0, 3).forEach((row: any) => {
        const consolidated = new Date(row.consolidated_as_of_date).toLocaleDateString();
        const nextCheck = new Date(row.next_check_date).toLocaleDateString();
        console.log(`  - ${row.pdf_name.substring(0, 50)}...`);
        console.log(`    Consolidated: ${consolidated} → Next check: ${nextCheck}`);
      });
      if (checkDateUpdate.rows.length > 3) {
        console.log(`  ... and ${checkDateUpdate.rows.length - 3} more`);
      }
    }
    console.log('');

    // Step 5: Update version_status = 'current' for non-superseded documents
    console.log('Step 5: Setting version_status to "current"...');
    const statusUpdate = await pool.query(`
      UPDATE documents
      SET version_status = 'current'
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND (version_status IS NULL OR version_status = 'unverified')
      RETURNING id, pdf_name, version_status;
    `);

    console.log(`✅ Updated ${statusUpdate.rows.length} documents to version_status='current'`);
    console.log('');

    // Final summary
    console.log('=== Final Summary ===');
    const summary = await pool.query(`
      SELECT
        COUNT(*) FILTER (WHERE regulation_year IS NOT NULL) as has_year,
        COUNT(*) FILTER (WHERE consolidated_as_of_date IS NOT NULL) as has_consolidated_date,
        COUNT(*) FILTER (WHERE consolidation_url IS NOT NULL) as has_url,
        COUNT(*) FILTER (WHERE next_check_date IS NOT NULL) as has_next_check,
        COUNT(*) FILTER (WHERE version_status = 'current') as status_current,
        COUNT(*) FILTER (WHERE is_superseded = false) as active_documents,
        COUNT(*) as total_documents
      FROM documents
      WHERE document_type = 'SEPP'
        AND pdf_name NOT LIKE '%Section%';
    `);

    const stats = summary.rows[0];
    console.log(`Total SEPP documents (non-section): ${stats.total_documents}`);
    console.log(`Active documents: ${stats.active_documents}`);
    console.log('');
    console.log('Metadata population:');
    console.log(`  regulation_year:           ${stats.has_year}/${stats.total_documents}`);
    console.log(`  consolidated_as_of_date:   ${stats.has_consolidated_date}/${stats.total_documents}`);
    console.log(`  consolidation_url:         ${stats.has_url}/${stats.active_documents} (active only)`);
    console.log(`  next_check_date:           ${stats.has_next_check}/${stats.total_documents}`);
    console.log(`  version_status='current':  ${stats.status_current}/${stats.active_documents} (active only)`);

    // Check for any missing data
    const missing = await pool.query(`
      SELECT
        id,
        pdf_name,
        CASE WHEN regulation_year IS NULL THEN 'year' ELSE NULL END as missing_year,
        CASE WHEN consolidated_as_of_date IS NULL THEN 'date' ELSE NULL END as missing_date,
        CASE WHEN consolidation_url IS NULL AND is_superseded = false THEN 'url' ELSE NULL END as missing_url,
        CASE WHEN next_check_date IS NULL THEN 'next_check' ELSE NULL END as missing_check
      FROM documents
      WHERE document_type = 'SEPP'
        AND pdf_name NOT LIKE '%Section%'
        AND (
          regulation_year IS NULL
          OR consolidated_as_of_date IS NULL
          OR (consolidation_url IS NULL AND is_superseded = false)
          OR next_check_date IS NULL
        );
    `);

    if (missing.rows.length > 0) {
      console.log('');
      console.log(`⚠️  ${missing.rows.length} documents still missing some metadata:`);
      missing.rows.forEach((row: any) => {
        const missingFields = [row.missing_year, row.missing_date, row.missing_url, row.missing_check].filter(Boolean);
        console.log(`  - ${row.pdf_name.substring(0, 60)}...`);
        console.log(`    Missing: ${missingFields.join(', ')}`);
      });
    } else {
      console.log('');
      console.log('✅ All active SEPP documents have complete version metadata!');
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

populateMetadata();
