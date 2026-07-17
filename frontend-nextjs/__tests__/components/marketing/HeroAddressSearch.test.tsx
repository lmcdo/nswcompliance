import { render, screen, fireEvent } from '@testing-library/react';
import { HeroAddressSearch } from '@/components/marketing/HeroAddressSearch';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));
jest.mock('@/lib/analytics', () => ({ trackFunnelCta: jest.fn() }));

describe('HeroAddressSearch', () => {
  beforeEach(() => mockPush.mockClear());

  it('is a real text input, not a link (regression: the old hero CTA was a fake <Link>)', () => {
    render(<HeroAddressSearch />);
    expect(screen.getByPlaceholderText('Enter any NSW address...').tagName).toBe('INPUT');
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('routes a typed address to the reports hub, carrying it as ?address=', () => {
    render(<HeroAddressSearch />);
    fireEvent.change(screen.getByPlaceholderText('Enter any NSW address...'), {
      target: { value: '14 Hunter St, Lewisham NSW' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search this address' }));
    expect(mockPush).toHaveBeenCalledWith('/reports?address=14%20Hunter%20St%2C%20Lewisham%20NSW');
  });

  it('does not navigate when the address is empty or whitespace', () => {
    render(<HeroAddressSearch />);
    const input = screen.getByPlaceholderText('Enter any NSW address...');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.submit(input.closest('form')!);
    expect(mockPush).not.toHaveBeenCalled();
  });
});
