/**
 * Extract Section/Figure from Document API
 *
 * On-demand extraction using LGA-specific configurations
 * Features: Smart caching, config-driven patterns, batch extraction
 */

import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';
import { getConfigFromDocumentId } from '@/lib/lga-configs';
import { extractReferences } from '@/lib/document-extraction/figure-parser';
import { extractSection, extractMultipleSections } from '@/lib/document-extraction/section-extractor';
import { getCachedSection, cacheSection, getCacheStats } from '@/lib/document-extraction/section-cache';
import type { ExtractedSection } from '@/lib/lga-configs/types';


export const dynamic = 'force-dynamic';
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
});

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const startTime = Date.now();
  const documentId = params.id;
  const searchParams = request.nextUrl.searchParams;

  // Get query parameters
  const sectionParam = searchParams.get('section');
  const figureParam = searchParams.get('figure');
  const provisionId = searchParams.get('provision_id');
  const autoDetect = searchParams.get('auto') === 'true';
  const includeStats = searchParams.get('stats') === 'true';

  try {
    // Get LGA config for this document
    const config = getConfigFromDocumentId(documentId);

    if (!config) {
      return NextResponse.json({
        success: false,
        error: 'LGA configuration not found',
        details: `No configuration available for document: ${documentId}`
      }, { status: 404 });
    }

    // Get full document
    const docResult = await pool.query(`
      SELECT id, full_text
      FROM documents
      WHERE id = $1
    `, [documentId]);

    if (docResult.rows.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Document not found' },
        { status: 404 }
      );
    }

    const fullText = docResult.rows[0].full_text;
    const sections: ExtractedSection[] = [];
    let cacheHits = 0;
    let cacheMisses = 0;

    // Auto-detect from provision text
    if (autoDetect && provisionId) {
      const provResult = await pool.query(`
        SELECT provision_text
        FROM regulatory_provisions_canonical
        WHERE id = $1
      `, [parseInt(provisionId)]);

      if (provResult.rows.length > 0) {
        const provisionText = provResult.rows[0].provision_text;

        // Extract references using LGA-specific patterns
        const refs = extractReferences(provisionText, config as any);

        for (const ref of refs) {
          // Check cache first
          const cached = getCachedSection(documentId, ref.reference);

          if (cached) {
            sections.push(cached);
            cacheHits++;
          } else {
            // Extract on-demand
            const section = extractSection(fullText, ref.reference, config as any, ref.type === 'appendix' ? undefined : ref.type);
            if (section) {
              sections.push(section);
              cacheSection(documentId, section);
              cacheMisses++;
            }
          }
        }
      }
    }

    // Manual section/figure extraction
    const targetRef = sectionParam || figureParam;
    if (targetRef && sections.length === 0) {
      // Check cache
      const cached = getCachedSection(documentId, targetRef);

      if (cached) {
        sections.push(cached);
        cacheHits++;
      } else {
        // Extract on-demand
        const section = extractSection(fullText, targetRef, config as any);
        if (section) {
          sections.push(section);
          cacheSection(documentId, section);
          cacheMisses++;
        }
      }
    }

    if (sections.length === 0) {
      return NextResponse.json({
        success: false,
        error: 'Section not found',
        details: `Could not find section ${targetRef || 'auto-detected'} in document`,
        debug: {
          documentId,
          lgaConfig: (config as any).lga,
          searchedFor: targetRef || 'auto-detect from provision'
        }
      }, { status: 404 });
    }

    const responseTime = Date.now() - startTime;

    const response: any = {
      success: true,
      data: {
        documentId,
        lgaConfig: (config as any).lga,
        sections,
        totalSections: sections.length
      },
      meta: {
        responseTimeMs: responseTime,
        method: autoDetect ? 'auto_detect' : 'manual',
        cacheHits,
        cacheMisses,
        cacheHitRate: cacheHits + cacheMisses > 0
          ? `${Math.round((cacheHits / (cacheHits + cacheMisses)) * 100)}%`
          : 'N/A'
      }
    };

    // Include cache stats if requested
    if (includeStats) {
      response.meta.cacheStats = getCacheStats();
    }

    return NextResponse.json(response);

  } catch (error) {
    console.error('Section extraction error:', error);
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
