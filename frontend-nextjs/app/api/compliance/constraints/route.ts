import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection
const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'nsw_planning',
  user: 'postgres',
  password: 'postgres'
});

interface ConstraintQuery {
  address: string;
  zone: string;
  developmentType?: string;
  propId?: number;
}

interface ProvisionResult {
  id: number;
  provision_text: string;
  provision_type: string;
  ref_number: string;
  section_header: string;
  document_id: string;
  zone: string;
}

interface ComplianceConstraint {
  type: 'height' | 'fsr' | 'setback' | 'heritage' | 'environmental' | 'special';
  value: string | number;
  unit?: string;
  source: {
    clause: string;
    document: string;
    authority_level: 'LEP' | 'DCP' | 'SEPP';
  };
  provision_id: number;
  full_text: string;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: ConstraintQuery = await request.json();
    const { address, zone, developmentType, propId } = body;

    if (!zone) {
      return NextResponse.json({
        success: false,
        error: 'Zone is required'
      }, { status: 400 });
    }

    console.log(`[Constraints API] Query: zone=${zone}, devType=${developmentType}`);

    // Query 1: Get zone-specific provisions (without document join for now)
    const provisionsQuery = `
      SELECT
        rp.id,
        rp.provision_text,
        rp.provision_type,
        rp.ref_number,
        rp.section_header,
        rp.zone,
        rp.document_id
      FROM regulatory_provisions rp
      WHERE rp.zone = $1
      AND rp.provision_type IS NOT NULL
      AND rp.provision_type != ''
      ORDER BY rp.ref_number
      LIMIT 50
    `;

    const provisionsResult = await pool.query(provisionsQuery, [zone]);

    console.log(`[Constraints API] Found ${provisionsResult.rows.length} provisions for zone ${zone}`);

    // Query 2: Get development permissions if developmentType provided
    let permissions: any[] = [];
    if (developmentType) {
      const permissionsQuery = `
        SELECT
          zone,
          development_type,
          permission_status,
          lep_name,
          source_provision_id
        FROM development_permissions
        WHERE zone = $1
        AND development_type = $2
        LIMIT 10
      `;

      const permissionsResult = await pool.query(permissionsQuery, [zone, developmentType]);
      permissions = permissionsResult.rows;

      console.log(`[Constraints API] Found ${permissions.length} permissions for ${developmentType} in ${zone}`);
    }

    // Query 3: Get SEPP overrides that might affect this zone
    const seppQuery = `
      SELECT
        s.id,
        s.sepp_provision_id,
        s.lep_clause_reference,
        s.override_type,
        s.extracted_text,
        s.confidence_score,
        rp.provision_text as sepp_text
      FROM sepp_lep_overrides s
      LEFT JOIN regulatory_provisions rp ON s.sepp_provision_id::text = rp.id::text
      WHERE s.confidence_score::numeric > 0.5
      ORDER BY s.override_type DESC
      LIMIT 10
    `;

    const seppResult = await pool.query(seppQuery);

    console.log(`[Constraints API] Found ${seppResult.rows.length} SEPP overrides`);

    // Transform provisions into constraints
    const constraints = transformProvisionsToConstraints(
      provisionsResult.rows,
      permissions,
      seppResult.rows
    );

