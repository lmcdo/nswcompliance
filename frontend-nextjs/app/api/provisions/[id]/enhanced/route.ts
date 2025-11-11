/**
 * Enhanced Provision API with Linked Data
 * Combines provision with cross-references, applicability, and control codes
 * Single query for comprehensive provision context
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

interface EnhancedProvision {
  id: number;
  refNumber: string;
  provisionText: string;
  zone: string | null;
  documentId: string;
  sectionHeader: string;
  provisionType: string;
  provisionCategory: string;
  displayPriority: number;
  isMandatory: boolean;

  // Applicability
  applicability: {
    explicitZone: string | null;
    appliesToZone: string | null;
    appliesToAllZones: boolean;
    appliesToLGA: string | null;
    appliesStateWide: boolean;
    applicabilitySource: string;
    confidenceScore: number;
  };

  // Cross-references
  crossReferences: {
    total: number;
    resolved: number;
    references: Array<{
      referenceType: string;
      referenceNumber: string;
      referenceText: string;
      targetProvisionId: number | null;
      targetReference: string | null;
      resolutionStatus: string;
      isMandatory: boolean;
    }>;
  };

  // Control codes
  controlCodes: {
    total: number;
    codeGroup: string | null;
    controlType: string | null;
    codes: string[];
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const startTime = Date.now();
  const provisionId = parseInt(params.id);

  if (isNaN(provisionId)) {
    return NextResponse.json(
      { error: 'Invalid provision ID' },
      { status: 400 }
    );
  }

  try {
    // Main provision query
    const provisionResult = await pool.query(`
      SELECT
        rp.id,
        rp.ref_number,
        rp.provision_text,
        rp.zone,
        rp.document_id,
        rp.section_header,
        rp.provision_type,
        rp.provision_category,
        rp.display_priority,
        rp.is_mandatory,
        pa.applies_to_zone,
        pa.applies_to_all_zones,
        pa.applies_to_lga,
        pa.applies_state_wide,
        pa.applicability_source,
        pa.confidence_score
      FROM regulatory_provisions_canonical rp
      LEFT JOIN provision_applicability pa ON rp.id = pa.provision_id
      WHERE rp.id = $1
    `, [provisionId]);

    if (provisionResult.rows.length === 0) {
      return NextResponse.json(
        { error: 'Provision not found' },
        { status: 404 }
      );
    }

    const provision = provisionResult.rows[0];

    // Cross-references query
    const crossRefResult = await pool.query(`
      SELECT
        xr.reference_type,
        xr.reference_number,
        xr.reference_text,
        xr.target_provision_id,
        xr.resolution_status,
        xr.is_mandatory,
        rp_target.ref_number as target_reference
      FROM cross_reference_index xr
      LEFT JOIN regulatory_provisions_canonical rp_target
        ON xr.target_provision_id = rp_target.id
      WHERE xr.source_provision_id = $1
      ORDER BY xr.is_mandatory DESC, xr.resolution_confidence DESC
    `, [provisionId]);

    // Control codes query
    const controlCodesResult = await pool.query(`
      SELECT
        cc.code,
        cc.code_group,
        cc.control_type,
        cc.sequence_number
      FROM control_codes cc
      WHERE cc.provision_id = $1
      ORDER BY cc.sequence_number
    `, [provisionId]);

    // Build enhanced response
    const enhanced: EnhancedProvision = {
      id: provision.id,
      refNumber: provision.ref_number || 'N/A',
      provisionText: provision.provision_text || '',
      zone: provision.zone,
      documentId: provision.document_id,
      sectionHeader: provision.section_header || '',
      provisionType: provision.provision_type || '',
      provisionCategory: provision.provision_category || 'general',
      displayPriority: provision.display_priority || 5,
      isMandatory: provision.is_mandatory !== false,

      applicability: {
        explicitZone: provision.zone,
        appliesToZone: provision.applies_to_zone,
        appliesToAllZones: provision.applies_to_all_zones || false,
        appliesToLGA: provision.applies_to_lga,
        appliesStateWide: provision.applies_state_wide || false,
        applicabilitySource: provision.applicability_source || 'explicit_zone',
        confidenceScore: provision.confidence_score || 1.0
      },

      crossReferences: {
        total: crossRefResult.rows.length,
        resolved: crossRefResult.rows.filter(r => r.resolution_status === 'resolved').length,
        references: crossRefResult.rows.map(row => ({
          referenceType: row.reference_type,
          referenceNumber: row.reference_number,
          referenceText: row.reference_text,
          targetProvisionId: row.target_provision_id,
          targetReference: row.target_reference,
          resolutionStatus: row.resolution_status,
          isMandatory: row.is_mandatory
        }))
      },

      controlCodes: {
        total: controlCodesResult.rows.length,
        codeGroup: controlCodesResult.rows[0]?.code_group || null,
        controlType: controlCodesResult.rows[0]?.control_type || null,
        codes: controlCodesResult.rows.map(row => row.code)
      }
    };

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: enhanced,
      meta: {
        responseTimeMs: responseTime,
        source: 'enhanced_provision',
        linkedDataLoaded: true
      }
    });

  } catch (error) {
    console.error('Enhanced provision query error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
