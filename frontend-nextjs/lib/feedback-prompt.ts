// prior-art-checked: reuses components/feedback/FeedbackWidget.tsx and POST /api/feedback (stores to
// user_feedback and emails the operator). This file adds NO new endpoint and NO new storage. It only holds the
// event that opens the existing widget from an inline prompt, and the text builder for what that prompt adds.

/** Fired by an inline prompt; FeedbackWidget listens for it and opens. */
export const OPEN_FEEDBACK_EVENT = 'plotdetect:open-feedback';

export type PromptFeedbackType = 'feature_request' | 'missing_info' | 'general';

export interface OpenFeedbackDetail {
  /** The tab the visitor was on when they clicked: 'sepp' | 'lep' | 'dcp'. */
  tab?: string | null;
  feedbackType?: PromptFeedbackType;
}

/** Plain names for the tab ids, so a stored message reads as prose. */
export const TAB_LABEL: Record<string, string> = {
  sepp: 'SEPP tab',
  lep: 'Planning Controls (LEP) tab',
  dcp: 'DCP Provisions tab',
};

/**
 * Roles the page's real audience uses that the original list did not have.
 * They are sent to the API as 'other' (see apiUserType) and written into the message text instead, because
 * production's constraint on user_type could not be checked from this session. A role the column rejected would turn
 * a saved feedback into a failed save with no sign why.
 */
export const EXTRA_ROLES = [
  { value: 'conveyancer', label: 'Conveyancer or solicitor' },
  { value: 'buyers_agent', label: "Buyer's agent" },
  { value: 'builder', label: 'Builder' },
  { value: 'owner', label: 'Property owner' },
] as const;

export type ExtraRole = (typeof EXTRA_ROLES)[number]['value'];

export function isExtraRole(value: string): value is ExtraRole {
  return EXTRA_ROLES.some((r) => r.value === value);
}

/** The values the widget has always sent as user_type, so the column is known to hold them. */
const EXISTING_USER_TYPES: readonly string[] = [
  'certifier',
  'town_planner',
  'architect',
  'developer',
  'student',
  'academic',
  'other',
];

/**
 * What goes in the user_type field: a value the column already holds, never a new one. A new role, a typo in an option
 * and an empty value all go as 'other', which the route also uses as its own fallback.
 */
export function apiUserType(role: string): string {
  return EXISTING_USER_TYPES.includes(role) ? role : 'other';
}

/**
 * The message as stored. Adds a short bracketed line ONLY for facts the stored row would otherwise lose: the tab the
 * visitor opened the form from, and a role that was sent as 'other'. A plain widget submission is returned unchanged.
 */
export function composeFeedbackText(
  text: string,
  context: { tab?: string | null; role?: string },
): string {
  const parts: string[] = [];
  if (context.tab) parts.push(`From: ${TAB_LABEL[context.tab] ?? context.tab}`);
  if (context.role && isExtraRole(context.role)) {
    const label = EXTRA_ROLES.find((r) => r.value === context.role)?.label ?? context.role;
    parts.push(`Role: ${label}`);
  }
  return parts.length ? `[${parts.join(' | ')}]\n${text}` : text;
}

/** Ask the mounted FeedbackWidget to open. Does nothing on the server. */
export function openFeedback(detail: OpenFeedbackDetail): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<OpenFeedbackDetail>(OPEN_FEEDBACK_EVENT, { detail }));
}
