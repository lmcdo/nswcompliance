/**
 * Step 3: Enrich ALL Marrickville heritage provisions with dual-pass validation
 *
 * - Uses enhanced heritage vocabulary mapping
 * - Dual-pass: runs same provision twice, flags if results differ
 * - Low confidence (<0.9) flagged for human review
 * - Audit trail for all changes
 */

import Anthropic from '@anthropic-ai/sdk';
import fs from 'fs';
import dotenv from 'dotenv';
import pg from 'pg';

dotenv.config({ path: '.env.local' });

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Physical elements only (strict)
const VALID_ELEMENTS = [
  'roof', 'verandah', 'window', 'door', 'fence', 'garden', 'facade',
  'chimney', 'infill', 'car_parking', 'demolition', 'interior',
  'materials', 'setback', 'scale'
];

// Enhanced system prompt with heritage vocabulary
const SYSTEM_PROMPT = `You are a heritage planning expert. Tag heritage provisions with PHYSICAL ELEMENTS they regulate.

STRICT RULES:
1. ONLY tag PHYSICAL elements explicitly mentioned or clearly regulated
2. General significance/character statements → [] (empty)
3. Design principles (rhythm, articulation, character) → NOT TAGGED
4. Return ONLY from this list: ${VALID_ELEMENTS.join(', ')}

HERITAGE VOCABULARY MAPPING (domain terms → physical elements):

ROOF elements:
- eaves, soffits, gutters, parapet, ridge, hip, valley, gable, dormer, skylight, solar panel, roof plane, roof line, roof form, roof pitch → "roof"
- finial, corbelling on roofline → "roof"

FACADE elements:
- elevation, frontage, street presentation, shopfront → "facade"
- corbelling, pilaster, cornice, architrave, pediment, parapet (wall) → "facade"
- balcony, awning, canopy (attached to building) → "facade"
- ornamentation, decorative features on building face → "facade"

WINDOW elements:
- glazing, sash, mullion, sill, lintel, opening (when referring to windows) → "window"
- shopfront glazing → both "window" AND "facade"

DOOR elements:
- entry, doorway, threshold, portal → "door"

FENCE elements:
- paling, picket, balustrade (as railing), gate, boundary wall → "fence"

GARDEN elements:
- landscaping, planting, trees (in garden context), front garden → "garden"

MATERIALS elements:
- brick, masonry, timber, render, cladding, paint, stain, stone, terracotta, slate, face brick, weatherboard → "materials"
- Any specification of building material → "materials"

CHIMNEY elements:
- chimney, flue, stack → "chimney"

SETBACK elements:
- setback, distance from street, building line, alignment → "setback"

SCALE elements:
- height, bulk, storey, massing (physical size) → "scale"
- BUT: "rhythm" (spacing pattern) → NOT TAGGED (design principle)

CAR_PARKING elements:
- garage, carport, parking, driveway → "car_parking"

DEMOLITION elements:
- demolition, removal, demolish → "demolition"

INFILL elements:
- infill development, new building, new construction → "infill"

INTERIOR elements:
- interior spaces, internal layout, room configuration → "interior"

EXAMPLES:

Text: "Roof materials must match original terracotta tiles"
Answer: ["roof", "materials"]
Reason: Explicitly regulates roof + specifies materials (terracotta)

Text: "Eaves and soffits must be retained in original form"
Answer: ["roof"]
Reason: Eaves/soffits are roof elements

Text: "Front elevation must maintain rhythm of openings"
Answer: ["facade", "window"]
Reason: Front elevation = facade, openings = windows. "Rhythm" is design principle (not tagged)

Text: "Timber paling fences set back 1m from street"
Answer: ["fence", "materials", "setback"]
Reason: Fence + material (timber) + setback specified

Text: "The HCA is significant for Victorian architecture and streetscapes"
Answer: []
Reason: General significance statement, no specific element regulation

Text: "Shopfronts with traditional glazing and pilasters"
Answer: ["facade", "window", "materials"]
Reason: Shopfronts = facade, glazing = window, pilasters = facade detail, traditional = materials specification

Text: "Alterations to alleviate noise must not harm street presentation"
Answer: ["materials", "facade"]
Reason: Noise alleviation = materials (insulation/glazing), street presentation = facade

CRITICAL:
- Be conservative - when unsure, don't tag
- Descriptive/historical text → []
- Multiple elements mentioned → tag ALL of them
- Design principles (rhythm, character, significance) → NOT TAGGED

Return ONLY valid JSON: {"elements": [...], "confidence": 0.0-1.0, "reasoning": "brief explanation"}`;

async function tagProvision(provisionText, attempt = 1) {
  const message = await anthropic.messages.create({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 600,
    temperature: 0,
    system: SYSTEM_PROMPT,
    messages: [{
      role: 'user',
      content: `Tag this provision (attempt ${attempt}/2):\n\n"${provisionText}"`
    }]
  });

  const responseText = message.content[0].text;
  const jsonMatch = responseText.match(/\{[\s\S]*\}/);

  if (!jsonMatch) {
    throw new Error(`No JSON in response: ${responseText}`);
  }

  const result = JSON.parse(jsonMatch[0]);
  const validElements = result.elements.filter(e => VALID_ELEMENTS.includes(e));

  return {
    elements: validElements,
    confidence: result.confidence || 0,
    reasoning: result.reasoning || '',
    raw_response: responseText
  };
}

