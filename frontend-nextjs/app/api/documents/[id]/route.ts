/**
 * Full Document Text API
 * Returns complete DCP/LEP/SEPP document text with embedded images
 *
 * Purpose: Provide full context for provisions with images, figures, and tables
 * Use case: When user needs complete chapter text (not just truncated provisions)
 */

import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
});

interface DocumentResponse {
  id: string;
  pdfName: string;
  documentType: string;
  documentArea: string | null;
  charCount: number;
  wordCount: number;
  fullText: string;
  extractionTimestamp: string;
  metadata: {
    imageCount: number;
    sectionCount: number;
    hasVisualElements: boolean;
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const startTime = Date.now();
  const documentId = params.id;

  if (!documentId) {
    return NextResponse.json(
      { error: 'Document ID is required' },
      { status: 400 }
    );
  }

  try {
    // Query documents table for full text
    const documentResult = await pool.query(`
      SELECT
        id,
        pdf_name,
        document_type,
        document_area,
        char_count,
        word_count,
        full_text,
        extraction_timestamp
      FROM documents
      WHERE id = $1
    `, [documentId]);

    if (documentResult.rows.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: 'Document not found',
          details: `No document found with id: ${documentId}`
        },
        { status: 404 }
      );
    }

    const doc = documentResult.rows[0];

    // Count images in markdown text
    const imageMatches = doc.full_text.match(/!\[\]\(images\//g);
    const imageCount = imageMatches ? imageMatches.length : 0;

    // Count sections (markdown headers)
    const sectionMatches = doc.full_text.match(/^#+\s/gm);
    const sectionCount = sectionMatches ? sectionMatches.length : 0;

    // Check if visual elements exist for this document
    const visualQuery = await pool.query(`
      SELECT COUNT(*) as count
      FROM visual_elements_real
      WHERE document_id = $1 OR document_id = $2
    `, [documentId, doc.pdf_name]);

    const hasVisualElements = visualQuery.rows[0].count > 0;

    const response: DocumentResponse = {
      id: doc.id,
      pdfName: doc.pdf_name,
      documentType: doc.document_type,
      documentArea: doc.document_area,
      charCount: parseInt(doc.char_count),
      wordCount: parseInt(doc.word_count),
      fullText: doc.full_text,
      extractionTimestamp: doc.extraction_timestamp,
      metadata: {
        imageCount,
        sectionCount,
        hasVisualElements
      }
    };

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: response,
      meta: {
        responseTimeMs: responseTime,
        source: 'documents_table',
        textLength: doc.full_text.length
      }
    });

  } catch (error) {
    console.error('Full document retrieval error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
