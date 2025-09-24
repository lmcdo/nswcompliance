import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

const pool = new Pool({
  host: 'localhost',
  database: 'nsw_planning_corrected', // Using corrected database
  user: 'postgres',
  password: 'postgres',
  port: 5432,
});

interface CompleteProvisionResponse {
  id: number;
  reference: string;
  excerptText: string;
  fullClauseText: string | null;
  legalPrecedence: number;
  instrumentType: string;
  documentTitle: string;
  documentId: string;
  charCount?: number;
}

function extractClauseFromDocument(fullText: string, clauseNumber: string): string | null {
  if (!fullText || !clauseNumber) return null;

  // Create patterns to find the clause
  const startPatterns = [
    new RegExp(`\\b${clauseNumber}\\s*[—―-].*?\\n`, 'i'),
    new RegExp(`\\b${clauseNumber}\\s+[A-Za-z]`, 'i'),
    new RegExp(`\\b${clauseNumber}\\b`, 'i')
  ];

  let startIndex = -1;
  for (const pattern of startPatterns) {
    const match = fullText.search(pattern);
    if (match !== -1) {
      startIndex = match;
      break;
    }
  }

  if (startIndex === -1) return null;

  // Find the end of this clause (next clause or chapter)
  const nextClause = getNextClauseNumber(clauseNumber);
  const endPatterns = [
    nextClause ? new RegExp(`\\b${nextClause}\\s*[—―-]`, 'i') : null,
    /Chapter\s+\d+/i,
    /Part\s+\d+/i,
    /Schedule\s+\d+/i
  ].filter(Boolean);

  let endIndex = fullText.length;
  for (const pattern of endPatterns) {
    const match = fullText.substring(startIndex + 100).search(pattern!);
    if (match !== -1) {
      const actualIndex = startIndex + 100 + match;
      if (actualIndex < endIndex) {
        endIndex = actualIndex;
      }
    }
  }

  // Extract and clean the text
  let clauseText = fullText.substring(startIndex, endIndex).trim();

  // Remove extra whitespace and normalize
  clauseText = clauseText.replace(/\s+/g, ' ').replace(/\n\s*\n/g, '\n\n');

  return clauseText;
}

function getNextClauseNumber(current: string): string | null {
  // Handle different clause numbering patterns
  const patterns = [
    /^(\d+)\.(\d+)$/, // 2.2 -> 2.3
    /^(\d+)\.(\d+)\((\d+)\)$/, // 3.1(2) -> 3.1(3)
    /^(\d+)$/ // 2 -> 3
  ];

  for (const pattern of patterns) {
    const match = current.match(pattern);
    if (match) {
      if (pattern === patterns[0]) { // x.y format
        const [, major, minor] = match;
        return `${major}.${parseInt(minor) + 1}`;
      } else if (pattern === patterns[1]) { // x.y(z) format
        const [, major, minor, sub] = match;
        return `${major}.${minor}(${parseInt(sub) + 1})`;
      } else if (pattern === patterns[2]) { // x format
        return `${parseInt(match[1]) + 1}`;
      }
    }
  }

  return null;
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const provisionId = parseInt(params.id);

  if (isNaN(provisionId)) {
    return NextResponse.json(
      { error: 'Invalid provision ID' },
      { status: 400 }
    );
  }

  const client = await pool.connect();

  try {
    // Single optimized query using the corrected database relationships
    const result = await client.query(`
      SELECT
        rp.id,
        rp.ref_number,
        rp.provision_text as excerpt_text,
        rp.document_id,
        li.instrument_type,
        li.legal_precedence,
        li.title,
        li.instrument_code,
        d.full_text as complete_document_text,
        d.char_count
      FROM regulatory_provisions rp
      JOIN legal_instruments li ON rp.instrument_id = li.id
      JOIN documents d ON d.id = rp.document_id
      WHERE rp.id = $1
    `, [provisionId]);

    if (result.rows.length === 0) {
      return NextResponse.json(
        { error: 'Provision not found' },
        { status: 404 }
      );
    }

    const provision = result.rows[0];

    // Extract the complete clause text from the full document
    const fullClauseText = extractClauseFromDocument(
      provision.complete_document_text,
      provision.ref_number
    );

    const response: CompleteProvisionResponse = {
      id: provision.id,
      reference: provision.ref_number,
      excerptText: provision.excerpt_text,
      fullClauseText: fullClauseText,
      legalPrecedence: provision.legal_precedence,
      instrumentType: provision.instrument_type,
      documentTitle: provision.title,
      documentId: provision.document_id,
      charCount: provision.char_count
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  } finally {
    client.release();
  }
}