/**
 * API utility functions
 * Handles AJAX requests with proper headers and error handling
 */

const API_BASE_URL = '/api';

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

/**
 * Get default headers for API requests
 * @param {Object} headers - Additional headers to include
 * @returns {Object} Headers object
 */
function getDefaultHeaders(headers = {}) {
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCSRFToken(),
    'X-Requested-With': 'XMLHttpRequest',
    ...headers
  };
}

/**
 * Handle API response
 * @param {Response} response - Fetch response object
 * @returns {Promise} Resolves with JSON data or rejects with error
 */
async function handleResponse(response) {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const error = new Error(response.statusText);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

/**
 * Make an API request
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {string} method - HTTP method (GET, POST, etc.)
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @returns {Promise} Resolves with response data
 */
async function apiRequest(endpoint, method = 'GET', data = null, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = getDefaultHeaders(options.headers);
  
  const config = {
    method,
    headers,
    credentials: 'same-origin',
    ...options
  };

  if (data) {
    if (method === 'GET') {
      // Convert data to query string for GET requests
      const params = new URLSearchParams();
      Object.entries(data).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach(v => params.append(`${key}[]`, v));
        } else if (value !== null && value !== undefined) {
          params.append(key, value);
        }
      });
      config.url = `${url}?${params.toString()}`;
    } else if (data instanceof FormData) {
      // For FormData, let the browser set the Content-Type header
      delete headers['Content-Type'];
      config.body = data;
    } else {
      // For JSON data
      config.body = JSON.stringify(data);
    }
  }

  try {
    const response = await fetch(url, config);
    return await handleResponse(response);
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

/**
 * GET request
 * @param {string} endpoint - API endpoint
 * @param {Object} params - Query parameters
 * @param {Object} options - Additional fetch options
 * @returns {Promise} Resolves with response data
 */
function get(endpoint, params = {}, options = {}) {
  return apiRequest(endpoint, 'GET', params, options);
}

/**
 * POST request
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @returns {Promise} Resolves with response data
 */
function post(endpoint, data = {}, options = {}) {
  return apiRequest(endpoint, 'POST', data, options);
}

/**
 * PUT request
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @returns {Promise} Resolves with response data
 */
function put(endpoint, data = {}, options = {}) {
  return apiRequest(endpoint, 'PUT', data, options);
}

/**
 * PATCH request
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @returns {Promise} Resolves with response data
 */
function patch(endpoint, data = {}, options = {}) {
  return apiRequest(endpoint, 'PATCH', data, options);
}

/**
 * DELETE request
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @returns {Promise} Resolves with response data
 */
function del(endpoint, data = {}, options = {}) {
  return apiRequest(endpoint, 'DELETE', data, options);
}

// Export API methods
export default {
  get,
  post,
  put,
  patch,
  delete: del,
  request: apiRequest
};
