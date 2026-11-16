/**
 * The privacy page must say the site records sessions. PostHog session recording is on (components/providers/PostHogProvider.tsx), and testers enter
 * real addresses; the page used to say only "anonymous usage analytics".
 * prior-art-checked: no test covered the privacy page text.
 */
import React from 'react';
import { render } from '@testing-library/react';
import PrivacyPage from '@/app/privacy/page';

describe('privacy page', () => {
  const text = () => render(<PrivacyPage />).container.textContent!.replace(/\s+/g, ' ');

  it('says pages are recorded, what is recorded, and that form text is masked', () => {
    const t = text();
    expect(t).toMatch(/recordings of how pages are used/i);
    expect(t).toMatch(/what is shown on screen/i);
    expect(t).toMatch(/address you search for/i);
    expect(t).toMatch(/text typed into form fields is masked/i);
    expect(t).toMatch(/web address of a page can also include an address you searched for/i);
  });

  it('lists PostHog as analytics and session recordings, no longer as anonymous analytics alone', () => {
    const t = text();
    expect(t).toMatch(/PostHog — usage analytics and session recordings/);
    expect(t).not.toMatch(/PostHog — anonymous usage analytics/);
  });

  it('says what the Feedback button saves and that the email is optional', () => {
    const t = text();
    expect(t).toMatch(/Feedback you send through the Feedback button/i);
    expect(t).toMatch(/email address if you choose to add one/i);
  });

  it('names the operator by ABN, not ABN pending', () => {
    const t = text();
    expect(t).toMatch(/ABN 76 629 477 885/);
    expect(t).not.toMatch(/ABN pending/);
  });

  it('keeps the promise that nothing is sold or used for advertising', () => {
    expect(text()).toMatch(/do not sell your personal information/i);
  });
});
