// Runs via setupFiles — BEFORE jsdom environment is initialized.
// Captures Node 20+ native Web API constructors before jsdom can strip them.
// The jest.setup.js (setupFilesAfterEnv) restores them after jsdom init.

const _Response = globalThis.Response;
const _Request = globalThis.Request;
const _Headers = globalThis.Headers;
const _fetch = globalThis.fetch;

// Store on a property that jsdom won't touch
globalThis.__NODE_RESPONSE__ = _Response;
globalThis.__NODE_REQUEST__ = _Request;
globalThis.__NODE_HEADERS__ = _Headers;
globalThis.__NODE_FETCH__ = _fetch;
