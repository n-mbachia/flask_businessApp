/**
 * Stub analytics module
 * These placeholders keep the dynamic imports from failing in cases where the real modules are not provided.
 */

export default function initAnalytics() {
  if (typeof console !== 'undefined') {
    console.debug('Analytics module loaded (stub).');
  }
}
