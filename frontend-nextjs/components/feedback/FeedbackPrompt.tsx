'use client';

// prior-art-checked: reuses components/feedback/FeedbackWidget.tsx (mounted on this page) and POST /api/feedback.
// This is only a visible entry point that opens that widget; it stores nothing itself.

import { MessageCircle } from 'lucide-react';
import { posthog } from '@/components/providers/PostHogProvider';
import { openFeedback } from '@/lib/feedback-prompt';

interface Props {
  /** The tab the visitor is on: 'sepp' | 'lep' | 'dcp'. Recorded with the message and the click. */
  tab: string;
}

/**
 * A visible prompt above the regulatory tabs. The floating "Feedback" button already exists but is small and sits in
 * a corner, and the page has had almost no outside feedback. This asks one plain question and opens the same form.
 */
export default function FeedbackPrompt({ tab }: Props) {
  const handleClick = () => {
    try {
      // The click is counted on its own, so interest can be measured even when nobody finishes the form.
      posthog.capture('feedback_prompt_clicked', { tab });
    } catch {
      // analytics only; never block opening the form
    }
    openFeedback({ tab, feedbackType: 'feature_request' });
  };

  return (
    <div
      className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3"
      data-testid="feedback-prompt"
    >
      <p className="text-sm text-blue-900">
        Is there something you wanted to find out about this property that this page does not tell you?
      </p>
      <button
        type="button"
        onClick={handleClick}
        className="inline-flex min-h-[44px] items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        <MessageCircle size={16} aria-hidden="true" />
        Tell us what you were looking for
      </button>
    </div>
  );
}
