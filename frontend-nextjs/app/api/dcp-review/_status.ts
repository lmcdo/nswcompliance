// prior-art-checked: reuse not viable because the matches (reports/status, compliance-status
// components) are unrelated UI/report status displays; this is the DCP-review verdict enum
// map, currently duplicated inline in the per-id route — extracted here so both the per-id
// and per-chapter routes share one definition.
// Shared DCP-review verdict → dcp_review_queue status mapping, used by both the
// per-id route and the per-chapter bulk route so the enum values live in one place.
export const ACTION_TO_STATUS: Record<string, string> = {
  approve: 'approved',
  reject: 'rejected',
  'needs-info': 'needs_info',
};
