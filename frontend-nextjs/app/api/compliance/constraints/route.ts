import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { getDCPSection, extractLGA } from '@/lib/dcp-section-service';
import { determineFormerCouncilArea } from '@/lib/inner-west-mapping-v2';
import { getPrecinctForAddress, getPrecinctControls } from '@/lib/precinct-service';
import { getZoneAliases } from '@/lib/zone-translation';
import { normalizeDevType } from '@/lib/dev-type-loader';
import { getCommercialKeywords } from '@/lib/keyword-loader';
import { PropertySearchSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

interface ConstraintQuery {
  address: string;
  zone: string;
  lga?: string;
  developmentType?: string;
  propId?: number;
  planningApiClauses?: string[];  // Clause numbers extracted from Planning API layers
  heritageItemName?: string;  // Heritage item name for HCA→precinct mapping
  coordinates?: { lat: number; lon: number };  // WGS84 coordinates for spatial precinct matching
}

interface ProvisionResult {
  id: number;
  provision_text: string;
  provision_type: string;
  ref_number: string;
  section_header: string;
  document_id: string;
  zone: string;
  document_category?: string;
  development_type?: string;
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
  provisions?: Array<{
    id: number;
    ref_number: string;
    section_header: string;
    provision_text: string;
    document_id: string;
  }>;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: ConstraintQuery = await request.json();

    // Validate core address fields
    const validation = validateRequest(PropertySearchSchema, {
      address: body.address,
      lga: body.lga,
    });

    if (!validation.success) {
      return NextResponse.json({
        success: false,
        error: 'Invalid request data',
        details: formatValidationErrors(validation.details),
      }, { status: 400 });
    }

    if (!body.zone) {
      return NextResponse.json({
        success: false,
        error: 'Zone is required'
      }, { status: 400 });
    }

    const { address, lga } = validation.data;
    const { zone, developmentType, propId, planningApiClauses = [], heritageItemName, coordinates } = body;

    // Extract or default LGA
    const lgaName = lga || extractLGA(address || '');

    // For Inner West, determine the specific former council area
    let targetLGA = lgaName;
    let lgaSearchPattern = targetLGA;

    if (lgaName.toLowerCase().includes('inner west')) {
      if (address) {
        const formerCouncil = determineFormerCouncilArea(address, lgaName);
        if (formerCouncil) {
          targetLGA = formerCouncil; // Use "Marrickville", "Ashfield", or "Leichhardt"
          lgaSearchPattern = formerCouncil;
          console.log(`[Constraints API] Mapped Inner West address to former council: ${formerCouncil}`);
        } else {
          // Address provided but couldn't determine former council - search all three
          lgaSearchPattern = '.*(Marrickville|Ashfield|Leichhardt).*';
          console.log(`[Constraints API] Couldn't map address to former council, will search all three`);
        }
      } else {
        // No address provided - search all three former councils
        lgaSearchPattern = '.*(Marrickville|Ashfield|Leichhardt).*';
        console.log(`[Constraints API] No address provided, will search all Inner West former councils`);
      }
    }

    console.log(`[Constraints API] Query: lga=${targetLGA}, zone=${zone}, devType=${developmentType}, searchPattern=${lgaSearchPattern}`);

    // Get zone aliases (includes legacy equivalents: E1 → [E1, B1, B2])
    const zoneAliases = getZoneAliases(zone);
    console.log(`[Constraints API] Zone translation: ${zone} → [${zoneAliases.join(', ')}]`);

    // Get DCP section dynamically (works for ANY LGA)
    let dcpSectionInfo = null;
    if (developmentType) {
      dcpSectionInfo = await getDCPSection(targetLGA, developmentType);
      console.log(`[Constraints API] DCP Section:`, dcpSectionInfo);
    }

    // Precinct-based controls with optional feature flag
    // Feature flag allows safe gradual rollout (set ENABLE_PRECINCT_MATCHING=true to enable)
    const enablePrecinctMatching = process.env.ENABLE_PRECINCT_MATCHING === 'true';

    // IMPORTANT: Use original 'lga' for heritage mapping, not mapped 'targetLGA'
    // Heritage mapping uses "INNER WEST", but DCP queries use "Ashfield/Marrickville/Leichhardt"
    const precinct = enablePrecinctMatching && address
      ? await getPrecinctForAddress(address, lga ?? '', coordinates, heritageItemName)
      : null;

    let precinctControls: any[] = [];

    if (precinct) {
      console.log(`[Constraints API] ✅ Precinct matching enabled - matched precinct:`, precinct);

      // Identify the provisions by precinct + council, not by a concatenated
      // document id. The old argument was `${council}_DCP_2011_${id}_${name}`,
      // built in code and matching no stored document.
      const rawPrecinctControls = await getPrecinctControls(
        precinct.precinctId,
        precinct.lga,
        precinct.formerCouncil,
        ['height', 'setback', 'parking', 'fsr', 'open_space', 'heritage', 'vegetation']
      );

      console.log(`[Constraints API] Found ${rawPrecinctControls.length} raw precinct controls (before filtering)`);

      // CRITICAL: The transformControlsToConstraints function (lines 550-717) will automatically
      // filter out commercial provisions for residential development types using keyword matching.
      // This prevents the "7 storeys for dwelling house" issue without needing database changes.
      precinctControls = rawPrecinctControls; // Will be filtered by transformControlsToConstraints
    } else if (enablePrecinctMatching) {
      console.log(`[Constraints API] ⚠️ Precinct matching enabled but no precinct found for address`);
    } else {
      console.log(`[Constraints API] ℹ️ Precinct matching disabled (set ENABLE_PRECINCT_MATCHING=true to enable)`);
    }

    // Query 1: Get high-confidence extracted controls from development_controls
    // Use zone translation to find both current (E1) and legacy (B1, B2) provisions
    const zonePlaceholders = zoneAliases.map((_, i) => `$${i + 1}`).join(', ');
    const controlsQuery = `
      SELECT
        dc.control_type,
        dc.control_subtype,
        dc.value_numeric,
        dc.unit,
        dc.confidence_score,
        rp.id as provision_id,
        rp.provision_text,
        rp.ref_number,
        rp.section_header,
        rp.document_id,
        rp.zone,
        d.regulation_year,
        d.amendment_reference,
        d.amendment_date,
        d.version_status,
        d.last_verified_date,
        CURRENT_DATE - d.last_verified_date as days_since_verified,
        CASE
          WHEN CURRENT_DATE - d.last_verified_date <= 30 THEN 'current'
          WHEN CURRENT_DATE - d.last_verified_date <= 60 THEN 'caution'
          ELSE 'stale'
        END as staleness_level
      FROM development_controls dc
      JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id
      LEFT JOIN documents d ON rp.document_id = d.id
      WHERE rp.zone IN (${zonePlaceholders})
        AND dc.control_type IN ('height', 'setback', 'parking', 'fsr', 'open_space')
        AND dc.confidence_score::numeric > 0.75
        AND dc.value_numeric IS NOT NULL
        AND (
          $${zoneAliases.length + 1}::text IS NULL
          OR rp.development_type = $${zoneAliases.length + 1}::text
        )
        AND (
          rp.document_id ~* $${zoneAliases.length + 2}::text
        )
      ORDER BY
        dc.confidence_score::numeric DESC,
        CASE dc.control_type
          WHEN 'height' THEN 1
          WHEN 'fsr' THEN 2
          WHEN 'setback' THEN 3
          WHEN 'parking' THEN 4
          ELSE 5
        END
      LIMIT 15
    `;

    const controlsResult = await query(controlsQuery, [...zoneAliases, developmentType || null, lgaSearchPattern]);

    console.log(`[Constraints API] Found ${controlsResult.rows.length} extracted controls for zones [${zoneAliases.join(', ')}]`);

    // Query 2: Get curated setback rules from zone_setback_rules
    // REMOVED: All fallback queries that hide missing metadata
    // If data is missing, the API should fail loudly
    const setbackResult = { rows: [] };
    console.log(`[Constraints API] Skipping zone_setback_rules query (deprecated)`);

    // Data quality check: Log missing metadata
    const missingMetadataQuery = `
      SELECT
        COUNT(*) FILTER (WHERE zone IS NULL) as missing_zone,
        COUNT(*) FILTER (WHERE development_type IS NULL) as missing_dev_type,
        COUNT(*) as total_provisions
      FROM regulatory_provisions_canonical rp
      LEFT JOIN documents d ON rp.document_id = d.id
      WHERE (d.pdf_name ~* $1::text OR rp.document_id ~* $1::text)
        AND d.document_type = 'DCP'
        AND rp.provision_text ~ '[0-9]+\\.?[0-9]*\\s*(m|metre)'
        AND rp.provision_text ILIKE '%setback%'
    `;

    const metadataCheck = await query(missingMetadataQuery, [lgaSearchPattern]);
    const { missing_zone, missing_dev_type, total_provisions } = metadataCheck.rows[0] || {};

    if (missing_zone > 0 || missing_dev_type > 0) {
      console.error(`[Constraints API] ❌ DATA QUALITY ISSUE:`, {
        lga: lgaSearchPattern,
        missing_zone: parseInt(missing_zone) || 0,
        missing_dev_type: parseInt(missing_dev_type) || 0,
        total_provisions: parseInt(total_provisions) || 0,
        message: 'Provisions found but missing zone/development_type metadata'
      });
    }

    // Combine zone-specific controls, setbacks, AND precinct controls (NO FALLBACKS)
    const allControls = [
      ...controlsResult.rows,
      ...setbackResult.rows,
      ...precinctControls
    ];

    // Query 3: Get development permissions if developmentType provided
    let permissions: any[] = [];
    let permissionStatus: string | null = null;

    if (developmentType) {
      // Normalize UI development type to database/LEP terminology (loaded from config)
      const normalizedType = normalizeDevType(developmentType);
      console.log(`[Constraints API] Development type: ${developmentType} → normalized: ${normalizedType}`);

      // CORRECT LOGIC:
      // 1. Check base permissibility (permitted/prohibited/consent) from LEP
      // 2. IF permitted, check if exempt/complying pathway available from SEPP
      // 3. SEPP codes don't grant permission - they only streamline approval IF already permitted

      // Step 1: Check base LEP permissibility using normalized type
      const basePermissionQuery = `
        SELECT
          zone,
          development_type,
          permission_status,
          conditions,
          source_provision_id,
          source_type,
          confidence_score
        FROM development_permissions
        WHERE zone IN (${zonePlaceholders})
        AND development_type = $${zoneAliases.length + 1}
        AND source_type NOT ILIKE '%exempt%'
        ORDER BY
          CASE source_type
            WHEN 'nsw_standard' THEN 1
            WHEN 'existing' THEN 2
            ELSE 3
          END,
          confidence_score DESC
        LIMIT 1
      `;

      const baseResult = await query(basePermissionQuery, [...zoneAliases, normalizedType]);

      if (baseResult.rows.length > 0) {
        const basePermission = baseResult.rows[0].permission_status;

        // If prohibited or consent required, don't check SEPP
        if (basePermission === 'prohibited' || basePermission === 'consent') {
          permissions = baseResult.rows;
          permissionStatus = basePermission;
          console.log(`[Constraints API] Base permission for ${developmentType} (normalized: ${normalizedType}) in ${zone}: ${permissionStatus} (not eligible for exempt/complying)`);
        } else if (basePermission === 'permitted') {
          // Step 2: Check if exempt/complying pathway available
          const seppQuery = `
            SELECT
              zone,
              development_type,
              permission_status,
              conditions,
              source_provision_id,
              source_type,
              confidence_score
            FROM development_permissions
            WHERE zone IN (${zonePlaceholders})
            AND (development_type = $${zoneAliases.length + 1} OR development_type = 'general')
            AND source_type ILIKE '%exempt%'
            ORDER BY
              CASE WHEN development_type = $${zoneAliases.length + 1} THEN 1 ELSE 2 END,
              confidence_score DESC
            LIMIT 1
          `;

          const seppResult = await query(seppQuery, [...zoneAliases, developmentType]);

          if (seppResult.rows.length > 0) {
            permissions = seppResult.rows;
            permissionStatus = seppResult.rows[0].permission_status;
            console.log(`[Constraints API] ${developmentType} in ${zone} is permitted AND qualifies for: ${permissionStatus}`);
          } else {
            // Permitted but no exempt/complying pathway
            permissions = baseResult.rows;
            permissionStatus = 'consent_required';
            console.log(`[Constraints API] ${developmentType} in ${zone} is permitted but requires DA (no exempt/complying pathway)`);
          }
        } else {
          // Unknown status
          permissions = baseResult.rows;
          permissionStatus = baseResult.rows[0]?.permission_status ?? 'unknown';
          console.log(`[Constraints API] Permission for ${developmentType} in ${zone}: ${permissionStatus}`);
        }
      } else {
        // No base permission found - LOG ERROR instead of silent fallback
        console.error(`[Constraints API] ❌ MISSING PERMISSION DATA:`, {
          zone,
          development_type: developmentType,
          normalized_type: normalizedType,
          message: 'No LEP permission found in database'
        });

        permissionStatus = 'unknown';
        permissions = [{
          zone,
          development_type: developmentType,
          permission_status: 'unknown',
          conditions: 'ERROR: Permission data not found in database',
          source_type: 'missing_data',
          confidence_score: '0.0'
        }];
      }
    }

    // Query 4: Collect LEP clause references from displayed controls
    // Extract unique clause references from provisions we're showing
    const displayedClauses = new Set<string>();

    // Add clauses extracted from Planning API (generic per LGA)
    if (planningApiClauses && planningApiClauses.length > 0) {
      planningApiClauses.forEach(clause => {
        displayedClauses.add(clause);

        // Add parent clause if this is a sub-clause (e.g., "4.3" → add "4")
        const parentMatch = clause.match(/^([0-9]+[A-Z]?)/);
        if (parentMatch) {
          displayedClauses.add(parentMatch[1]);
        }
      });
      console.log('[Constraints API] Added Planning API clauses:', planningApiClauses);
    }

    // Extract clauses from database controls
    for (const control of controlsResult.rows) {
      const refNum = control.ref_number;
      const docId = control.document_id || '';

      // Only process LEP clauses (numeric patterns like "4.3", "3B", "5A")
      if (docId.toLowerCase().includes('local_environmental_plan') && refNum) {
        const match = refNum.match(/^([0-9]+[A-Z]?(?:\.[0-9]+)?)/);
        if (match) {
          const clause = match[1];
          displayedClauses.add(clause);

          // Add parent clause if this is a sub-clause (e.g., "4.3" → add "4")
          const parentMatch = clause.match(/^([0-9]+)/);
          if (parentMatch) {
            displayedClauses.add(parentMatch[1]);
          }
        }
      }
    }

    console.log(`[Constraints API] Displayed LEP clauses:`, Array.from(displayedClauses));

    // Query 5: Get SEPP overrides ONLY for displayed clauses (relevancy filter)
    const clauseArray = Array.from(displayedClauses);
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
      LEFT JOIN regulatory_provisions_canonical rp ON s.sepp_provision_id::text = rp.id::text
      WHERE s.confidence_score::numeric > 0.5
        AND s.lep_clause_reference = ANY($1::text[])
      ORDER BY s.override_type DESC, s.lep_clause_reference
      LIMIT 20
    `;

    const seppResult = await query(seppQuery, [clauseArray]);

    console.log(`[Constraints API] Found ${seppResult.rows.length} SEPP overrides`);

    // Transform controls into constraints with development type filtering
    const constraints = transformControlsToConstraints(
      allControls,
      seppResult.rows,
      developmentType || '',
      zone
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
        sepp_overrides: seppResult.rows,
        permission_status: permissionStatus  // Add permission status to response
      },
      // The precinct MUST reach the client. It was resolved here, logged, and
      // then dropped from the response — so ProvisionsByTocStructure read
      // `constraints?.precinctId`, got undefined, and never sent precinct_id to
      // /api/provisions/for-property. The precinct layer therefore never
      // filtered, in every council, however good the boundary polygons were.
      precinct: precinct
        ? {
            precinctId: precinct.precinctId,
            precinctNumber: precinct.precinctNumber,
            precinctName: precinct.precinctName,
            lga: precinct.lga,
            formerCouncil: precinct.formerCouncil ?? null,
            matchMethod: precinct.matchMethod ?? null,
            confidenceScore: precinct.confidenceScore ?? null,
          }
        : null,
      // Flat alias: the assessment page reads selectedProperty.constraints?.precinctId.
      precinctId: precinct?.precinctId ?? null,
      metadata: {
        lga: lgaName,
        zone,
        developmentType,
        dcpSection: dcpSectionInfo,
        permissionStatus: permissionStatus,  // Include in metadata too
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
 * Transform extracted controls into UI-ready constraints
 * Filters out irrelevant controls based on development type and zone
 */
function transformControlsToConstraints(
  controls: any[],
  seppOverrides: any[],
  developmentType: string,
  zone: string
): ComplianceConstraint[] {
  const constraints: ComplianceConstraint[] = [];

  // Development type filtering context
  const isDwellingHouse = developmentType === 'dwelling_house';
  const isResidentialZone = ['R1', 'R2', 'R3', 'R4', 'R5'].some(z => zone.toUpperCase().startsWith(z));
  const isMixedUse = ['B4', 'B8'].some(z => zone.toUpperCase().startsWith(z)) ||
                     developmentType.includes('shop_top') ||
                     developmentType.includes('mixed');

  // Commercial keywords to filter for residential development (loaded from config)
  const commercialKeywords = getCommercialKeywords();

  let filteredCount = 0;

  // Transform each control
  for (const control of controls) {
    // Map control types to UI types
    let uiType: ComplianceConstraint['type'];
    const controlType = control.control_type?.toLowerCase() || '';
    const provisionText = (control.provision_text || '').toLowerCase();
    const documentId = (control.document_id || '').toLowerCase();
    const refNumber = (control.ref_number || '').toLowerCase();

    // Development type relevance filtering (DCP controls only)
    const isDCP = documentId.includes('dcp') || documentId.includes('development_control');

    if (isDCP && (isDwellingHouse || isResidentialZone) && !isMixedUse) {
      // Filter commercial controls for residential development
      const hasCommercialKeyword = commercialKeywords.some(kw =>
        provisionText.includes(kw) || refNumber.includes(kw)
      );

      if (hasCommercialKeyword) {
        filteredCount++;
        console.log('[DCP Filter] Filtered commercial control for residential:', {
          ref_number: control.ref_number,
          matched_keyword: commercialKeywords.find(kw =>
            provisionText.includes(kw) || refNumber.includes(kw)
          ),
          development_type: developmentType,
          zone: zone
        });
        continue; // Skip this control
      }
    }

    // Structural controls (always categorize correctly)
    switch (controlType) {
      case 'height':
        uiType = 'height';
        break;
      case 'fsr':
        uiType = 'fsr';
        break;
      case 'setback':
        uiType = 'setback';
        break;
      case 'parking':
      case 'open_space':
        uiType = 'special';
        break;
      default:
        // Smart categorization for unknown types
        // Check document type first
        if (documentId.includes('sepp_65') || documentId.includes('sepp_no_65')) {
          uiType = 'special'; // SEPP 65 is design quality, not environmental
        }
        // Check for true environmental keywords
        else if (
          provisionText.includes('flood') ||
          provisionText.includes('bushfire') ||
          provisionText.includes('contamination') ||
          provisionText.includes('acid sulfate') ||
          provisionText.includes('heritage') && provisionText.includes('conservation') ||
          provisionText.includes('biodiversity') ||
          provisionText.includes('tree preservation') ||
          provisionText.includes('water quality') ||
          provisionText.includes('stormwater')
        ) {
          uiType = 'environmental';
        }
        // Default to special (not environmental) for unknown types
        else {
          uiType = 'special';
          console.log('[Control Categorization] Unknown type defaulted to special:', {
            control_type: control.control_type,
            ref_number: control.ref_number,
            document_id: control.document_id?.substring(0, 50)
          });
        }
    }

    // Parse numeric value (handle 0 explicitly since it's falsy but valid)
    const numericValue = control.value_numeric !== null && control.value_numeric !== undefined
      ? parseFloat(control.value_numeric)
      : null;

    // Extract readable document name
    const docName = extractDocumentName(control.document_id || '');

    // Determine authority level
    const authority = inferAuthorityLevel(control.document_id || '');

    // Create provisions array for ConstraintCard compatibility with version metadata
    const provisions = control.provision_text ? [{
      id: control.provision_id || 0,
      ref_number: control.ref_number || 'N/A',
      section_header: control.section_header || '',
      provision_text: control.provision_text,
      document_id: control.document_id || '',
      version: control.regulation_year ? {
        regulation_year: control.regulation_year,
        amendment_reference: control.amendment_reference,
        amendment_date: control.amendment_date,
        version_status: control.version_status,
        last_verified_date: control.last_verified_date,
        days_since_verified: parseInt(control.days_since_verified) || 0,
        staleness_level: control.staleness_level
      } : undefined
    }] : [];

    constraints.push({
      type: uiType,
      value: numericValue !== null ? numericValue : 'See provision',
      unit: control.unit || undefined,
      source: {
        clause: control.ref_number || 'N/A',
        document: docName,
        authority_level: authority as 'LEP' | 'DCP' | 'SEPP'
      },
      provision_id: control.provision_id || 0,
      full_text: control.provision_text || '',
      provisions: provisions  // Add provisions array for card display
    });
  }

  // Add SEPP overrides as special constraints
  for (const sepp of seppOverrides) {
    const overrideText = sepp.extracted_text || sepp.sepp_text || 'SEPP override applies';
    const overrideType = sepp.override_type || 'modifies';

    // Create provisions array with full text
    const provisions = sepp.sepp_text ? [{
      id: sepp.sepp_provision_id || 0,
      ref_number: sepp.lep_clause_reference || 'N/A',
      section_header: `SEPP ${overrideType} LEP clause ${sepp.lep_clause_reference || 'N/A'}`,
      provision_text: sepp.sepp_text,
      document_id: `sepp_override_${sepp.sepp_provision_id || 'unknown'}`
    }] : [];

    constraints.push({
      type: 'special',
      value: `SEPP ${overrideType} LEP clause ${sepp.lep_clause_reference || 'N/A'}`,
      source: {
        clause: `Override: ${sepp.lep_clause_reference || 'N/A'}`,
        document: `SEPP Override (Provision ${sepp.sepp_provision_id || 'Unknown'})`,
        authority_level: 'SEPP'
      },
      provision_id: sepp.sepp_provision_id || 0,
      full_text: overrideText,
      provisions: provisions  // Include full provision with complete text
    });
  }

  // Log filtering summary
  if (filteredCount > 0) {
    console.log(`[DCP Filter] Filtered ${filteredCount} irrelevant DCP controls for ${developmentType} in ${zone}`);
  }

  return constraints;
}

/**
 * Extract readable document name from document ID
 */
function extractDocumentName(documentId: string): string {
  if (!documentId) return 'Unknown Document';

  // Remove underscores and long suffixes
  const parts = documentId.split('___');
  const mainPart = parts[0] || documentId;

  return mainPart.replace(/_/g, ' ');
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