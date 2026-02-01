/**
 * Procedural Guidance API
 *
 * Query the procedural workflow Q&A pairs and application checklists.
 * Supports:
 * - Natural language question matching
 * - Category filtering (pathway, checklist, timeline, professional)
 * - Pathway filtering (CDC, DA)
 * - Checklist retrieval
 *
 * GET /api/procedural?question=should%20I%20use%20cdc
 * GET /api/procedural?category=pathway
 * GET /api/procedural?pathway=CDC
 * GET /api/procedural?type=checklist&pathway=CDC
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/database/pool-manager';


export const dynamic = 'force-dynamic';
interface GuidanceResult {
  id: number;
  question_pattern: string;
  question_category: string;
  answer_summary: string;
  answer_detailed: string;
  answer_conditions: string[] | null;
  source_document: string;
  source_url: string | null;
  source_section: string | null;
  follow_up_questions: string[] | null;
  applies_to_cdc: boolean;
  applies_to_da: boolean;
  applies_to_dev_types: string[] | null;
}

interface ChecklistItem {
  id: number;
  checklist_name: string;
  pathway: string;
  development_type: string | null;
  item_order: number;
  item_name: string;
  item_description: string | null;
  item_required: boolean;
  item_conditions: string | null;
  source_document: string;
  source_url: string | null;
}

interface ProceduralResponse {
  success: boolean;
  type: 'guidance' | 'checklist' | 'mixed';
  guidance?: {
    count: number;
    items: GuidanceResult[];
  };
  checklist?: {
    count: number;
    items: ChecklistItem[];
  };
  meta: {
    query?: string;
    filters_applied: Record<string, string>;
    response_time_ms: number;
  };
}

export async function GET(request: NextRequest): Promise<NextResponse<ProceduralResponse | { error: string; details?: string }>> {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;

    // Parse query parameters
    const questionText = searchParams.get('question');
    const category = searchParams.get('category');
    const pathway = searchParams.get('pathway')?.toUpperCase();
    const type = searchParams.get('type') || 'guidance'; // guidance, checklist, or both
    const developmentType = searchParams.get('development_type');
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 100);

    const filtersApplied: Record<string, string> = {};
    if (questionText) filtersApplied.question = questionText;
    if (category) filtersApplied.category = category;
    if (pathway) filtersApplied.pathway = pathway;
    if (developmentType) filtersApplied.development_type = developmentType;

    let guidance: GuidanceResult[] = [];
    let checklist: ChecklistItem[] = [];

    // Query guidance (Q&A pairs)
    if (type === 'guidance' || type === 'both') {
      const guidanceConditions: string[] = [];
      const guidanceParams: (string | number | boolean)[] = [];
      let paramIndex = 1;

      // Full-text search on question
      if (questionText) {
        guidanceConditions.push(`(
          question_normalized ILIKE $${paramIndex++}
          OR to_tsvector('english', question_pattern || ' ' || answer_summary) @@ plainto_tsquery('english', $${paramIndex++})
        )`);
        guidanceParams.push(`%${questionText.toLowerCase().trim()}%`);
        guidanceParams.push(questionText);
      }

      // Category filter
      if (category) {
        guidanceConditions.push(`question_category = $${paramIndex++}`);
        guidanceParams.push(category.toLowerCase());
      }

      // Pathway filter
      if (pathway === 'CDC') {
        guidanceConditions.push(`applies_to_cdc = true`);
      } else if (pathway === 'DA') {
        guidanceConditions.push(`applies_to_da = true`);
      }

      // Development type filter
      if (developmentType) {
        guidanceConditions.push(`$${paramIndex++} = ANY(applies_to_dev_types)`);
        guidanceParams.push(developmentType.toLowerCase());
      }

      const guidanceWhereClause = guidanceConditions.length > 0
        ? `WHERE ${guidanceConditions.join(' AND ')}`
        : '';

      const guidanceSql = `
        SELECT
          id,
          question_pattern,
          question_category,
          answer_summary,
          answer_detailed,
          answer_conditions,
          source_document,
          source_url,
          source_section,
          follow_up_questions,
          applies_to_cdc,
          applies_to_da,
          applies_to_dev_types
        FROM procedural_guidance
        ${guidanceWhereClause}
        ORDER BY
          ${questionText ? `
            CASE
              WHEN question_normalized ILIKE $1 THEN 1
              WHEN question_normalized ILIKE '%' || $1 || '%' THEN 2
              ELSE 3
            END,
          ` : ''}
          question_category,
          id
        LIMIT $${paramIndex}
      `;

      guidanceParams.push(limit);

      const guidanceResult = await query(guidanceSql, guidanceParams);
      guidance = guidanceResult.rows as GuidanceResult[];
    }

    // Query checklists
    if (type === 'checklist' || type === 'both') {
      const checklistConditions: string[] = [];
      const checklistParams: (string | number)[] = [];
      let paramIndex = 1;

      // Pathway filter
      if (pathway) {
        checklistConditions.push(`pathway = $${paramIndex++}`);
        checklistParams.push(pathway);
      }

      // Development type filter
      // "residential" or empty means general checklist (development_type IS NULL)
      // specific types match their development_type value
      if (developmentType) {
        if (developmentType.toLowerCase() === 'residential' || developmentType.toLowerCase() === 'general') {
          checklistConditions.push(`development_type IS NULL`);
        } else {
          checklistConditions.push(`development_type ILIKE $${paramIndex++}`);
          checklistParams.push(`%${developmentType}%`);
        }
      }

      const checklistWhereClause = checklistConditions.length > 0
        ? `WHERE ${checklistConditions.join(' AND ')}`
        : '';

      const checklistSql = `
        SELECT
          id,
          checklist_name,
          pathway,
          development_type,
          item_order,
          item_name,
          item_description,
          item_required,
          item_conditions,
          source_document,
          source_url
        FROM application_checklists
        ${checklistWhereClause}
        ORDER BY checklist_name, item_order
        LIMIT $${paramIndex}
      `;

      checklistParams.push(limit * 3); // Checklists can have many items

      const checklistResult = await query(checklistSql, checklistParams);
      checklist = checklistResult.rows as ChecklistItem[];
    }

    const responseTime = Date.now() - startTime;

    console.log(`[Procedural API] Found ${guidance.length} Q&A, ${checklist.length} checklist items in ${responseTime}ms`);

    // Build response
    const response: ProceduralResponse = {
      success: true,
      type: type === 'both' ? 'mixed' : type as 'guidance' | 'checklist',
      meta: {
        query: questionText || undefined,
        filters_applied: filtersApplied,
        response_time_ms: responseTime
      }
    };

    if (type === 'guidance' || type === 'both') {
      response.guidance = {
        count: guidance.length,
        items: guidance
      };
    }

    if (type === 'checklist' || type === 'both') {
      response.checklist = {
        count: checklist.length,
        items: checklist
      };
    }

    return NextResponse.json(response);

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('[Procedural API] Error:', error);

    return NextResponse.json(
      {
        error: 'Failed to query procedural guidance',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
