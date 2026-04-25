/**
 * Adversarial tests for PostResultEmailStrip.
 * Covers: render state, lead API call shape, confirmation after submit,
 * silent error handling, empty email guard.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PostResultEmailStrip } from '@/components/reports/PostResultEmailStrip';

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

beforeEach(() => mockFetch.mockReset());

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

describe('PostResultEmailStrip — render', () => {
  it('renders email input and submit button', () => {
    render(<PostResultEmailStrip address="1 Smith St NSW 2000" product="solar-yield" />);
    expect(screen.getByPlaceholderText('your@email.com')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Email me' })).toBeInTheDocument();
  });

  it('renders default copy when none provided', () => {
    render(<PostResultEmailStrip address="1 Smith St NSW 2000" product="solar-yield" />);
    expect(screen.getByText('Get this result emailed to you')).toBeInTheDocument();
  });

  it('renders custom copy when provided', () => {
    render(
      <PostResultEmailStrip
        address="1 Smith St NSW 2000"
        product="flood-truth"
        copy="Get this flood risk report emailed to you — share with your conveyancer →"
      />
    );
    expect(screen.getByText(/share with your conveyancer/)).toBeInTheDocument();
  });

  it('does not show confirmation before submit', () => {
    render(<PostResultEmailStrip address="1 Smith St NSW 2000" product="solar-yield" />);
    expect(screen.queryByText(/Thanks/)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Submit — happy path
// ---------------------------------------------------------------------------

describe('PostResultEmailStrip — submit', () => {
  it('calls lead API with correct address, email, and interest_type', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(
      <PostResultEmailStrip
        address="42 Test Rd Leichhardt NSW 2040"
        product="shadow-detector"
      />
    );

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'buyer@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Email me' }));

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/canibuildit/lead');
    const body = JSON.parse(opts.body);
    expect(body.email).toBe('buyer@example.com');
    expect(body.address).toBe('42 Test Rd Leichhardt NSW 2040');
    expect(body.interest_type).toBe('shadow-detector');
    expect(body.eligible).toBeNull();
  });

  it('shows confirmation with email address after successful submit', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<PostResultEmailStrip address="1 Smith St NSW 2000" product="solar-yield" />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'test@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Email me' }));

    expect(await screen.findByText(/Thanks — we'll be in touch at test@test.com/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('your@email.com')).not.toBeInTheDocument();
  });

  it('hides form and shows confirmation even when API returns non-ok', async () => {
    // Silent failure — never block the UX
    mockFetch.mockResolvedValueOnce({ ok: false, json: async () => ({ error: 'DB error' }) });
    render(<PostResultEmailStrip address="1 Smith St NSW 2000" product="solar-yield" />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'silent@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Email me' }));

    expect(await screen.findByText(/Thanks — we'll be in touch at silent@test.com/)).toBeInTheDocument();
  });

  it('hides form and shows confirmation even when fetch throws', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network failure'));
    render(<PostResultEmailStrip address="1 Smith St NSW 2000" product="solar-yield" />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'error@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Email me' }));

    expect(await screen.findByText(/Thanks — we'll be in touch at error@test.com/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Edge cases
// ---------------------------------------------------------------------------

describe('PostResultEmailStrip — edge cases', () => {
  it('each instance is independent — submitting one does not affect another', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });

    render(
      <>
        <PostResultEmailStrip address="1 Smith St" product="solar-yield" />
        <PostResultEmailStrip address="2 Jones Ave" product="flood-truth" />
      </>
    );

    const inputs = screen.getAllByPlaceholderText('your@email.com');
    fireEvent.change(inputs[0], { target: { value: 'first@test.com' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Email me' })[0]);

    await waitFor(() =>
      expect(screen.getByText(/Thanks — we'll be in touch at first@test.com/)).toBeInTheDocument()
    );

    // Second strip still shows its form
    expect(inputs[1]).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Email me' })).toHaveLength(1);
  });

  it('product="threat-radar" sends correct interest_type', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<PostResultEmailStrip address="5 Bay St NSW 2000" product="threat-radar" />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'radar@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Email me' }));

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.interest_type).toBe('threat-radar');
  });
});
