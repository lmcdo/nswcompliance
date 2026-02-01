/**
 * Response Encoding for Anti-Copycat Security
 *
 * Obfuscates API response structure to make reverse-engineering harder.
 * Responses are base64-encoded to hide field names and data patterns.
 */

export interface StandardResponse {
  answer: string;
  citations: string[];
  confidence?: number;
  suggestedQuestions?: string[];
  category?: string;
}

export interface EncodedResponse {
  d: string;           // data (base64 encoded answer)
  c: string[];         // citations (array of base64 strings)
  f?: number;          // confidence (0-100, not encoded - just a number)
  s?: string[];        // suggested questions (base64 encoded)
  t?: string;          // category/type (base64 encoded)
}

/**
 * Encode a standard response into obfuscated format
 */
export function encodeResponse(response: StandardResponse): EncodedResponse {
  const encoded: EncodedResponse = {
    d: btoa(response.answer),
    c: response.citations.map(c => btoa(c)),
  };

  if (response.confidence !== undefined) {
    encoded.f = Math.round(response.confidence * 100);
  }

  if (response.suggestedQuestions && response.suggestedQuestions.length > 0) {
    encoded.s = response.suggestedQuestions.map(q => btoa(q));
  }

  if (response.category) {
    encoded.t = btoa(response.category);
  }

  return encoded;
}

/**
 * Decode an obfuscated response back to standard format
 */
export function decodeResponse(encoded: EncodedResponse): StandardResponse {
  const response: StandardResponse = {
    answer: atob(encoded.d),
    citations: encoded.c.map(c => atob(c)),
  };

  if (encoded.f !== undefined) {
    response.confidence = encoded.f / 100;
  }

  if (encoded.s && encoded.s.length > 0) {
    response.suggestedQuestions = encoded.s.map(q => atob(q));
  }

  if (encoded.t) {
    response.category = atob(encoded.t);
  }

  return response;
}

/**
 * Type guard to check if response is encoded
 */
export function isEncodedResponse(obj: any): obj is EncodedResponse {
  return typeof obj === 'object'
    && typeof obj.d === 'string'
    && Array.isArray(obj.c);
}
