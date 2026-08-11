const Anthropic = require('@anthropic-ai/sdk');
const { Pool } = require('pg');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env.local') });

// ============================================================
// CONFIGURATION
// ============================================================

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const DATABASE_URL = process.env.DATABASE_URL;
const MODEL = 'claude-sonnet-4-5-20250929';

const DELAY_MS = 1200; // Rate limiting: 1.2s between API calls
const TEST_LIMIT = 10;  // TEST MODE: Only process 10 provisions

// ============================================================
// DATABASE CONNECTION
// ============================================================

// Note: Using Pool directly for standalone script (not Next.js runtime)
const pool = new Pool({ connectionString: DATABASE_URL });

// ============================================================
// TOOL SCHEMA DEFINITION
// ============================================================

const SEPP_EXTRACTION_TOOL = {
  name: 'extract_sepp_requirements',
  description: 'Extracts structured requirements from SEPP provision text for pathway feasibility engine. Identifies exclusion triggers, numeric standards, dimensional thresholds, override rules, and procedural requirements.',
  input_schema: {
    type: 'object',
    properties: {
      requirements: {
        type: 'array',
        description: 'Array of structured requirements extracted from the provision',
        items: {
          type: 'object',
          properties: {
            // Core classification
            requirement_category: {
              type: 'string',
              enum: ['exclusion', 'numeric_standard', 'dimensional', 'override', 'procedure'],
              description: 'Type of requirement'
            },
            applies_to: {
              type: 'string',
              enum: ['CDC', 'TAD', 'DA', 'Pattern_Book', 'all'],
              description: 'Which approval pathway this affects'
            },

            // Exclusion logic
            is_exclusion_trigger: {
              type: 'boolean',
              description: 'TRUE if this provision excludes properties from fast-track pathways'
            },
            exclusion_type: {
              type: 'string',
              enum: [
                'heritage', 'flood_planning_area', 'bushfire_prone', 'acid_sulfate_soils',
                'threatened_species', 'coastal_erosion', 'environmentally_sensitive',
                'protected_area', 'foreshore_area', 'aircraft_noise',
                'reserved_public_purpose', 'unsewered'
              ],
              description: 'Type of exclusion if is_exclusion_trigger is true'
            },
            exclusion_scope: {
              type: 'string',
              enum: ['entire_lot', 'partial_constraint', 'setback_only'],
              description: 'Does exclusion affect entire lot or just part'
            },

            // Numeric standards
            metric_name: {
              type: 'string',
              description: 'Name of the metric (e.g., deep_soil_percent, tree_canopy_percent, setback_front_m)'
            },
            metric_value: {
              type: 'number',
              description: 'Numeric value of the metric'
            },
            metric_unit: {
              type: 'string',
              enum: ['percent', 'm', 'm2', 'mm', 'spaces_per_dwelling'],
              description: 'Unit of measurement'
            },
            metric_operator: {
              type: 'string',
              enum: ['min', 'max', 'equals', 'range'],
              description: 'Comparison operator (min = at least, max = not exceed)'
            },
            metric_value_max: {
              type: 'number',
              description: 'For range operators, the maximum value'
            },

            // Dimensional thresholds
            dimension_type: {
              type: 'string',
              enum: ['lot_width', 'lot_depth', 'lot_area', 'frontage'],
              description: 'Type of dimension for pattern book matching'
            },
            dimension_min: {
              type: 'number',
              description: 'Minimum dimension required'
            },
            dimension_max: {
              type: 'number',
              description: 'Maximum dimension (if range)'
            },

            // Context and conditions
            context: {
              type: 'object',
              description: 'JSONB conditions like zones, lot sizes, heritage flags, etc.',
              additionalProperties: true
            },

            // Override logic
            is_override: {
              type: 'boolean',
              description: 'Does this SEPP provision override local DCP/LEP rules'
            },
            overrides_layer: {
              type: 'string',
              enum: ['DCP', 'LEP', 'council_policy'],
              description: 'Which layer does it override'
            },
            override_condition: {
              type: 'string',
              description: 'Condition under which override applies (e.g., if_TOD_within_400m)'
            },

            // Pattern book integration
            pattern_book_ref: {
              type: 'string',
              description: 'Reference to NSW Housing Pattern Book design (e.g., PB-2025-Pattern-04)'
            },
            template_constraint: {
              type: 'object',
              description: 'Template constraints (min_width, min_depth, envelope_m2, deep_soil_m2)',
              additionalProperties: true
            },

            // Audit trail
            source_clause: {
              type: 'string',
              description: 'Full clause reference for professional citation (e.g., Codes SEPP Clause 1.19(2)(a))'
            },

            // Quality metadata
            extraction_confidence: {
              type: 'number',
              description: 'Confidence score 0.0-1.0 for this extraction',
              minimum: 0,
              maximum: 1
            },
            requires_professional_review: {
              type: 'boolean',
              description: 'Flag for human review if complex/ambiguous'
            },
            ambiguity_notes: {
              type: 'string',
              description: 'Notes on ambiguities or edge cases'
            }
          },
          required: ['requirement_category', 'applies_to', 'source_clause', 'extraction_confidence']
        }
      }
    },
    required: ['requirements']
  }
};

