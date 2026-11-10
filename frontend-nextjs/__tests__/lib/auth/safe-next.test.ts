import { safeNext } from '@/lib/auth/safe-next';

describe('safeNext — after sign-in, only a path on this site', () => {
  it.each([
    ['/internal/dcp-review', '/internal/dcp-review'],
    ['/reports?x=1', '/reports?x=1'],
  ])('keeps %s', (input, out) => {
    expect(safeNext(input)).toBe(out);
  });

  it.each([
    [null],
    [undefined],
    [''],
    ['https://evil.example/'],
    ['//evil.example/'],
    ['/\\evil.example'],
    ['javascript:alert(1)'],
  ])('falls back to /reports for %p', (input) => {
    expect(safeNext(input as string | null | undefined)).toBe('/reports');
  });
});
