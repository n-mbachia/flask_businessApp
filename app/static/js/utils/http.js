/**
 * HTTP Request Utility
 * Provides a robust wrapper around fetch with queuing, retries, and caching
 */

import { local, session } from './storage.js';

// ... rest of the code remains the same ...

// Export all HTTP methods
export {
  request,
  get,
  post,
  put,
  patch,
  delete, del,
  addRequestInterceptor,
  addResponseInterceptor,
  addErrorInterceptor,
  removeInterceptor,
  clearInterceptors,
  getCookie
};

export default {
  request,
  get,
  post,
  put,
  patch,
  delete: del,
  addRequestInterceptor,
  addResponseInterceptor,
  addErrorInterceptor,
  removeInterceptor,
  clearInterceptors,
  getCookie
};
