/**
 * Stub enhanced analytics module
 * Bundles expect this file to exist even if no custom logic is provided.
 */

export default function initEnhancedAnalytics() {
  if (typeof console !== 'undefined') {
    console.debug('Analytics enhanced module loaded (stub).');
  }
}
