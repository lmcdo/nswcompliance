/**
 * Browse Documents API - List All DCP Documents
 * Returns all DCP documents with TOC availability status
 *
 * Purpose: Populate document selector in /browse route
 * Use case: Show all 82 Marrickville DCP documents (57 with TOC, 25 without)
 */

export const dynamic = 'force-dynamic';

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { dataRateLimiter, getClientIdentifier, checkRateLimit, createRateLimitHeaders } from '@/lib/rate-limit';
import { captureServerException } from '@/lib/posthog-server';

interface Document {
  documentId: string;
  label: string;
  hasTOC: boolean;
  provisionCount: number;
  partNumber: string | null;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const clientIP = getClientIdentifier(request);
    const rateLimitResult = await checkRateLimit(clientIP, dataRateLimiter, 30, 60000);
    if (!rateLimitResult.success) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again in a minute.' },
        { status: 429, headers: createRateLimitHeaders(rateLimitResult) }
      );
    }

    console.log('[Browse Documents] Fetching all DCP documents');

    // Get all DCP documents with TOC status and provision counts
    const result = await query(`
      SELECT
        p.document_id,
        EXISTS(
          SELECT 1 FROM dcp_table_of_contents t
          WHERE t.document_id = p.document_id
        ) as has_toc,
        COUNT(p.id) as provision_count
      FROM regulatory_provisions p
      WHERE p.is_current = TRUE
        AND (p.document_id LIKE '%Marrickville_DCP%'
          OR p.document_id LIKE '%Ashfield_DCP%'
          OR p.document_id LIKE '%Leichhardt_DCP%')
      GROUP BY p.document_id
      ORDER BY p.document_id
    `);

    // Transform to friendly labels and extract DCP info
    const documents: Document[] = result.rows.map((row) => {
      const docId = row.document_id;

      let label = docId;
      let partNumber = null;
      let dcpName = 'Other';

      // Determine which DCP this belongs to
      if (docId.includes('Marrickville_DCP')) {
        dcpName = 'Marrickville DCP 2011';
      } else if (docId.includes('Ashfield_DCP')) {
        dcpName = 'Ashfield DCP 2016';
      } else if (docId.includes('Leichhardt_DCP')) {
        dcpName = 'Leichhardt DCP 2013';
      } else if (docId.includes('Inner_West')) {
        // Inner West branded documents are part of Ashfield DCP
        dcpName = 'Ashfield DCP 2016';
      }

      // Replace underscores with spaces, but keep section numbers
      if (docId.includes('__')) {
        const parts = docId.split('__');
        const section = parts[1].replace(/_/g, ' '); // "2 10 Parking" or "4.1 Low Density..."

        let sectionClean = '';

        // For Ashfield chapters, use document_id to determine label
        if (docId.includes('Ashfield') || docId.includes('Inner_West')) {
          if (docId.includes('Miscellaneous')) {
            sectionClean = 'Chapter A: Miscellaneous';
          } else if (docId.includes('Public_Domain')) {
            sectionClean = 'Chapter B: Public Domain';
          } else if (docId.includes('Sustainability')) {
            sectionClean = 'Chapter C: Sustainability';
          } else if (docId.includes('Precinct_Guidelines')) {
            sectionClean = 'Chapter D: Precinct Guidelines';
          } else if (docId.includes('E1') && docId.includes('Heritage')) {
            sectionClean = 'Chapter E1: Heritage';
          } else if (docId.includes('Development_Category')) {
            sectionClean = 'Chapter F: Development Categories';
          } else if (docId.includes('Definitions')) {
            sectionClean = 'Chapter G: Definitions';
          } else if (docId.includes('Chapter_H')) {
            sectionClean = 'Chapter H';
          } else if (docId.includes('Preliminary')) {
            sectionClean = 'Preliminary & Notification';
          }
        }
        // For Leichhardt parts, use document_id to determine label
        else if (docId.includes('Leichhardt_DCP')) {
          if (docId.includes('__3__Part_A')) {
            sectionClean = 'Part A: Introduction';
          } else if (docId.includes('__4__Part_B')) {
            sectionClean = 'Part B: Connections';
          } else if (docId.includes('__5__Part_C')) {
            sectionClean = 'Part C: Section 1';
          } else if (docId.includes('__6__Part_C_Place_Section_2')) {
            sectionClean = 'Part C: Section 2';
          } else if (docId.includes('__7__Part_C')) {
            sectionClean = 'Part C: Section 3';
          } else if (docId.includes('__8__Part_C')) {
            sectionClean = 'Part C: Section 4';
          } else if (docId.includes('Part_C_Section_5')) {
            sectionClean = 'Part C: Section 5';
          } else if (docId.includes('__9__Part_D')) {
            sectionClean = 'Part D: Energy';
          } else if (docId.includes('__10__Part_E')) {
            sectionClean = 'Part E: Water';
          } else if (docId.includes('__11__Part_F')) {
            sectionClean = 'Part F: Food';
          } else if (docId.includes('Part_G')) {
            // Part G has multiple sections
            if (docId.includes('Section_13')) {
              sectionClean = 'Part G: Section 13 (Pyrmont Bridge Rd)';
            } else if (docId.includes('1_50')) {
              sectionClean = 'Part G: Sections 1-12 (Pages 1-50)';
            } else if (docId.includes('51_100')) {
              sectionClean = 'Part G: Sections 1-12 (Pages 51-100)';
            } else if (docId.includes('101_149')) {
              sectionClean = 'Part G: Sections 1-12 (Pages 101-149)';
            } else {
              sectionClean = 'Part G: Development Controls';
            }
          } else if (docId.includes('__13__Appendix_A')) {
            sectionClean = 'Appendix A: Glossary';
          } else if (docId.includes('__14__Appendix_B')) {
            sectionClean = 'Appendix B: Building Typologies';
          } else if (docId.includes('__15')) {
            sectionClean = 'Appendix C: Urban Framework Plans';
          } else if (docId.includes('__17__Appendix_E')) {
            sectionClean = 'Appendix E: Water Guidelines';
          }
        }

        // If not yet labeled (Marrickville or unknown), clean up section name
        if (!sectionClean) {
          sectionClean = section
            .replace(/^(\d+)\s+(\d+)/, '$1.$2') // "2 10" → "2.10"
            .replace(/^(\d+)\.(\d+)\s/, '$1.$2 ') // Already has dot
            .replace(/\s+and\s+/g, ' & ') // "and" → "&"
            .replace(/\s{2,}/g, ' ') // Multiple spaces → single space
            .replace(/with IWLEP.*$/i, '') // Remove amendment text
            .replace(/Amdt.*$/i, '') // Remove amendment references
            .trim();
        }

        // Extract part number for Marrickville sections
        const partMatch = sectionClean.match(/^(\d+)\./);
        if (partMatch && dcpName === 'Marrickville DCP 2011') {
          partNumber = `Part ${partMatch[1]}`;
        }

        label = sectionClean;
      }

      return {
        documentId: docId,
        label,
        hasTOC: row.has_toc,
        provisionCount: parseInt(row.provision_count),
        partNumber: dcpName // Use DCP name for grouping instead of part number
      };
    });

    // Group by DCP name
    const grouped: Record<string, Document[]> = {};
    documents.forEach(doc => {
      const dcp = doc.partNumber || 'Other';
      if (!grouped[dcp]) {
        grouped[dcp] = [];
      }
      grouped[dcp].push(doc);
    });

    // Sort documents within each group by label
    Object.keys(grouped).forEach(key => {
      grouped[key].sort((a, b) => {
        // Natural sort for section numbers
        const aNum = a.label.match(/^[\d.]+/);
        const bNum = b.label.match(/^[\d.]+/);
        if (aNum && bNum) {
          return parseFloat(aNum[0]) - parseFloat(bNum[0]);
        }
        return a.label.localeCompare(b.label);
      });
    });

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        documents,
        grouped,
        totalDocuments: documents.length,
        withTOC: documents.filter(d => d.hasTOC).length,
        withoutTOC: documents.filter(d => !d.hasTOC).length
      },
      meta: {
        responseTimeMs: responseTime,
        source: 'regulatory_provisions + dcp_table_of_contents'
      }
    });

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('[Browse Documents] Error:', error);
    captureServerException(error, { endpoint: '/api/browse/documents' });

    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error',
        responseTimeMs: responseTime
      },
      { status: 500 }
    );
  }
}