// ============================================================
// ANTHROPIC CLIENT
// ============================================================

const client = new Anthropic({ apiKey: ANTHROPIC_API_KEY });

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function extractStructuredRequirements(provision) {
  const prompt = `You are extracting structured requirements from a SEPP (State Environmental Planning Policy) provision for an Australian planning compliance system.

**SEPP Document:** ${provision.document_name || 'Unknown SEPP'}
**Part:** ${provision.v2_part || 'Unknown'}
**Topic:** ${provision.v2_topic || 'Unknown'}
**PDF Page:** ${provision.pdf_page || 'Unknown'}

**Provision Text:**
${provision.provision_text}

Extract ALL structured requirements from this provision. Focus on:

1. **Exclusion Triggers** - Does this provision exclude sites from CDC/Pattern Book pathways?
   - Heritage items, HCAs, flood planning areas, bushfire prone land, acid sulfate soils, threatened species, etc.
   - Specify scope: entire_lot vs partial_constraint vs setback_only

2. **Numeric Standards** - Quantitative requirements like:
   - Deep soil percentage, tree canopy coverage
   - Setbacks (front/side/rear, primary/secondary road)
   - Height limits, FSR limits, area limits
   - Parking ratios (spaces per dwelling)

3. **Dimensional Thresholds** - Lot size requirements for pattern matching:
   - Minimum lot width, depth, area, frontage

4. **Override Rules** - Does this SEPP provision supersede DCP/LEP?
   - E.g., TOD parking reductions, Housing SEPP non-discretionary standards

5. **Procedural Requirements** - Process requirements without numeric/spatial constraints

**Context Conditions:**
If a requirement only applies under certain conditions (e.g., specific zones, lot sizes, heritage flags), capture these in the "context" field as JSON.

Example: {"zones": ["R2", "R3"], "lot_size_min_m2": 300, "heritage_excluded": true}

**Source Citation:**
Provide the full clause reference in "source_clause" field (e.g., "Codes SEPP Clause 1.19(2)(a)").

**Confidence & Ambiguity:**
- Set extraction_confidence to 0.0-1.0 based on clarity
- If provision references external tables, cross-references, or requires professional judgment, set requires_professional_review = true and explain in ambiguity_notes

Use the extract_sepp_requirements tool to return your findings.`;

  try {
    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 4096,
      tools: [SEPP_EXTRACTION_TOOL],
      messages: [{
        role: 'user',
        content: prompt
      }]
    });

    // Find tool use in response
    const toolUse = response.content.find(block => block.type === 'tool_use');
    if (!toolUse || toolUse.name !== 'extract_sepp_requirements') {
      throw new Error('No tool use found in response');
    }

    return {
      success: true,
      requirements: toolUse.input.requirements || [],
      stop_reason: response.stop_reason,
      usage: response.usage
    };

  } catch (error) {
    return {
      success: false,
      error: error.message,
      requirements: []
    };
  }
}

