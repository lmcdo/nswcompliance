/**
 * Tests for EmailGate component.
 * Verifies: gate blocks content, email submission reveals content,
 * localStorage persistence, and lead API call.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmailGate } from '@/components/reports/EmailGate';

// Mock fetch
const mockFetch = jest.fn().mockResolvedValue({ ok: true });
global.fetch = mockFetch;

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('EmailGate — locked state', () => {
  it('shows email form when no email in localStorage', () => {
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Secret content</div>
      </EmailGate>
    );
    expect(screen.queryByText('Secret content')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText('your@email.com')).toBeInTheDocument();
    expect(screen.getByText('Continue')).toBeInTheDocument();
  });

  it('shows prompt text', () => {
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Hidden</div>
      </EmailGate>
    );
    expect(screen.getByText('See the detailed breakdown')).toBeInTheDocument();
  });
});

describe('EmailGate — unlock via form', () => {
  it('reveals children after email submit', async () => {
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Secret content</div>
      </EmailGate>
    );

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.click(screen.getByText('Continue'));

    await waitFor(() => {
      expect(screen.getByText('Secret content')).toBeInTheDocument();
    });
  });

  it('stores email in localStorage', async () => {
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Content</div>
      </EmailGate>
    );

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.click(screen.getByText('Continue'));

    await waitFor(() => {
      expect(localStorage.getItem('plotdetect_email')).toBe('test@example.com');
    });
  });

  it('calls lead API with correct payload', async () => {
    render(
      <EmailGate address="42 Jones Ave" product="solar-yield">
        <div>Content</div>
      </EmailGate>
    );

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'user@test.com' },
    });
    fireEvent.click(screen.getByText('Continue'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'user@test.com',
          address: '42 Jones Ave',
          eligible: null,
          interest_type: 'solar-yield',
        }),
      });
    });
  });
});

describe('EmailGate — pre-unlocked via localStorage', () => {
  it('shows children immediately when email exists in localStorage', () => {
    localStorage.setItem('plotdetect_email', 'stored@email.com');
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Secret content</div>
      </EmailGate>
    );
    expect(screen.getByText('Secret content')).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('your@email.com')).not.toBeInTheDocument();
  });
});

describe('EmailGate — edge cases', () => {
  it('does not submit with empty email', () => {
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Content</div>
      </EmailGate>
    );
    fireEvent.click(screen.getByText('Continue'));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('trims whitespace from email', async () => {
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Content</div>
      </EmailGate>
    );

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: '  user@test.com  ' },
    });
    fireEvent.click(screen.getByText('Continue'));

    await waitFor(() => {
      expect(localStorage.getItem('plotdetect_email')).toBe('user@test.com');
    });
  });

  it('still reveals content when API call fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    render(
      <EmailGate address="1 Smith St" product="flood-truth">
        <div>Secret content</div>
      </EmailGate>
    );

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.click(screen.getByText('Continue'));

    await waitFor(() => {
      expect(screen.getByText('Secret content')).toBeInTheDocument();
    });
  });
});
