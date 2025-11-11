import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection (PRP-A1 compliant)
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  statement_timeout: 30000  // 30 second timeout
});

/**
 * Extract a specific clause from LEP full text
 * Searches for clause pattern and extracts until next clause starts
 */
function extractClause(fullText: string, refNumber: string): string | null {
  // Pattern: line starting with clause number, followed by newline and heading
  // e.g. "4.3\nHeight of buildings\n(1) The objectives..."
  // NOT "4.3 Height of buildings ........ 36" (that's TOC)

  const escapedRef = refNumber.replace(/\./g, '\\.');

  // Look for pattern: "\n4.3\nHeading text" (clause on its own line)
  const pattern = new RegExp(`\\n${escapedRef}\\n([A-Z][^\\n]+)\\n`, 'g');

  let bestMatch = null;
  let match;

  // Find all matches and pick the one that looks like actual content (not TOC)
  while ((match = pattern.exec(fullText)) !== null) {
    const startPos = match.index;
    const contextAfter = fullText.substring(startPos, startPos + 200);

    // Skip if it looks like TOC (has dots: ".....")
    if (contextAfter.includes('.....')) {
      continue;
    }

    // This looks like the actual clause
    bestMatch = match;
    break;
  }

  if (!bestMatch) return null;

  const startPos = bestMatch.index;

  // Find where next major clause starts (e.g. "4.4\n" or "4.3A\n")
  const nextClausePattern = /\n\d+\.\d+[A-Z]?\n[A-Z]/g;
  nextClausePattern.lastIndex = startPos + 20; // Start searching after current clause

  const nextMatch = nextClausePattern.exec(fullText);
  const endPos = nextMatch ? nextMatch.index : startPos + 5000; // Max 5000 chars

  return fullText.substring(startPos, endPos).trim();
}

export async function POST(request: NextRequest) {
  try {
    const { documentId, refNumber } = await request.json();

    if (!documentId || !refNumber) {
      return NextResponse.json(
        { success: false, error: 'Missing documentId or refNumber' },
        { status: 400 }
      );
    }

    console.log('[LEP Full Text] Fetching:', { documentId, refNumber });

    // Get full text from documents table
    const docQuery = `
      SELECT id, pdf_name, full_text
      FROM documents
      WHERE id = $1
      LIMIT 1
    `;

    const docResult = await pool.query(docQuery, [documentId]);

    if (docResult.rows.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Document not found' },
        { status: 404 }
      );
    }

    const { full_text, pdf_name } = docResult.rows[0];

    // Extract the specific clause from full text
    const clauseText = extractClause(full_text, refNumber);

    if (!clauseText) {
      return NextResponse.json(
        { success: false, error: `Clause ${refNumber} not found in document` },
        { status: 404 }
      );
    }

    console.log('[LEP Full Text] Extracted', clauseText.length, 'chars for clause', refNumber);

    // Return in same format as regulatory_provisions for compatibility
    const provisions = [{
      id: 0, // No provision ID for extracted clauses
      document_id: documentId,
      ref_number: refNumber,
      section_header: pdf_name,
      provision_text: clauseText
    }];

    return NextResponse.json({
      success: true,
      data: {
        provisions
      },
      metadata: {
        documentId,
        refNumber,
        count: provisions.length,
        extractedFromFullText: true
      }
    });

  } catch (error) {
    console.error('[LEP Full Text] Database error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch LEP text'
      },
      { status: 500 }
    );
  }
}