/**
 * Tests for BlogEmailCapture component.
 * Verifies: renders form, submits to lead API, shows confirmation.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BlogEmailCapture } from '@/components/marketing/BlogEmailCapture';

const mockFetch = jest.fn().mockResolvedValue({ ok: true });
global.fetch = mockFetch;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('BlogEmailCapture — render', () => {
  it('shows email input and subscribe button', () => {
    render(<BlogEmailCapture />);
    expect(screen.getByPlaceholderText('your@email.com')).toBeInTheDocument();
    expect(screen.getByText('Subscribe')).toBeInTheDocument();
  });

  it('shows value proposition text', () => {
    render(<BlogEmailCapture />);
    expect(screen.getByText('Get property intelligence updates')).toBeInTheDocument();
  });
});

describe('BlogEmailCapture — submit', () => {
  it('calls lead API with blog-subscriber interest type', async () => {
    render(<BlogEmailCapture />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'reader@example.com' },
    });
    fireEvent.click(screen.getByText('Subscribe'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'reader@example.com',
          address: '',
          eligible: null,
          interest_type: 'blog-subscriber',
        }),
      });
    });
  });

  it('shows confirmation after submit', async () => {
    render(<BlogEmailCapture />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'reader@example.com' },
    });
    fireEvent.click(screen.getByText('Subscribe'));

    await waitFor(() => {
      expect(screen.getByText(/on the list/)).toBeInTheDocument();
    });
    expect(screen.queryByText('Subscribe')).not.toBeInTheDocument();
  });

  it('still shows confirmation when API fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('fail'));
    render(<BlogEmailCapture />);

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'reader@example.com' },
    });
    fireEvent.click(screen.getByText('Subscribe'));

    await waitFor(() => {
      expect(screen.getByText(/on the list/)).toBeInTheDocument();
    });
  });
});
