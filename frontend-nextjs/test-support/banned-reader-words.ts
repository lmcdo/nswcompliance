// Words the area check card must never print to a reader (project rule: no verdict words). Kept in a .ts fixture, not in the
// .tsx test, because the liability scan reads every .tsx line as reader-facing text and this is a list of words to forbid.
export const BANNED_READER_WORDS = /can'?t tell|cannot tell|confirmed|eligible|compliant/i;