    const processingTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        building_envelope: constraints.filter(c =>
          ['height', 'fsr', 'setback'].includes(c.type)
        ),
        environmental: constraints.filter(c =>
          ['heritage', 'environmental'].includes(c.type)
        ),
        special_provisions: constraints.filter(c =>
          c.type === 'special'
        ),
        development_permissions: permissions,
        sepp_overrides: seppResult.rows
      },
      metadata: {
        zone,
        developmentType,
        totalConstraints: constraints.length,
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[Constraints API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}

/**
 * Transform database provisions into UI-ready constraints
 */
function transformProvisionsToConstraints(
  provisions: ProvisionResult[],
  permissions: any[],
  seppOverrides: any[]
): ComplianceConstraint[] {
  const constraints: ComplianceConstraint[] = [];

  // Provision type to constraint type mapping
  const typeMap: Record<string, ComplianceConstraint['type']> = {
    'height_limit': 'height',
    'height_of_buildings': 'height',
    'building_height': 'height',
    'maximum_height': 'height',
    'floor_space_ratio': 'fsr',
    'fsr': 'fsr',
    'density': 'fsr',
    'setback': 'setback',
    'building_setback': 'setback',
    'heritage': 'heritage',
    'heritage_conservation': 'heritage',
    'flood': 'environmental',
    'bushfire': 'environmental',
    'basix': 'special',
    'car_parking': 'special'
  };

  for (const provision of provisions) {
    const constraintType = typeMap[provision.provision_type?.toLowerCase()] || 'special';

    // Extract numeric value if present
    const value = extractConstraintValue(provision.provision_text, constraintType);

    constraints.push({
      type: constraintType,
      value: value || provision.provision_text.substring(0, 100),
      unit: getUnitForType(constraintType, provision.provision_text),
      source: {
        clause: provision.ref_number || 'N/A',
        document: provision.document_id || 'Unknown Document',
        authority_level: inferAuthorityLevel(provision.document_id)
      },
      provision_id: provision.id,
      full_text: provision.provision_text
    });
  }

  // Add SEPP overrides as special constraints
  for (const sepp of seppOverrides) {
    const overrideText = sepp.extracted_text || sepp.sepp_text || 'SEPP override applies';
    const overrideType = sepp.override_type || 'modifies';

    constraints.push({
      type: 'special',
      value: `SEPP ${overrideType} LEP clause ${sepp.lep_clause_reference || 'N/A'}`,
      source: {
        clause: `Override: ${sepp.lep_clause_reference || 'N/A'}`,
        document: `SEPP Override (Provision ${sepp.sepp_provision_id || 'Unknown'})`,
        authority_level: 'SEPP'
      },
      provision_id: sepp.sepp_provision_id || 0,
      full_text: overrideText.substring(0, 500) // Limit to 500 chars
    });
  }

  return constraints;
}

/**
 * Extract numeric constraint values from provision text
 */
function extractConstraintValue(text: string, type: string): string | number | null {
  if (!text) return null;

  switch (type) {
    case 'height':
      // Match patterns like "9.5m", "9.5 metres", "9.5 meters"
      const heightMatch = text.match(/(\d+\.?\d*)\s*(m|metres?|meters?)/i);
      return heightMatch ? parseFloat(heightMatch[1]) : null;

    case 'fsr':
      // Match patterns like "0.6:1", "0.6", "1.5:1"
      const fsrMatch = text.match(/(\d+\.?\d*)\s*:?\s*1/);
      return fsrMatch ? parseFloat(fsrMatch[1]) : null;

    case 'setback':
      // Match patterns like "6m", "1.5m", "3 metres"
      const setbackMatches = text.match(/(\d+\.?\d*)\s*(m|metres?|meters?)/gi);
      if (setbackMatches && setbackMatches.length > 0) {
        return setbackMatches.join(', ');
      }
      return null;

    default:
      return null;
  }
}

/**
 * Get appropriate unit for constraint type
 */
function getUnitForType(type: string, text: string): string | undefined {
  switch (type) {
    case 'height':
    case 'setback':
      return 'm';
    case 'fsr':
      return ':1';
    default:
      return undefined;
  }
}

/**
 * Infer authority level from document ID
 */
function inferAuthorityLevel(documentId: string): 'LEP' | 'DCP' | 'SEPP' {
  const docIdLower = documentId?.toLowerCase() || '';

  if (docIdLower.includes('sepp') || docIdLower.includes('state_environmental')) {
    return 'SEPP';
  } else if (docIdLower.includes('lep') || docIdLower.includes('local_environmental')) {
    return 'LEP';
  } else if (docIdLower.includes('dcp') || docIdLower.includes('development_control')) {
    return 'DCP';
  }

  // Default to DCP if unknown
  return 'DCP';
}