async function saveRequirements(provisionId, requirements, pdfPage, provisionText) {
  if (requirements.length === 0) {
    return 0;
  }

  const insertQuery = `
    INSERT INTO sepp_structured_requirements (
      provision_id,
      requirement_category,
      applies_to,
      is_exclusion_trigger,
      exclusion_type,
      exclusion_scope,
      metric_name,
      metric_value,
      metric_unit,
      metric_operator,
      metric_value_max,
      dimension_type,
      dimension_min,
      dimension_max,
      context,
      is_override,
      overrides_layer,
      override_condition,
      pattern_book_ref,
      template_constraint,
      source_clause,
      source_pdf_page,
      source_provision_text,
      extraction_confidence,
      requires_professional_review,
      ambiguity_notes
    ) VALUES (
      $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26
    )
  `;

  let savedCount = 0;

  for (const req of requirements) {
    try {
      await pool.query(insertQuery, [
        provisionId,
        req.requirement_category,
        req.applies_to,
        req.is_exclusion_trigger || false,
        req.exclusion_type || null,
        req.exclusion_scope || null,
        req.metric_name || null,
        req.metric_value || null,
        req.metric_unit || null,
        req.metric_operator || null,
        req.metric_value_max || null,
        req.dimension_type || null,
        req.dimension_min || null,
        req.dimension_max || null,
        req.context ? JSON.stringify(req.context) : null,
        req.is_override || false,
        req.overrides_layer || null,
        req.override_condition || null,
        req.pattern_book_ref || null,
        req.template_constraint ? JSON.stringify(req.template_constraint) : null,
        req.source_clause,
        pdfPage,
        provisionText,
        req.extraction_confidence,
        req.requires_professional_review || false,
        req.ambiguity_notes || null
      ]);
      savedCount++;
    } catch (error) {
      console.error(`   ❌ Failed to save requirement: ${error.message}`);
    }
  }

  return savedCount;
}

// ============================================================
// MAIN EXTRACTION WORKFLOW
// ============================================================

