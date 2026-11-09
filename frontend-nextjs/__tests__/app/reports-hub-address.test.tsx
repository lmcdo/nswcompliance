import { render, screen } from '@testing-library/react';
import ReportsLanding from '@/app/reports/page';

// The reports hub is an async server component. Call it directly with a resolved
// searchParams promise and render the returned tree — next/link renders <a href>.

describe('ReportsLanding — address threading from the homepage hero search', () => {
  it('threads ?address= into both product card hrefs and shows the active-address banner', async () => {
    const ui = await ReportsLanding({
      searchParams: Promise.resolve({ address: '14 Hunter St, Lewisham NSW' }),
    });
    render(ui);

    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);
    // The hub now lists the two pilot products only (lib/pilot-focus.ts).
    expect(links.map((a) => (a.getAttribute('href') || '').split('?')[0]).sort()).toEqual(['/assessment', '/reports/intelligence-brief']);
    links.forEach((a) => {
      expect(a.getAttribute('href')).toContain('?address=14%20Hunter%20St%2C%20Lewisham%20NSW');
    });
    expect(screen.getByText('14 Hunter St, Lewisham NSW')).toBeInTheDocument();
  });

  it('leaves product hrefs bare and hides the banner when no address is supplied', async () => {
    const ui = await ReportsLanding({ searchParams: Promise.resolve({}) });
    render(ui);

    screen.getAllByRole('link').forEach((a) => {
      expect(a.getAttribute('href')).not.toContain('?address=');
    });
    expect(screen.queryByText(/^Address:/)).toBeNull();
  });

  it('ignores a malformed (array) address param rather than serialising it', async () => {
    const ui = await ReportsLanding({
      searchParams: Promise.resolve({ address: ['a', 'b'] }),
    });
    render(ui);

    screen.getAllByRole('link').forEach((a) => {
      expect(a.getAttribute('href')).not.toContain('?address=');
    });
  });
});