async function enrichAllProvisions() {
  console.log('🔍 Fetching Marrickville heritage provisions...\n');

  const result = await pool.query(`
    SELECT
      id,
      provision_text,
      v2_topic,
      v2_heritage_type,
      v2_heritage_element
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
      AND v2_is_actionable = true
      AND v2_heritage_type = 'control'
    ORDER BY id
  `);

  console.log(`Found ${result.rows.length} provisions to enrich\n`);

  const enriched = [];
  const flaggedForReview = [];
  let passCount = 0;
  let flagCount = 0;

  for (let i = 0; i < result.rows.length; i++) {
    const provision = result.rows[i];
    console.log(`\nProcessing ${i + 1}/${result.rows.length}: ID ${provision.id}`);

    try {
      // Dual-pass validation
      const pass1 = await tagProvision(provision.provision_text, 1);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Rate limit

      const pass2 = await tagProvision(provision.provision_text, 2);
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Compare passes
      const pass1Str = JSON.stringify(pass1.elements.sort());
      const pass2Str = JSON.stringify(pass2.elements.sort());
      const matched = pass1Str === pass2Str;
      const avgConfidence = (pass1.confidence + pass2.confidence) / 2;

      // Flag for review if:
      // - Passes don't match
      // - Average confidence < 0.9
      const needsReview = !matched || avgConfidence < 0.9;

      const finalElements = matched ? pass1.elements : [];

      console.log(`  Pass 1: ${JSON.stringify(pass1.elements)} (conf: ${pass1.confidence})`);
      console.log(`  Pass 2: ${JSON.stringify(pass2.elements)} (conf: ${pass2.confidence})`);
      console.log(`  Match: ${matched ? '✅' : '❌'}, Avg confidence: ${avgConfidence.toFixed(2)}`);
      console.log(`  ${needsReview ? '⚠️  FLAGGED for review' : '✅ AUTO-ACCEPT'}`);

      const record = {
        provision_id: provision.id,
        provision_text: provision.provision_text,
        v2_topic: provision.v2_topic,
        old_elements: provision.v2_heritage_element,
        new_elements: finalElements,
        pass1_elements: pass1.elements,
        pass2_elements: pass2.elements,
        pass1_confidence: pass1.confidence,
        pass2_confidence: pass2.confidence,
        avg_confidence: avgConfidence,
        matched: matched,
        needs_review: needsReview,
        pass1_reasoning: pass1.reasoning,
        pass2_reasoning: pass2.reasoning,
        timestamp: new Date().toISOString()
      };

      enriched.push(record);

      if (needsReview) {
        flaggedForReview.push(record);
        flagCount++;
      } else {
        passCount++;
      }

    } catch (error) {
      console.error(`  ❌ Error: ${error.message}`);
      enriched.push({
        provision_id: provision.id,
        provision_text: provision.provision_text,
        error: error.message,
        needs_review: true
      });
      flagCount++;
    }
  }

  // Save results
  fs.writeFileSync('./enrichment-results-all.json', JSON.stringify(enriched, null, 2));
  fs.writeFileSync('./enrichment-FLAGGED-review.json', JSON.stringify(flaggedForReview, null, 2));

  // Create human-readable review file for flagged items
  const reviewOutput = flaggedForReview.map((r, i) => `
=== FLAGGED ${i + 1}/${flaggedForReview.length} (ID: ${r.provision_id}) ===
Topic: ${r.v2_topic}
Reason: ${!r.matched ? 'Passes differ' : `Low confidence (${r.avg_confidence.toFixed(2)})`}

Text:
${r.provision_text.substring(0, 300)}...

Pass 1: ${JSON.stringify(r.pass1_elements)} (conf: ${r.pass1_confidence})
Reasoning: ${r.pass1_reasoning}

Pass 2: ${JSON.stringify(r.pass2_elements)} (conf: ${r.pass2_confidence})
Reasoning: ${r.pass2_reasoning}

✏️  CORRECT TAGS: [ ]
---`).join('\n');

  fs.writeFileSync('./enrichment-FLAGGED-review.txt', reviewOutput);

  console.log('\n\n✅ COMPLETE!\n');
  console.log(`📊 Summary:`);
  console.log(`   Total provisions: ${result.rows.length}`);
  console.log(`   Auto-accepted: ${passCount} (${(passCount/result.rows.length*100).toFixed(1)}%)`);
  console.log(`   Flagged for review: ${flagCount} (${(flagCount/result.rows.length*100).toFixed(1)}%)`);
  console.log(`\n📄 Files created:`);
  console.log(`   - enrichment-results-all.json (all provisions)`);
  console.log(`   - enrichment-FLAGGED-review.json (needs review)`);
  console.log(`   - enrichment-FLAGGED-review.txt (human-readable)`);
  console.log(`\n🔍 NEXT: Review flagged provisions in enrichment-FLAGGED-review.txt`);

  await pool.end();
}

enrichAllProvisions().catch(console.error);
