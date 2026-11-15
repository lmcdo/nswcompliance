/**
 * Helpers behind the inline feedback prompt.
 * The rule that matters: a value the user_type column might reject is never sent. New roles go as 'other' and are
 * written into the text, so a saved feedback cannot turn into a failed save.
 * prior-art-checked: no existing test covers lib/feedback-prompt.ts (new file); FeedbackWidget tests cover only the widget.
 */
import {
  EXTRA_ROLES,
  apiUserType,
  composeFeedbackText,
  isExtraRole,
  OPEN_FEEDBACK_EVENT,
  openFeedback,
} from '@/lib/feedback-prompt';

describe('apiUserType', () => {
  it.each(EXTRA_ROLES.map((r) => r.value))('sends the new role %s as "other"', (role) => {
    expect(apiUserType(role)).toBe('other');
  });

  it.each(['certifier', 'town_planner', 'architect', 'developer', 'student', 'academic', 'other'])(
    'passes the existing value %s through unchanged',
    (role) => {
      expect(apiUserType(role)).toBe(role);
    },
  );

  it('sends any value the column is not known to hold as "other", so a typo in an option can never reach it', () => {
    // Found by the pre-push cross-review: the first version passed unknown strings through unchanged.
    expect(apiUserType('something_else')).toBe('other');
    expect(apiUserType('townplanner')).toBe('other');
    expect(apiUserType('')).toBe('other');
  });
});

describe('isExtraRole', () => {
  it('is true only for the new roles', () => {
    expect(isExtraRole('builder')).toBe(true);
    expect(isExtraRole('certifier')).toBe(false);
    expect(isExtraRole('')).toBe(false);
  });
});

describe('composeFeedbackText', () => {
  it('returns a plain widget submission unchanged', () => {
    expect(composeFeedbackText('The setback looks wrong', { tab: null, role: 'certifier' })).toBe('The setback looks wrong');
  });

  it('adds the tab when the form was opened from the prompt', () => {
    expect(composeFeedbackText('Hello', { tab: 'sepp' })).toBe('[From: SEPP tab]\nHello');
    expect(composeFeedbackText('Hello', { tab: 'lep' })).toBe('[From: Planning Controls (LEP) tab]\nHello');
    expect(composeFeedbackText('Hello', { tab: 'dcp' })).toBe('[From: DCP Provisions tab]\nHello');
    expect(composeFeedbackText('Hello', { tab: 'upzoning' })).toBe('[From: Upzoning Check (LMR and TOD) page]\nHello');
  });

  it('keeps an unrecognised tab id readable instead of dropping it', () => {
    expect(composeFeedbackText('Hello', { tab: 'tod' })).toBe('[From: tod]\nHello');
  });

  it('adds the role for a new role, because it is sent as "other"', () => {
    expect(composeFeedbackText('Hello', { role: 'buyers_agent' })).toBe("[Role: Buyer's agent]\nHello");
  });

  it('adds both, tab first', () => {
    expect(composeFeedbackText('Hello', { tab: 'sepp', role: 'conveyancer' })).toBe(
      '[From: SEPP tab | Role: Conveyancer or solicitor]\nHello',
    );
  });

  it('does not repeat an existing role, which the user_type column already holds', () => {
    expect(composeFeedbackText('Hello', { tab: 'sepp', role: 'town_planner' })).toBe('[From: SEPP tab]\nHello');
  });
});

describe('openFeedback', () => {
  it('dispatches the open event with the detail', () => {
    const seen: unknown[] = [];
    const handler = (e: Event) => seen.push((e as CustomEvent).detail);
    window.addEventListener(OPEN_FEEDBACK_EVENT, handler);
    openFeedback({ tab: 'lep', feedbackType: 'feature_request' });
    window.removeEventListener(OPEN_FEEDBACK_EVENT, handler);
    expect(seen).toEqual([{ tab: 'lep', feedbackType: 'feature_request' }]);
  });
});
