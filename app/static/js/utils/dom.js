/**
 * DOM utility functions
 * Provides helper methods for common DOM manipulations
 */

/**
 * Toggle a class on an element
 * @param {Element} element - The DOM element
 * @param {string} className - The class to toggle
 * @param {boolean} [force] - Force add or remove the class
 */
export function toggleClass(element, className, force) {
  if (element) {
    element.classList.toggle(className, force);
  }
}

/**
 * Check if an element has a class
 * @param {Element} element - The DOM element
 * @param {string} className - The class to check
 * @returns {boolean} True if the element has the class
 */
export function hasClass(element, className) {
  return element && element.classList.contains(className);
}

/**
 * Add a class to an element
 * @param {Element} element - The DOM element
 * @param {string} className - The class to add
 */
export function addClass(element, className) {
  if (element) {
    element.classList.add(className);
  }
}

/**
 * Remove a class from an element
 * @param {Element} element - The DOM element
 * @param {string} className - The class to remove
 */
export function removeClass(element, className) {
  if (element) {
    element.classList.remove(className);
  }
}

/**
 * Get the closest parent element matching a selector
 * @param {Element} element - The starting element
 * @param {string} selector - The CSS selector to match
 * @returns {Element|null} The closest matching parent or null
 */
export function closest(element, selector) {
  if (!element || !selector) return null;
  return element.closest(selector);
}

/**
 * Find all elements matching a selector within a parent
 * @param {string} selector - The CSS selector
 * @param {Element|Document} [parent=document] - The parent element to search within
 * @returns {NodeList} List of matching elements
 */
export function $$(selector, parent = document) {
  return parent.querySelectorAll(selector);
}

/**
 * Find the first element matching a selector within a parent
 * @param {string} selector - The CSS selector
 * @param {Element|Document} [parent=document] - The parent element to search within
 * @returns {Element|null} The first matching element or null
 */
export function $(selector, parent = document) {
  return parent.querySelector(selector);
}

/**
 * Show an element by removing the 'hidden' class and setting display style
 * @param {Element} element - The element to show
 * @param {string} [display='block'] - The display value to use
 */
export function showElement(element, display = 'block') {
  if (element) {
    removeClass(element, 'hidden');
    element.style.display = display;
  }
}

/**
 * Hide an element by adding the 'hidden' class
 * @param {Element} element - The element to hide
 */
export function hideElement(element) {
  if (element) {
    addClass(element, 'hidden');
    element.style.display = 'none';
  }
}

/**
 * Toggle element visibility
 * @param {Element} element - The element to toggle
 * @param {boolean} [force] - Force show or hide
 */
export function toggleElement(element, force) {
  if (!element) return;
  
  const isHidden = element.style.display === 'none' || hasClass(element, 'hidden');
  const shouldShow = force !== undefined ? force : isHidden;
  
  if (shouldShow) {
    showElement(element);
  } else {
    hideElement(element);
  }
}

/**
 * Set multiple attributes on an element
 * @param {Element} element - The target element
 * @param {Object} attributes - Object of attribute names and values
 */
export function setAttributes(element, attributes) {
  if (!element) return;
  
  Object.entries(attributes).forEach(([key, value]) => {
    if (value === null || value === false) {
      element.removeAttribute(key);
    } else {
      element.setAttribute(key, value === true ? '' : value);
    }
  });
}

/**
 * Get the current scroll position
 * @returns {Object} Object with x and y scroll positions
 */
export function getScrollPosition() {
  return {
    x: window.pageXOffset || document.documentElement.scrollLeft,
    y: window.pageYOffset || document.documentElement.scrollTop
  };
}

/**
 * Scroll to a specific position with smooth animation
 * @param {number} x - The x-coordinate to scroll to
 * @param {number} y - The y-coordinate to scroll to
 * @param {Object} [options] - Scroll options
 * @param {string} [options.behavior='smooth'] - Scroll behavior
 */
export function scrollTo(x, y, { behavior = 'smooth' } = {}) {
  window.scrollTo({
    left: x,
    top: y,
    behavior
  });
}

/**
 * Debounce a function
 * @param {Function} func - The function to debounce
 * @param {number} wait - The delay in milliseconds
 * @returns {Function} The debounced function
 */
export function debounce(func, wait = 100) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * Throttle a function
 * @param {Function} func - The function to throttle
 * @param {number} limit - The time limit in milliseconds
 * @returns {Function} The throttled function
 */
export function throttle(func, limit = 100) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Get the position of an element relative to the document
 * @param {Element} element - The target element
 * @returns {Object} Object with top, right, bottom, left, width, and height
 */
export function getPosition(element) {
  if (!element) return null;
  
  const rect = element.getBoundingClientRect();
  return {
    top: rect.top + window.pageYOffset,
    right: rect.right + window.pageXOffset,
    bottom: rect.bottom + window.pageYOffset,
    left: rect.left + window.pageXOffset,
    width: rect.width,
    height: rect.height
  };
}

/**
 * Check if an element is in the viewport
 * @param {Element} element - The element to check
 * @returns {boolean} True if the element is in the viewport
 */
export function isInViewport(element) {
  if (!element) return false;
  
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Create a new DOM element
 * @param {string} tag - The tag name of the element
 * @param {Object} [options] - Element options
 * @param {string|string[]} [options.className] - Class name(s) to add
 * @param {Object} [options.attributes] - Attributes to set
 * @param {string} [options.text] - Text content
 * @param {string} [options.html] - HTML content
 * @param {Element[]} [options.children] - Child elements to append
 * @returns {Element} The created element
 */
export function createElement(tag, {
  className = '',
  attributes = {},
  text = '',
  html = '',
  children = []
} = {}) {
  const element = document.createElement(tag);
  
  if (className) {
    const classes = Array.isArray(className) ? className : className.split(' ');
    element.classList.add(...classes.filter(Boolean));
  }
  
  setAttributes(element, attributes);
  
  if (text) {
    element.textContent = text;
  } else if (html) {
    element.innerHTML = html;
  }
  
  children.forEach(child => {
    if (child) element.appendChild(child);
  });
  
  return element;
}
