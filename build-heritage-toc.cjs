/**
 * Build full TOC for Marrickville Heritage DCP 8.0 from content_list.json heading elements.
 *
 * Page number formula:
 *   base_pdf_page = page_idx + part_offset
 *   where part_offset is the heritage printed page number of Part's first page:
 *     Part1: offset=1  → heritage pages 1-62
 *     Part2: offset=63 → heritage pages 63-124
 *     Part3: offset=125→ heritage pages 125-186
 *     Part4: offset=187→ heritage pages 187-248
 *
 *   The base document provisions use pdf_page = heritage page number (1-indexed).
 *   Verified: Part1 page_idx=22 (section 8.1.8.2) → heritage page 23 → matches
 *   base doc provision at pdf_page=23.
 *
 * TOC entries are inserted for the base doc: Marrickville_DCP_2011__8.0_Heritage
 * (also matches Marrickville_DCP_2011_-_8.0_Heritage via SQL JOIN normalization)
 */

const { Pool } = require('./frontend-nextjs/node_modules/pg');
const { readFileSync } = require('fs');
const path = require('path');

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const ARCHIVE_BASE = 'archive/2026-01-pipeline-outputs/output';

// TOC entries will be inserted with this document_id (matches both base doc variants via JOIN)
const TOC_DOC_ID = 'Marrickville_DCP_2011__8.0_Heritage';

const PARTS = [
  {
    folder: 'Marrickville DCP 2011 - 8.0 Heritage - Part1 (pages 1-62)',
    partOffset: 1,
    // Part1 pages 0-13 (heritage pages 1-14) are the PDF's own table-of-contents.
    // Skip them — real section headings start at page_idx=14 (heritage page 15).
    minPageIdx: 14,
    maxPageIdx: 61,
  },
  {
    folder: 'Marrickville DCP 2011 - 8.0 Heritage - Part2 (pages 63-124)',
    partOffset: 63,
    minPageIdx: 0,
    maxPageIdx: 61,
  },
  {
    folder: 'Marrickville DCP 2011 - 8.0 Heritage - Part3 (pages 125-186)',
    partOffset: 125,
    minPageIdx: 0,
    maxPageIdx: 61,
  },
  {
    folder: 'Marrickville DCP 2011 - 8.0 Heritage - Part4 (pages 187-248)',
    partOffset: 187,
    minPageIdx: 0,
    maxPageIdx: 61,
  },
];

// Regex: numbered heritage section heading like "8.1.7" or "8.2.4.26 Corners"
const SECTION_RE = /^(8\.\d+(?:\.\d+)*)\s+(.*)/;
// Skip headings with dotted leaders (PDF table-of-contents page entries)
const DOTTED_LEADER_RE = /\.{3,}|\s{3,}\d+\s*$/;

function extractHeadings(part) {
  const filePath = path.join(
    ARCHIVE_BASE,
    part.folder,
    'auto',
    `${part.folder}_content_list.json`
  );

  let data;
  try {
    data = JSON.parse(readFileSync(filePath, 'utf8'));
  } catch (e) {
    console.log(`  SKIP: ${e.message}`);
    return [];
  }

  const headings = [];
  for (const elem of data) {
    if (!('text_level' in elem) || !elem.text) continue;

    const text = elem.text.trim();

    // Must match numbered section pattern
    const match = text.match(SECTION_RE);
    if (!match) continue;

    // Skip TOC-page headings (dotted leaders or trailing page number references)
    if (DOTTED_LEADER_RE.test(text)) continue;

    // Skip pages outside content range
    if (elem.page_idx < part.minPageIdx || elem.page_idx > part.maxPageIdx) continue;

    const sectionNumber = match[1];
    const sectionTitle = match[2].trim();
    const basePdfPage = elem.page_idx + part.partOffset;

    headings.push({ sectionNumber, sectionTitle, basePdfPage });
  }

  return headings;
}

async function main() {
  const dryRun = process.argv.includes('--dry-run');
  if (dryRun) console.log('=== DRY RUN ===\n');

  const allEntries = [];

  for (const part of PARTS) {
    const headings = extractHeadings(part);
    console.log(`${part.folder.split(' - ').pop()}: ${headings.length} section headings`);

    if (dryRun) {
      headings.slice(0, 10).forEach(h => {
        console.log(`  §${h.sectionNumber} p${h.basePdfPage}: ${h.sectionTitle.substring(0, 60)}`);
      });
      if (headings.length > 10) console.log(`  ... and ${headings.length - 10} more`);
    }

    // Assign page_end = next section's page_start - 1 (floor at page_start)
    for (let i = 0; i < headings.length; i++) {
      const next = headings[i + 1];
      const rawEnd = next
        ? next.basePdfPage - 1
        : part.partOffset + part.maxPageIdx; // last section → end of part
      const pageEnd = Math.max(rawEnd, headings[i].basePdfPage);

      const parts_arr = headings[i].sectionNumber.split('.');
      const depth = parts_arr.length;
      const parentSection = depth > 1 ? parts_arr.slice(0, -1).join('.') : null;

      allEntries.push({
        sectionNumber: headings[i].sectionNumber,
        sectionTitle: headings[i].sectionTitle,
        pageStart: headings[i].basePdfPage,
        pageEnd,
        depth,
        parentSection,
      });
    }
  }

  console.log(`\nTotal entries: ${allEntries.length}`);

  if (dryRun) {
    console.log('\nSample page assignments:');
    // Show a range around section 8.1.8
    const sample = allEntries.filter(e => e.sectionNumber.startsWith('8.1.8'));
    sample.forEach(e => console.log(`  §${e.sectionNumber} p${e.pageStart}-${e.pageEnd}: ${e.sectionTitle}`));
    console.log('\nVerification: section 8.1.8.2 should be at p23 to match provision pdf_page=23');
    await pool.end();
    return;
  }

  // Delete existing heritage TOC entries
  const { rowCount: deleted } = await pool.query(
    `DELETE FROM dcp_table_of_contents WHERE document_id LIKE '%Marrickville%Heritage%'`
  );
  console.log(`Deleted ${deleted} existing heritage TOC entries.`);

  // Insert new entries
  let inserted = 0;
  for (const e of allEntries) {
    await pool.query(
      `INSERT INTO dcp_table_of_contents
         (document_id, section_number, section_title, page_start, page_end, depth, parent_section)
       VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [TOC_DOC_ID, e.sectionNumber, e.sectionTitle, e.pageStart, e.pageEnd, e.depth, e.parentSection]
    );
    inserted++;
  }

  console.log(`Inserted ${inserted} TOC entries for '${TOC_DOC_ID}'.`);

  // Verify key sections
  const { rows } = await pool.query(`
    SELECT section_number, page_start, page_end, LEFT(section_title, 50) as title
    FROM dcp_table_of_contents
    WHERE document_id = $1 AND section_number LIKE '8.1.8%'
    ORDER BY page_start
  `, [TOC_DOC_ID]);
  console.log('\n=== Verification: section 8.1.8.x ===');
  rows.forEach(r => console.log(`  §${r.section_number} p${r.page_start}-${r.page_end}: ${r.title}`));
  console.log('\nExpected: 8.1.8.2 at p23 (matches base doc provision pdf_page=23)');

  await pool.end();
}

main().catch(e => { console.error(e.message); process.exit(1); });
