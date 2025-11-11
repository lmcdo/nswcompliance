import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning', // Correct database
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
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

  try {
    // Simple fast query - provision_text IS the full text
    const result = await pool.query(`
      SELECT
        id,
        ref_number,
        provision_text,
        document_id,
        section_header,
        provision_type,
        full_text_length
      FROM regulatory_provisions_canonical
      WHERE id = $1
    `, [provisionId]);

    if (result.rows.length === 0) {
      return NextResponse.json(
        { error: 'Provision not found' },
        { status: 404 }
      );
    }

    const provision = result.rows[0];

    // Determine document type from document_id
    let instrumentType = 'DCP';
    let precedence = 3;

    if (provision.document_id?.includes('SEPP') || provision.document_id?.includes('State_Environmental')) {
      instrumentType = 'SEPP';
      precedence = 1;
    } else if (provision.document_id?.includes('LEP') || provision.document_id?.includes('Environmental_Plan')) {
      instrumentType = 'LEP';
      precedence = 2;
    }

    const response: CompleteProvisionResponse = {
      id: provision.id,
      reference: provision.ref_number || 'N/A',
      excerptText: provision.provision_text?.substring(0, 200) || '',
      fullClauseText: provision.provision_text || null,
      legalPrecedence: precedence,
      instrumentType: instrumentType,
      documentTitle: provision.section_header || provision.document_id,
      documentId: provision.document_id,
      charCount: provision.full_text_length || provision.provision_text?.length || 0
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}