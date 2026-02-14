/**
 * Step 2: Use LLM to auto-tag gold standard with high scrutiny
 * User will review and correct before using as ground truth
 */

import Anthropic from '@anthropic-ai/sdk';
import fs from 'fs';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Available heritage elements
const VALID_ELEMENTS = [
  'roof', 'verandah', 'window', 'door', 'fence', 'garden', 'facade',
  'chimney', 'infill', 'car_parking', 'demolition', 'interior',
  'materials', 'setback', 'scale'
];

// Strict tagging prompt
const SYSTEM_PROMPT = `You are a heritage planning expert. Tag heritage provisions with the specific physical elements they regulate.

STRICT RULES:
1. ONLY tag if the provision explicitly mentions or clearly regulates a specific physical element
2. General heritage significance statements → [] (empty array)
3. Conservation objectives without specific elements → [] (empty array)
4. Multiple elements mentioned → tag all of them
5. Return ONLY elements from this list: ${VALID_ELEMENTS.join(', ')}

EXAMPLES:

Text: "Roof materials must match original terracotta tiles"
Answer: ["roof", "materials"]
Reason: Explicitly mentions roof and materials

Text: "New fencing must be timber picket, 1.2m high, set back 1m from street"
Answer: ["fence", "materials", "setback"]
Reason: Mentions fence, materials (timber), and setback

Text: "The HCA is historically significant for its Victorian houses and streetscapes"
Answer: []
Reason: General significance statement, no specific element regulation

Text: "Alterations to alleviate noise must not detract from street presentation"
Answer: ["materials", "facade"]
Reason: Noise = materials/insulation, street presentation = facade

Text: "This section provides heritage controls"
Answer: []
Reason: General intro, no specific elements

IMPORTANT:
- Be conservative - when in doubt, don't tag
- Descriptive/historical statements = []
- Only actionable controls about physical elements get tags`;

async function tagProvision(provisionText) {
  const message = await anthropic.messages.create({
    model: 'claude-haiku-4-5-20251001',  // Current Haiku 4.5
    max_tokens: 500,
    temperature: 0,  // Deterministic
    system: SYSTEM_PROMPT,
    messages: [{
      role: 'user',
      content: `Tag this provision:\n\n"${provisionText}"\n\nReturn ONLY valid JSON: {"elements": [...], "reasoning": "why"}`
    }]
  });

  const responseText = message.content[0].text;

  // Extract JSON from response (handles markdown code blocks)
  const jsonMatch = responseText.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`No JSON in response: ${responseText}`);
  }

  const result = JSON.parse(jsonMatch[0]);

  // Validate elements
  const validElements = result.elements.filter(e => VALID_ELEMENTS.includes(e));

  return {
    elements: validElements,
    reasoning: result.reasoning || '',
    raw_response: responseText
  };
}

async function main() {
  console.log('🤖 Auto-tagging gold standard provisions with LLM...\n');

  // Load gold standard
  const goldStandard = JSON.parse(fs.readFileSync('./gold-standard-heritage-elements.json', 'utf-8'));

  const tagged = [];

  for (let i = 0; i < goldStandard.length; i++) {
    const provision = goldStandard[i];
    console.log(`Processing ${i + 1}/${goldStandard.length}: ID ${provision.id}...`);

    try {
      const result = await tagProvision(provision.text);

      tagged.push({
        ...provision,
        elements: result.elements,
        llm_reasoning: result.reasoning,
        llm_raw_response: result.raw_response,
        reviewed_by: 'llm_auto_tagged',
        reviewed_at: new Date().toISOString()
      });

      console.log(`  → ${result.elements.length > 0 ? JSON.stringify(result.elements) : '[]'}`);
      console.log(`  Reason: ${result.reasoning}\n`);

      // Rate limit: 1 request per second
      await new Promise(resolve => setTimeout(resolve, 1000));

    } catch (error) {
      console.error(`  ❌ Error: ${error.message}`);
      tagged.push({
        ...provision,
        elements: [],
        llm_error: error.message
      });
    }
  }

  // Save tagged results
  fs.writeFileSync('./gold-standard-llm-tagged.json', JSON.stringify(tagged, null, 2));

  // Create human-readable review file
  const reviewOutput = tagged.map((p, i) => {
    return `
=== PROVISION ${i + 1} (ID: ${p.id}) ===
Topic: ${p.v2_topic}
Length: ${p.text_length} chars

Text:
${p.text}

LLM Tags: ${JSON.stringify(p.elements)}
Reasoning: ${p.llm_reasoning}

✏️  REVIEW: Correct? (Y/N) _____
   If N, correct tags: [ ]
   Notes: ____________

---`;
  }).join('\n');

  fs.writeFileSync('./gold-standard-REVIEW.txt', reviewOutput);

  console.log('\n✅ Done!');
  console.log(`\n📄 Files created:`);
  console.log(`   - gold-standard-llm-tagged.json (machine-readable)`);
  console.log(`   - gold-standard-REVIEW.txt (for human review)`);
  console.log(`\n🔍 NEXT STEPS:`);
  console.log(`1. Open gold-standard-REVIEW.txt`);
  console.log(`2. Review each provision's tags`);
  console.log(`3. Mark Y (correct) or N (needs correction)`);
  console.log(`4. For any N, write correct tags`);
  console.log(`5. Run 03-apply-corrections.mjs to finalize gold standard`);

  // Summary stats
  const elementsDistribution = tagged.reduce((acc, p) => {
    const count = p.elements.length;
    acc[count] = (acc[count] || 0) + 1;
    return acc;
  }, {});

  console.log(`\n📊 Summary:`);
  console.log(`   Empty []: ${elementsDistribution[0] || 0} provisions`);
  console.log(`   1 element: ${elementsDistribution[1] || 0} provisions`);
  console.log(`   2+ elements: ${Object.entries(elementsDistribution).filter(([k]) => k > 1).reduce((sum, [, v]) => sum + v, 0)} provisions`);
}

main().catch(console.error);
