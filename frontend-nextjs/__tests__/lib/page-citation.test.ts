import { PAGE_NOT_LOCATED, pageAnchor, pageHref, pageLabel } from '@/lib/page-citation';
import { formatCitation } from '@/lib/pdf/formatProvisions';

const URL = 'https://pub.r2.dev/dcp/ashfield/v1/part-c.pdf';
const DCP = { source_council: 'ashfield' };

describe("a DCP rule's page link opens only a page shown to hold it (migration 079)", () => {
  it('links a located page and shows the number the council prints on it', () => {
    const p = { ...DCP, pdf_page: 54, printed_page_label: '49', page_check: 'moved' };
    expect(pageHref(URL, p)).toBe(`${URL}#page=54`);
    expect(pageLabel(p)).toBe('page 49');
  });

  it('prints a lettered or dashed page number as the council prints it', () => {
    expect(pageLabel({ ...DCP, pdf_page: 9, printed_page_label: 'B5', page_check: 'on_page' })).toBe('page B5');
    expect(pageLabel({ ...DCP, pdf_page: 5, printed_page_label: '14-117', page_check: 'on_page' })).toBe('page 14-117');
  });

  it('falls back to the PDF page when the council prints no number', () => {
    expect(pageLabel({ ...DCP, pdf_page: 83, printed_page_label: null, page_check: 'moved' })).toBe('PDF page 83');
  });

  it('never anchors a page that was not shown to hold the rule', () => {
    for (const page_check of ['unresolved', 'not_found', 'too_short', 'no_source']) {
      const p = { ...DCP, pdf_page: 13, printed_page_label: '9', page_check };
      expect(pageAnchor(p)).toBeNull();
      expect(pageHref(URL, p)).toBe(URL);
      expect(pageLabel(p)).toBe(PAGE_NOT_LOCATED);
    }
  });

  it('fails closed on a council DCP row that was never checked (a failed post-publish check)', () => {
    const p = { ...DCP, pdf_page: 13, printed_page_label: null, page_check: null };
    expect(pageAnchor(p)).toBeNull();
    expect(pageHref(URL, p)).toBe(URL);
    expect(pageLabel(p)).toBe(PAGE_NOT_LOCATED);
  });

  it('leaves rows outside the check (LEP/SEPP) as they were', () => {
    const p = { pdf_page: 54, pdf_printed_page: 49, page_check: null, source_council: null };
    expect(pageAnchor(p)).toBe(54);
    expect(pageLabel(p)).toBe('PDF page 49');
  });

  it('says nothing about a page when there is none', () => {
    expect(pageAnchor({ pdf_page: null })).toBeNull();
    expect(pageAnchor({ pdf_page: 0 })).toBeNull();
    expect(pageLabel({})).toBeNull();
    expect(pageLabel({ ...DCP, page_check: 'unresolved', pdf_page: null })).toBeNull();
  });

  it('uses no assurance wording', () => {
    expect(PAGE_NOT_LOCATED).not.toMatch(/confirm|verif|certif|guarant|accura/i);
  });
});

describe('the report cites the same page reference', () => {
  const base = { id: 1, provision_text: 'x', v2_marker: '', v2_topic: '', document_name: '', v2_dcp_part: 'Part C' };
  it('uses the printed page on a located page', () => {
    expect(formatCitation({ ...base, ...DCP, pdf_page: 54, pdf_printed_page: 54, printed_page_label: '49', page_check: 'moved' }))
      .toBe('Part C, page 49');
  });
  it('says the page was not located rather than printing a wrong one', () => {
    expect(formatCitation({ ...base, ...DCP, pdf_page: 13, pdf_printed_page: 13, page_check: 'unresolved' }))
      .toBe(`Part C, ${PAGE_NOT_LOCATED}`);
  });
  it('keeps the printed page it always cited for a row outside the check', () => {
    expect(formatCitation({ ...base, pdf_page: 54, pdf_printed_page: 49 })).toBe('Part C, PDF page 49');
  });
});
