/**
 * DcpRequestCta — the missing-DCP point-of-pain email capture. Must POST the
 * council + email to the existing /api/dcp-interest route and confirm on success.
 * Failing silent (never blocking the report) is part of the contract.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

jest.mock('posthog-js', () => ({ capture: jest.fn() }));

import { DcpRequestCta } from '@/components/compliance/DcpRequestCta';

describe('DcpRequestCta', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })) as jest.Mock;
  });
  afterEach(() => jest.resetAllMocks());

  it('renders nothing without a council', () => {
    const { container } = render(<DcpRequestCta council="" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('posts council + email to /api/dcp-interest and confirms', async () => {
    render(<DcpRequestCta council="Edward River" address="1 Test St" />);
    fireEvent.change(screen.getByPlaceholderText('you@email.com'), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /request this dcp/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/dcp-interest',
        expect.objectContaining({ method: 'POST' }),
      );
    });
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body).toEqual({
      email: 'dev@example.com',
      council_name: 'Edward River',
      address: '1 Test St',
    });
    expect(await screen.findByText(/Noted/i)).toBeInTheDocument();
    expect(screen.getByText(/Edward River/)).toBeInTheDocument();
  });

  it('does not submit an empty email', () => {
    render(<DcpRequestCta council="Edward River" />);
    // Empty input; clicking should not fire a request (required + guard).
    fireEvent.click(screen.getByRole('button', { name: /request this dcp/i }));
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
