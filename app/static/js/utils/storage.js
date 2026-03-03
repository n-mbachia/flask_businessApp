/**
 * Storage utility
 * Provides a consistent API for working with localStorage and sessionStorage
 */

// Storage types
const STORAGE_TYPES = {
  LOCAL: 'local',
  SESSION: 'session'
};

// Default storage type
const DEFAULT_STORAGE_TYPE = STORAGE_TYPES.LOCAL;

// Storage instance cache
const storageInstances = new Map();

/**
 * Get a storage instance
 * @param {string} [type='local'] - Storage type ('local' or 'session')
 * @returns {Storage} The storage instance
 */
function getStorage(type = DEFAULT_STORAGE_TYPE) {
  if (storageInstances.has(type)) {
    return storageInstances.get(type);
  }

  const storage = type === STORAGE_TYPES.SESSION ? sessionStorage : localStorage;
  storageInstances.set(type, storage);
  return storage;
}

/**
 * Set an item in storage
 * @param {string} key - The key to set
 * @param {*} value - The value to store (will be JSON stringified)
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {boolean} True if successful, false otherwise
 */
function setItem(key, value, { type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    const serialized = JSON.stringify({
      value,
      timestamp: Date.now()
    });
    storage.setItem(key, serialized);
    return true;
  } catch (error) {
    console.error(`Failed to set item in ${type}Storage:`, error);
    return false;
  }
}

/**
 * Get an item from storage
 * @param {string} key - The key to get
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @param {*} [options.defaultValue=null] - Default value if key doesn't exist
 * @returns {*} The stored value or defaultValue
 */
function getItem(key, { type = DEFAULT_STORAGE_TYPE, defaultValue = null } = {}) {
  try {
    const storage = getStorage(type);
    const item = storage.getItem(key);
    
    if (item === null) return defaultValue;
    
    const parsed = JSON.parse(item);
    return parsed.value !== undefined ? parsed.value : defaultValue;
  } catch (error) {
    console.error(`Failed to get item from ${type}Storage:`, error);
    return defaultValue;
  }
}

/**
 * Remove an item from storage
 * @param {string} key - The key to remove
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {boolean} True if successful, false otherwise
 */
function removeItem(key, { type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    storage.removeItem(key);
    return true;
  } catch (error) {
    console.error(`Failed to remove item from ${type}Storage:`, error);
    return false;
  }
}

/**
 * Clear all items from storage
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {boolean} True if successful, false otherwise
 */
function clear({ type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    storage.clear();
    return true;
  } catch (error) {
    console.error(`Failed to clear ${type}Storage:`, error);
    return false;
  }
}

/**
 * Get all keys from storage
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {string[]} Array of keys
 */
function keys({ type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    return Object.keys(storage);
  } catch (error) {
    console.error(`Failed to get keys from ${type}Storage:`, error);
    return [];
  }
}

/**
 * Get the number of items in storage
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {number} Number of items
 */
function length({ type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    return storage.length;
  } catch (error) {
    console.error(`Failed to get length of ${type}Storage:`, error);
    return 0;
  }
}

/**
 * Get an item's timestamp from storage
 * @param {string} key - The key to check
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {number|null} Timestamp in milliseconds or null if not found
 */
function getItemTimestamp(key, { type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    const item = storage.getItem(key);
    
    if (item === null) return null;
    
    const parsed = JSON.parse(item);
    return parsed.timestamp || null;
  } catch (error) {
    console.error(`Failed to get timestamp from ${type}Storage:`, error);
    return null;
  }
}

/**
 * Check if an item exists in storage
 * @param {string} key - The key to check
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {boolean} True if the key exists
 */
function hasItem(key, { type = DEFAULT_STORAGE_TYPE } = {}) {
  try {
    const storage = getStorage(type);
    return storage.getItem(key) !== null;
  } catch (error) {
    console.error(`Failed to check item in ${type}Storage:`, error);
    return false;
  }
}

/**
 * Get all items from storage
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @param {boolean} [options.includeTimestamps=false] - Whether to include timestamps
 * @returns {Object} Object with all key-value pairs
 */
function getAll({ type = DEFAULT_STORAGE_TYPE, includeTimestamps = false } = {}) {
  try {
    const storage = getStorage(type);
    const result = {};
    
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (key === null) continue;
      
      const item = storage.getItem(key);
      if (item === null) continue;
      
      try {
        const parsed = JSON.parse(item);
        result[key] = includeTimestamps ? parsed : parsed.value;
      } catch (e) {
        // Handle non-JSON values
        result[key] = includeTimestamps 
          ? { value: item, timestamp: null } 
          : item;
      }
    }
    
    return result;
  } catch (error) {
    console.error(`Failed to get all items from ${type}Storage:`, error);
    return {};
  }
}

/**
 * Remove items older than a specified age
 * @param {number} maxAge - Maximum age in milliseconds
 * @param {Object} [options] - Storage options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @returns {string[]} Array of removed keys
 */
