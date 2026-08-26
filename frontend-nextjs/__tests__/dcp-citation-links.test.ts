/**
 * DCP citation links and the "not yet processed" contradiction.
 *
 * Two defects reported from the live Canterbury-Bankstown page on 2026-08-26:
 *
 * 1. The page listed "20 controls extracted / Source: Canterbury-Bankstown DCP
 *    2023" and, directly beneath, a form offering to notify the user when that
 *    council's DCP went live. Both statements about the same council, on one
 *    screen. The caller rendered the controls card AND the interest form
 *    unconditionally, though its own comment said "otherwise".
 *
 * 2. Exactly ONE of the twenty citations was a link. Measured cause: the
 *    registry query selected only r2_public_pdf_url and ignored council_url.
 *    Across served controls the chapter key matches the registry 88.6% of the
 *    time, but only 39.9% have an R2 copy while 49.2% have a council URL.
 *    Parking has an R2 copy; the two setback chapters do not.
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.join(__dirname, '..');
const read = (p: string) => fs.readFileSync(path.join(ROOT, p), 'utf8');

describe('the DCP tab does not contradict itself', () => {
  const parent = read('components/compliance/ProvisionsByTocStructure.tsx');
  const child = read('components/compliance/DcpStructuredControls.tsx');

  it('the interest form is passed AS the fallback, not rendered beside the controls', () => {
    // Anchor on the render guard's own comment. 'tocStructure.length === 0'
    // appears earlier in an unrelated memo and slicing from there scoped the
    // assertion to the wrong function entirely - it passed for the wrong reason
    // until the fix made it fail.
    const start = parent.indexOf('No DCP provision TEXT for this council');
    expect(start).toBeGreaterThan(-1);
    const scope = parent.slice(start, parent.indexOf('const handleSelectPart', start));
    expect(scope).toContain('fallback=');
    // A sibling <DCPInterestForm ...> outside the fallback prop is the defect.
    const controlsIdx = scope.indexOf('<DcpStructuredControls');
    const formIdx = scope.indexOf('<DCPInterestForm');
    expect(controlsIdx).toBeGreaterThanOrEqual(0);
    expect(formIdx).toBeGreaterThan(controlsIdx);   // nested inside, not before
    expect(scope.indexOf('fallback=')).toBeLessThan(formIdx);
  });

  it('the controls card renders the fallback when a council has none', () => {
    expect(child).toContain('fallback');
    expect(child).toMatch(/if \(!data\?\.has_controls\) return <>\{fallback\}<\/>;/);
  });
});

describe('citation links', () => {
  const registryRoute = read('app/api/provisions/for-property/route.ts');
  const controlsRoute = read('app/api/dcp/structured-controls/route.ts');

  it('the registry query selects council_url, not only the R2 copy', () => {
    expect(registryRoute).toContain('council_url');
    expect(registryRoute).toMatch(/r2_public_pdf_url,\s*council_url/);
  });

  it('falls back through council URL then council page URL', () => {
    // Cumulative coverage measured 2026-08-26 across served controls:
    //   r2 alone 39.9% -> +council_url 49.2% -> +council_page_url 78.7%.
    // The last step is the largest single gain and was the one nobody used.
    expect(registryRoute).toContain(
      'row.r2_public_pdf_url || row.council_url || row.council_page_url',
    );
    expect(registryRoute).toContain('council_page_url,');   // and it is SELECTed
  });

  it('the python path uses the same chain, not just the R2 copy', () => {
    // The identical defect existed twice. Fixing only the TS route would have
    // left the conveyancing report still showing dead refs.
    const py = fs.readFileSync(
      path.join(ROOT, '..', 'scripts', 'conveyancing_db.py'), 'utf8',
    );
    expect(py).toContain('COALESCE(r2_public_pdf_url, council_url, council_page_url)');
    // The old form selected the R2 column bare; assert that exact shape is gone.
    expect(py).not.toContain('SELECT chapter_key, r2_public_pdf_url');
  });

  it('only anchors a page onto our OWN paginated copy', () => {
    // pdf_page was measured against our R2 copy. Appending it to the council's
    // own PDF would point confidently at the wrong page - worse than no anchor.
    expect(controlsRoute).toContain('IS_OWN_COPY');
    expect(controlsRoute).toMatch(/row\.pdf_page && IS_OWN_COPY\.test\(pdfUrl\)/);
  });

  it('the own-copy pattern actually matches an R2 url and rejects a council one', () => {
    const m = controlsRoute.match(/const IS_OWN_COPY = (\/.+\/);/);
    expect(m).not.toBeNull();
    // eslint-disable-next-line no-eval
    const re: RegExp = eval(m![1]);
    expect(re.test('https://pub-abc123.r2.dev/dcp/chapter-3-2-parking.pdf')).toBe(true);
    expect(re.test('https://verify.plotdetect.com.au/pdf-pages/x.pdf')).toBe(true);
    expect(re.test('https://www.cbcity.nsw.gov.au/dcp/chapter5.pdf')).toBe(false);
  });
});
