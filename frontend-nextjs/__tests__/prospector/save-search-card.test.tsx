/**
 * SaveSearchCard tests — validation, submit payload, success/error states.
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

import { SaveSearchCard } from '@/components/prospector/SaveSearchCard';

jest.mock('@/lib/analytics', () => ({
  trackProspectorEmailCapture: jest.fn(),
}));

import { trackProspectorEmailCapture } from '@/lib/analytics';

describe('SaveSearchCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    }) as jest.Mock;
  });

  const fillAndSubmit = (email: string) => {
    const input = screen.getByLabelText('Email address');
    fireEvent.change(input, { target: { value: email } });
    // fireEvent.submit bypasses jsdom's native type="email" constraint
    // validation so the component's own regex path is exercised
    fireEvent.submit(input.closest('form')!);
  };

  it('rejects an invalid email without calling the API', async () => {
    render(<SaveSearchCard lgaName="INNER WEST" filterQuery="" />);
    fillAndSubmit('not-an-email');
    expect(await screen.findByRole('alert')).toHaveTextContent(/valid email/i);
    expect(global.fetch).not.toHaveBeenCalled();
    expect(trackProspectorEmailCapture).not.toHaveBeenCalled();
  });

  it('POSTs to /api/verify-interest with source=prospector and the filter URL', async () => {
    render(<SaveSearchCard lgaName="INNER WEST" filterQuery="zone_codes=R2&heritage=false" />);
    fillAndSubmit('dev@example.com');
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe('/api/verify-interest');
    expect(JSON.parse(opts.body)).toEqual({
      email: 'dev@example.com',
      role: null,
      source: 'prospector',
      council_name: 'INNER WEST',
      address: '/prospector?zone_codes=R2&heritage=false',
    });
  });

  it('includes the selected role in the payload and analytics event', async () => {
    render(<SaveSearchCard lgaName="INNER WEST" filterQuery="zone_codes=R2" />);
    fireEvent.change(screen.getByLabelText('Your role'), {
      target: { value: 'planner' },
    });
    fillAndSubmit('planner@example.com');
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.role).toBe('planner');
    await screen.findByText(/saved/i);
    expect(trackProspectorEmailCapture).toHaveBeenCalledWith({
      lga: 'INNER WEST',
      has_filters: true,
      role: 'planner',
    });
  });

  it('shows success state and fires analytics event on 200', async () => {
    render(<SaveSearchCard lgaName="INNER WEST" filterQuery="zone_codes=R2" />);
    fillAndSubmit('dev@example.com');
    expect(await screen.findByText(/saved/i)).toBeInTheDocument();
    expect(trackProspectorEmailCapture).toHaveBeenCalledWith({
      lga: 'INNER WEST',
      has_filters: true,
      role: null,
    });
  });

  it('sends bare /prospector and has_filters=false when no filters set', async () => {
    render(<SaveSearchCard lgaName="INNER WEST" filterQuery="" />);
    fillAndSubmit('dev@example.com');
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.address).toBe('/prospector');
    await screen.findByText(/saved/i);
    expect(trackProspectorEmailCapture).toHaveBeenCalledWith({
      lga: 'INNER WEST',
      has_filters: false,
      role: null,
    });
  });

  it('shows the API error message and no analytics event on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: async () => ({ error: 'invalid email address' }),
    });
    render(<SaveSearchCard lgaName="INNER WEST" filterQuery="" />);
    fillAndSubmit('dev@example.com');
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid email address');
    expect(trackProspectorEmailCapture).not.toHaveBeenCalled();
    // form is still usable for retry
    expect(screen.getByRole('button', { name: /notify me/i })).toBeEnabled();
  });
});