async function main() {
  console.log('🧪 SEPP Structured Extraction TEST (10 provisions)');
  console.log('====================================================\n');
  console.log(`Model: ${MODEL}`);
  console.log(`Rate Limit: ${DELAY_MS}ms delay between API calls`);
  console.log(`Test Limit: ${TEST_LIMIT} provisions\n`);

  // Get 10 SEPP provisions for testing
  console.log('📊 Fetching test provisions from database...');

  const provisionsQuery = `
    SELECT
      rp.id,
      rp.provision_text,
      rp.pdf_page,
      rp.v2_part,
      rp.v2_topic,
      rp.v2_is_actionable,
      d.pdf_name as document_name
    FROM regulatory_provisions rp
    JOIN documents d ON rp.document_id = d.id
    WHERE d.document_type = 'SEPP'
      AND rp.v2_is_actionable = true
      AND LENGTH(rp.provision_text) > 50
    ORDER BY d.pdf_name, rp.pdf_page, rp.id
    LIMIT ${TEST_LIMIT}
  `;

  const result = await pool.query(provisionsQuery);
  const provisions = result.rows;

  console.log(`✅ Found ${provisions.length} test provisions\n`);

  if (provisions.length === 0) {
    console.log('⚠️  No provisions to process. Exiting.');
    await pool.end();
    return;
  }

  // Processing statistics
  let processedCount = 0;
  let successCount = 0;
  let failedCount = 0;
  let totalRequirementsExtracted = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;

  const startTime = Date.now();

  // Process provisions one by one
  for (let i = 0; i < provisions.length; i++) {
    const provision = provisions[i];
    const provisionNum = i + 1;

    console.log(`\n[${provisionNum}/${provisions.length}] Processing provision #${provision.id}`);
    console.log(`   Document: ${provision.document_name}`);
    console.log(`   Part: ${provision.v2_part || 'Unknown'} | Topic: ${provision.v2_topic || 'Unknown'} | Page: ${provision.pdf_page || 'Unknown'}`);
    console.log(`   Text: ${provision.provision_text.substring(0, 100)}...`);

    // Extract requirements using Sonnet
    const extractionResult = await extractStructuredRequirements(provision);

    if (extractionResult.success) {
      const requirementsCount = extractionResult.requirements.length;
      console.log(`   ✅ Extracted ${requirementsCount} requirement(s)`);

      // Show extracted requirements summary
      if (requirementsCount > 0) {
        extractionResult.requirements.forEach((req, idx) => {
          console.log(`      ${idx + 1}. ${req.requirement_category} - ${req.applies_to} (confidence: ${req.extraction_confidence})`);
          if (req.is_exclusion_trigger) {
            console.log(`         🚫 Exclusion: ${req.exclusion_type} (${req.exclusion_scope})`);
          }
          if (req.metric_name) {
            console.log(`         📏 Metric: ${req.metric_name} ${req.metric_operator} ${req.metric_value}${req.metric_unit || ''}`);
          }
          if (req.dimension_type) {
            console.log(`         📐 Dimension: ${req.dimension_type} min ${req.dimension_min}`);
          }
        });
      }

      // Save to database
      const savedCount = await saveRequirements(
        provision.id,
        extractionResult.requirements,
        provision.pdf_page,
        provision.provision_text
      );

      console.log(`   💾 Saved ${savedCount} requirement(s) to database`);

      successCount++;
      totalRequirementsExtracted += savedCount;

      // Track actual token usage
      if (extractionResult.usage) {
        totalInputTokens += extractionResult.usage.input_tokens || 0;
        totalOutputTokens += extractionResult.usage.output_tokens || 0;
      }

    } else {
      console.log(`   ❌ Extraction failed: ${extractionResult.error}`);
      failedCount++;
    }

    processedCount++;

    // Rate limiting delay
    if (i < provisions.length - 1) {
      await sleep(DELAY_MS);
    }
  }

  // Final summary
  const totalTime = (Date.now() - startTime) / 1000;
  const actualCost = (totalInputTokens / 1000000) * 3 + (totalOutputTokens / 1000000) * 15;

  console.log('\n====================================================');
  console.log('📊 TEST EXTRACTION COMPLETE');
  console.log('====================================================');
  console.log(`Total provisions processed: ${processedCount}`);
  console.log(`Successful extractions: ${successCount}`);
  console.log(`Failed extractions: ${failedCount}`);
  console.log(`Total requirements extracted: ${totalRequirementsExtracted}`);
  console.log(`Average requirements per provision: ${(totalRequirementsExtracted/processedCount).toFixed(1)}`);
  console.log(`\nToken Usage:`);
  console.log(`  Input tokens: ${totalInputTokens.toLocaleString()}`);
  console.log(`  Output tokens: ${totalOutputTokens.toLocaleString()}`);
  console.log(`  Actual cost: $${actualCost.toFixed(4)}`);
  console.log(`\nPerformance:`);
  console.log(`  Total time: ${totalTime.toFixed(1)}s`);
  console.log(`  Average: ${(totalTime/processedCount).toFixed(1)}s per provision`);
  console.log(`\n📈 Projected for full extraction (8,600 provisions):`);
  console.log(`  Estimated cost: $${(actualCost / processedCount * 8600).toFixed(2)}`);
  console.log(`  Estimated time: ${((totalTime / processedCount * 8600) / 3600).toFixed(1)} hours\n`);

  await pool.end();
  process.exit(failedCount > 0 ? 1 : 0);
}

// ============================================================
// RUN
// ============================================================

if (require.main === module) {
  main().catch(error => {
    console.error('❌ Fatal error:', error);
    pool.end();
    process.exit(1);
  });
}

module.exports = { extractStructuredRequirements, saveRequirements };
