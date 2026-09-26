import { pageAnchor, pageHref, pageLabel } from '@/lib/page-citation';
import { formatCitation } from '@/lib/pdf/formatProvisions';

const URL = 'https://pub.r2.dev/dcp/ashfield/v1/part-c.pdf';

describe("a DCP rule's page link opens only a page that holds it (migration 079)", () => {
  it('links a checked page and shows the number the council prints on it', () => {
    const p = { pdf_page: 54, printed_page_label: '49', page_check: 'moved' };
    expect(pageHref(URL, p)).toBe(`${URL}#page=54`);
    expect(pageLabel(p)).toBe('page 49');
  });

  it('prints a lettered or dashed page number as the council prints it', () => {
    expect(pageLabel({ pdf_page: 9, printed_page_label: 'B5', page_check: 'on_page' })).toBe('page B5');
    expect(pageLabel({ pdf_page: 5, printed_page_label: '14-117', page_check: 'on_page' })).toBe('page 14-117');
  });

  it('falls back to the PDF page when the council prints no number', () => {
    expect(pageLabel({ pdf_page: 83, printed_page_label: null, page_check: 'moved' })).toBe('PDF page 83');
  });

  it('never sends a reader to a page that does not hold the rule', () => {
    for (const page_check of ['unresolved', 'not_found']) {
      const p = { pdf_page: 13, printed_page_label: '9', page_check };
      expect(pageAnchor(p)).toBeNull();
      expect(pageHref(URL, p)).toBe(URL);
      expect(pageLabel(p)).toBe('page not confirmed');
    }
  });

  it('does not show a printed label on a page that was never checked', () => {
    // A label belongs to the checked page; an unchecked pdf_page may be the chunk start.
    const p = { pdf_page: 13, printed_page_label: '9', page_check: null };
    expect(pageLabel(p)).toBe('PDF page 13');
    expect(pageHref(URL, p)).toBe(`${URL}#page=13`);
  });

  it('has no page reference when there is no page', () => {
    expect(pageAnchor({ pdf_page: null })).toBeNull();
    expect(pageAnchor({ pdf_page: 0 })).toBeNull();
    expect(pageLabel({})).toBeNull();
  });
});

describe('the report cites the same page reference', () => {
  const base = { id: 1, provision_text: 'x', v2_marker: '', v2_topic: '', document_name: '', v2_dcp_part: 'Part C' };
  it('uses the printed page on a checked page', () => {
    expect(formatCitation({ ...base, pdf_page: 54, printed_page_label: '49', page_check: 'moved' })).toBe('Part C, page 49');
  });
  it('says the page is not confirmed rather than printing a wrong one', () => {
    expect(formatCitation({ ...base, pdf_page: 13, page_check: 'unresolved' })).toBe('Part C, page not confirmed');
  });
});