function removeOlderThan(maxAge, { type = DEFAULT_STORAGE_TYPE } = {}) {
  const removed = [];
  const now = Date.now();
  
  try {
    const storage = getStorage(type);
    
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (key === null) continue;
      
      const item = storage.getItem(key);
      if (item === null) continue;
      
      try {
        const parsed = JSON.parse(item);
        if (parsed.timestamp && (now - parsed.timestamp) > maxAge) {
          storage.removeItem(key);
          removed.push(key);
        }
      } catch (e) {
        // Skip items that can't be parsed
        continue;
      }
    }
  } catch (error) {
    console.error(`Failed to remove old items from ${type}Storage:`, error);
  }
  
  return removed;
}

/**
 * Add a storage change listener
 * @param {Function} callback - Function to call when storage changes
 * @param {Object} [options] - Listener options
 * @param {string} [options.type='local'] - Storage type ('local' or 'session')
 * @param {string[]} [options.keys] - Specific keys to watch (all if not specified)
 * @returns {Function} Function to remove the listener
 */
function addStorageListener(callback, { type = DEFAULT_STORAGE_TYPE, keys } = {}) {
  const storage = getStorage(type);
  const isLocal = type === STORAGE_TYPES.LOCAL;
  
  const listener = (event) => {
    // Skip if:
    // 1. Not the storage we're interested in
    // 2. Event is from a different storage area
    if ((isLocal && event.storageArea !== localStorage) ||
        (!isLocal && event.storageArea !== sessionStorage)) {
      return;
    }
    
    // If specific keys are provided, check if the changed key is in the list
    if (Array.isArray(keys) && !keys.includes(event.key)) {
      return;
    }
    
    // Get the old and new values
    let oldValue, newValue;
    
    try {
      oldValue = event.oldValue ? JSON.parse(event.oldValue) : null;
      newValue = event.newValue ? JSON.parse(event.newValue) : null;
    } catch (e) {
      // If parsing fails, use raw values
      oldValue = event.oldValue;
      newValue = event.newValue;
    }
    
    // Call the callback with consistent data
    callback({
      key: event.key,
      oldValue: oldValue?.value ?? oldValue,
      newValue: newValue?.value ?? newValue,
      oldTimestamp: oldValue?.timestamp || null,
      newTimestamp: newValue?.timestamp || null,
      url: event.url,
      storageArea: event.storageArea
    });
  };
  
  // Add the event listener
  window.addEventListener('storage', listener);
  
  // Return a function to remove the listener
  return () => {
    window.removeEventListener('storage', listener);
  };
}

// Export storage types
export const StorageTypes = Object.freeze(STORAGE_TYPES);

// Export all functions
export {
  getStorage,
  setItem,
  getItem,
  removeItem,
  clear,
  keys,
  length,
  getItemTimestamp,
  hasItem,
  getAll,
  removeOlderThan,
  addStorageListener
};

// Convenience methods for localStorage
export const local = {
  set: (key, value) => setItem(key, value, { type: STORAGE_TYPES.LOCAL }),
  get: (key, defaultValue) => getItem(key, { type: STORAGE_TYPES.LOCAL, defaultValue }),
  remove: (key) => removeItem(key, { type: STORAGE_TYPES.LOCAL }),
  clear: () => clear({ type: STORAGE_TYPES.LOCAL }),
  keys: () => keys({ type: STORAGE_TYPES.LOCAL }),
  length: () => length({ type: STORAGE_TYPES.LOCAL }),
  getTimestamp: (key) => getItemTimestamp(key, { type: STORAGE_TYPES.LOCAL }),
  has: (key) => hasItem(key, { type: STORAGE_TYPES.LOCAL }),
  getAll: (options) => getAll({ ...options, type: STORAGE_TYPES.LOCAL }),
  removeOlderThan: (maxAge) => removeOlderThan(maxAge, { type: STORAGE_TYPES.LOCAL }),
  on: (callback, options) => addStorageListener(callback, { ...options, type: STORAGE_TYPES.LOCAL })
};

// Convenience methods for sessionStorage
export const session = {
  set: (key, value) => setItem(key, value, { type: STORAGE_TYPES.SESSION }),
  get: (key, defaultValue) => getItem(key, { type: STORAGE_TYPES.SESSION, defaultValue }),
  remove: (key) => removeItem(key, { type: STORAGE_TYPES.SESSION }),
  clear: () => clear({ type: STORAGE_TYPES.SESSION }),
  keys: () => keys({ type: STORAGE_TYPES.SESSION }),
  length: () => length({ type: STORAGE_TYPES.SESSION }),
  getTimestamp: (key) => getItemTimestamp(key, { type: STORAGE_TYPES.SESSION }),
  has: (key) => hasItem(key, { type: STORAGE_TYPES.SESSION }),
  getAll: (options) => getAll({ ...options, type: STORAGE_TYPES.SESSION }),
  removeOlderThan: (maxAge) => removeOlderThan(maxAge, { type: STORAGE_TYPES.SESSION }),
  on: (callback, options) => addStorageListener(callback, { ...options, type: STORAGE_TYPES.SESSION })
};

// Default export with all functionality
export default {
  StorageTypes,
  getStorage,
  setItem,
  getItem,
  removeItem,
  clear,
  keys,
  length,
  getItemTimestamp,
  hasItem,
  getAll,
  removeOlderThan,
  addStorageListener,
  local,
  session
};
