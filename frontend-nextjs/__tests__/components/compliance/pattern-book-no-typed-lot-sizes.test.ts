/**
 * The Pattern Book card must not print typed lot sizes. Before 2026-10-26 it said
 * "studio apartments (300m² min) to manor houses (1500m² min)" — numbers that would not follow
 * an amendment (code-quality review, served rules finding 6). The real minimums are rendered per
 * design type from eligibility.numericCheck.details (sepp_structured_requirements).
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, '..', '..', '..', 'components', 'compliance', 'PatternBookEligibilityCard.tsx'), 'utf8');

it('has no typed "NNNm² min" figure in its screen text', () => {
  expect(src).not.toMatch(/\d+\s*m²\s*min/);
});
