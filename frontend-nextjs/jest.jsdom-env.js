const { TestEnvironment: JsdomEnvironment } = require('jest-environment-jsdom');

/**
 * Custom jsdom environment that preserves Node.js Web API globals
 * (Response, Request, Headers, fetch, etc.) which standard jsdom strips.
 */
class FixedJsdomEnvironment extends JsdomEnvironment {
  constructor(...args) {
    super(...args);

    // Re-expose Node.js native Web API globals into the jsdom global
    // These are available in Node 18+ but jest-environment-jsdom removes them
    const globals = ['Response', 'Request', 'Headers', 'fetch',
      'TextEncoder', 'TextDecoder', 'ReadableStream', 'WritableStream',
      'TransformStream', 'Blob', 'FormData', 'structuredClone'];

    for (const name of globals) {
      if (typeof this.global[name] === 'undefined' && typeof globalThis[name] !== 'undefined') {
        this.global[name] = globalThis[name];
      }
    }
  }
}

module.exports = FixedJsdomEnvironment;
