/**
 * HTTP Request Utility
 * Provides a lightweight wrapper around fetch with interceptor hooks.
 */

import { local, session } from './storage.js';

const interceptors = {
  request: [],
  response: [],
  error: []
};

let nextInterceptorId = 1;

function addInterceptor(type, handler) {
  const id = nextInterceptorId++;
  interceptors[type].push({ id, handler });
  return id;
}

function removeInterceptor(id) {
  Object.values(interceptors).forEach(list => {
    const index = list.findIndex(entry => entry.id === id);
    if (index !== -1) {
      list.splice(index, 1);
    }
  });
}

function clearInterceptors() {
  Object.values(interceptors).forEach(list => list.splice(0, list.length));
}

async function applyRequestInterceptors(config) {
  let outgoing = config;
  for (const { handler } of interceptors.request) {
    const result = await handler(outgoing);
    if (result) {
      outgoing = result;
    }
  }
  return outgoing;
}

async function applyResponseInterceptors(response) {
  for (const { handler } of interceptors.response) {
    await handler(response);
  }
}

async function applyErrorInterceptors(error) {
  for (const { handler } of interceptors.error) {
    await handler(error);
  }
}

function buildHeaders(customHeaders = {}) {
  return {
    Accept: 'application/json, text/plain, */*',
    'X-Requested-With': 'XMLHttpRequest',
    ...customHeaders
  };
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

async function request(url, options = {}) {
  let config = {
    url,
    method: (options.method || 'GET').toUpperCase(),
    credentials: 'same-origin',
    headers: buildHeaders(options.headers),
    ...options
  };

  config = await applyRequestInterceptors(config);

  const { url: nextUrl, headers, ...fetchOptions } = config;

  try {
    const response = await fetch(nextUrl, {
      ...fetchOptions,
      headers
    });

    await applyResponseInterceptors(response);

    if (!response.ok) {
      const error = new Error(`Request failed with status ${response.status}`);
      error.response = response;
      error.status = response.status;
      throw error;
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return response.json();
    }

    return response.text();
  } catch (error) {
    await applyErrorInterceptors(error);
    throw error;
  }
}

function get(url, options) {
  return request(url, { ...options, method: 'GET' });
}

function post(url, options) {
  return request(url, { ...options, method: 'POST' });
}

function put(url, options) {
  return request(url, { ...options, method: 'PUT' });
}

function patch(url, options) {
  return request(url, { ...options, method: 'PATCH' });
}

function del(url, options) {
  return request(url, { ...options, method: 'DELETE' });
}

function addRequestInterceptor(handler) {
  return addInterceptor('request', handler);
}

function addResponseInterceptor(handler) {
  return addInterceptor('response', handler);
}

function addErrorInterceptor(handler) {
  return addInterceptor('error', handler);
}

function clearAllInterceptors() {
  clearInterceptors();
}

export {
  request,
  get,
  post,
  put,
  patch,
  del,
  addRequestInterceptor,
  addResponseInterceptor,
  addErrorInterceptor,
  removeInterceptor,
  clearAllInterceptors as clearInterceptors,
  getCookie,
  local,
  session
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
  clearInterceptors: clearAllInterceptors,
  getCookie,
  local,
  session
};
