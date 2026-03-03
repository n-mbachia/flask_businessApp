/**
 * Main application entry point
 * Initializes components and sets up global event listeners
 */

// Import HTTP utilities
import http from './utils/http.js';
import { local as storage } from './utils/storage.js';

// Add CSRF token interceptor
http.addRequestInterceptor(async (config) => {
  // Skip for GET/HEAD/OPTIONS or when explicitly disabled
  if (['GET', 'HEAD', 'OPTIONS'].includes(config.method?.toUpperCase()) || config.skipCsrf) {
    return config;
  }

  // Get CSRF token from meta tag
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  
  if (csrfToken) {
    // Add CSRF token to headers
    config.headers = {
      ...config.headers,
      'X-CSRFToken': csrfToken
    };
  }
  
  return config;
});

// Global app state
window.AppState = {
  currentPage: null,
  isLoading: false,
  user: null,
  theme: localStorage.getItem('theme') || 'light'
};

// Global error handler
window.AppErrorHandler = {
  handle(error, context = 'Unknown') {
    console.error(`[${context}] Error:`, error);
    
    // Show user-friendly error message
    const message = error?.message || 'An unexpected error occurred';
    this.showNotification(message, 'danger');
    
    // Log to server if available
    if (window.AppState.user) {
      this.logError(error, context);
    }
  },
  
  showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.setAttribute('role', 'alert');
    notification.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    let container = document.getElementById('notifications-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'notifications-container';
      container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
      `;
      document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Auto-dismiss
    setTimeout(() => {
      if (notification.parentNode) {
        notification.remove();
      }
    }, duration);
  },
  
  async logError(error, context) {
    try {
      await http.post('/api/v1/errors/log', {
        error: {
          message: error.message,
          stack: error.stack,
          context: context,
          url: window.location.href,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString()
        }
      }, { skipCsrf: true });
    } catch (e) {
      console.warn('Failed to log error to server:', e);
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  try {
    // Initialize components
    initializeComponents();
    
    // Set up global event listeners
    setupGlobalListeners();
    
    // Initialize page-specific scripts
    const page = document.body.dataset.page;
    if (page) {
      loadPageScript(page);
    }
    
    // Initialize theme
    initializeTheme();
    
    console.log('App initialized successfully');
  } catch (error) {
    AppErrorHandler.handle(error, 'App Initialization');
  }
});

/**
 * Initialize all app components
 */
function initializeComponents() {
  initTooltips();
  initModals();
  initDropdowns();
  initNavigation();
  initForms();
  initLazyLoading();
}

/**
 * Initialize navigation component
 * Handles mobile menu, dropdowns, and active states
 */
function initNavigation() {
  // Close mobile menu when clicking on a nav link
  const navLinks = document.querySelectorAll('.nav-link:not(.dropdown-toggle)');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      const navbarCollapse = document.querySelector('.navbar-collapse');
      if (navbarCollapse?.classList.contains('show')) {
        const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
        if (bsCollapse) {
          bsCollapse.hide();
        }
      }
    });
  });

  // Handle dropdown hover on desktop
  const dropdowns = document.querySelectorAll('.dropdown');
  const mediaQuery = window.matchMedia('(min-width: 992px)');
  
  function handleDropdownHover(e) {
    if (mediaQuery.matches) {
      const isEntering = e.type === 'mouseenter';
      const dropdown = e.currentTarget;
      
      if (isEntering) {
        dropdown.classList.add('show');
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
        if (menu) menu.classList.add('show');
      } else {
        dropdown.classList.remove('show');
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        if (menu) menu.classList.remove('show');
      }
    }
  }

  // Set up hover events for dropdowns
  dropdowns.forEach(dropdown => {
    dropdown.addEventListener('mouseenter', handleDropdownHover);
    dropdown.addEventListener('mouseleave', handleDropdownHover);
  });

  // Update active states based on URL
  updateActiveNavItems();
  
  // Re-run when navigating with browser back/forward
  window.addEventListener('popstate', updateActiveNavItems);
}

/**
 * Update active navigation items based on current URL
 */
function updateActiveNavItems() {
  const currentPath = window.location.pathname;
  
  // Clear all active states first
  document.querySelectorAll('.nav-link, .dropdown-toggle').forEach(link => {
    link.classList.remove('active');
    link.removeAttribute('aria-current');
  });
  
  // Update main nav items
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href !== '#' && currentPath.startsWith(href)) {
      link.classList.add('active');
      link.setAttribute('aria-current', 'page');
      
      // If this is a dropdown item, also activate the parent dropdown
      const dropdown = link.closest('.dropdown-menu');
      if (dropdown) {
        const dropdownToggle = dropdown.previousElementSibling;
        if (dropdownToggle?.classList.contains('dropdown-toggle')) {
          dropdownToggle.classList.add('active');
        }
      }
    }
  });
}

/**
 * Initialize all tooltips on the page
 */
function initTooltips() {
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl, {
      trigger: 'hover focus',
      delay: { show: 300, hide: 100 },
      placement: 'top'
    });
  });
}

/**
 * Initialize modal dialogs
 */
function initModals() {
  const modals = document.querySelectorAll('.modal');
  modals.forEach(modal => {
    modal.addEventListener('hidden.bs.modal', function () {
      // Clear form when modal is hidden
      const form = this.querySelector('form');
      if (form) {
        form.reset();
        // Clear any validation errors
        form.querySelectorAll('.is-invalid').forEach(el => {
          el.classList.remove('is-invalid');
        });
        form.querySelectorAll('.invalid-feedback').forEach(el => {
          el.remove();
        });
      }
    });
    
    // Focus management
    modal.addEventListener('shown.bs.modal', function () {
      const firstInput = this.querySelector('input:not([type="hidden"]), textarea, select');
      if (firstInput) {
        firstInput.focus();
      }
    });
  });
}

/**
 * Initialize dropdown menus
 */
function initDropdowns() {
  // Prevent dropdown from closing when clicking inside
  document.querySelectorAll('.dropdown-menu').forEach(menu => {
    menu.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  });
}

/**
 * Initialize form enhancements
 */
function initForms() {
  // Auto-resize textareas
  document.querySelectorAll('textarea[data-auto-resize]').forEach(textarea => {
    const resize = () => {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    };
    
    textarea.addEventListener('input', resize);
    resize(); // Initial resize
  });
  
  // Form validation enhancements
  document.querySelectorAll('form[data-validate]').forEach(form => {
    form.addEventListener('submit', function(e) {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
        
        // Show validation errors
        form.querySelectorAll(':invalid').forEach(field => {
          field.classList.add('is-invalid');
          
          let feedback = field.parentNode.querySelector('.invalid-feedback');
          if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
          }
          feedback.textContent = field.validationMessage;
        });
        
        // Focus first invalid field
        form.querySelector(':invalid')?.focus();
      }
    });
  });
}

/**
 * Initialize lazy loading for images
 */
function initLazyLoading() {
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.classList.remove('lazy');
          observer.unobserve(img);
        }
      });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });
  }
}

/**
 * Initialize theme system
 */
function initializeTheme() {
  const theme = window.AppState.theme;
  document.documentElement.setAttribute('data-theme', theme);
  
  // Theme toggle button
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
    updateThemeIcon(theme);
  }
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
  const currentTheme = window.AppState.theme;
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  
  window.AppState.theme = newTheme;
  localStorage.setItem('theme', newTheme);
  document.documentElement.setAttribute('data-theme', newTheme);
  updateThemeIcon(newTheme);
}

/**
 * Update theme toggle icon
 */
function updateThemeIcon(theme) {
  const icon = document.querySelector('#theme-toggle i');
  if (icon) {
    icon.className = theme === 'light' ? 'bi bi-moon-stars' : 'bi bi-sun';
  }
}

/**
 * Set up global event listeners
 */
function setupGlobalListeners() {
  // Handle form submissions with confirmation
  document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.hasAttribute('data-confirm')) {
      const message = form.getAttribute('data-confirm');
      if (!confirm(message)) {
        e.preventDefault();
        return false;
      }
    }
  });

  // Handle click events on elements with data-method
  document.addEventListener('click', function(e) {
    const el = e.target.closest('[data-method]');
    if (el) {
      const method = el.getAttribute('data-method');
      if (method === 'delete') {
        e.preventDefault();
        const message = el.getAttribute('data-confirm') || 'Are you sure you want to delete this item?';
        if (confirm(message)) {
          submitWithMethod(el.href || el.getAttribute('data-url'), 'DELETE');
        }
      }
    }
  });
  
  // Handle keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for quick search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const searchInput = document.querySelector('#search-input, [data-search]');
      if (searchInput) {
        searchInput.focus();
      }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
      const openModal = document.querySelector('.modal.show');
      if (openModal) {
        bootstrap.Modal.getInstance(openModal)?.hide();
      }
    }
  });
  
  // Handle online/offline status
  window.addEventListener('online', () => {
    AppErrorHandler.showNotification('Connection restored', 'success', 3000);
  });
  
  window.addEventListener('offline', () => {
    AppErrorHandler.showNotification('Connection lost. Some features may be unavailable.', 'warning', 5000);
  });
}

/**
 * Submit a form with a specific HTTP method
 * @param {string} url - The URL to submit to
 * @param {string} method - The HTTP method to use
 */
function submitWithMethod(url, method) {
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = url;
  
  // Add method override for non-POST methods
  if (method !== 'POST') {
    const methodInput = document.createElement('input');
    methodInput.type = 'hidden';
    methodInput.name = '_method';
    methodInput.value = method;
    form.appendChild(methodInput);
  }
  
  // Add CSRF token
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  if (csrfToken) {
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = '_csrf_token';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
  }
  
  document.body.appendChild(form);
  form.submit();
}

/**
 * Dynamically load a page-specific script
 * @param {string} page - The name of the page to load
 */
async function loadPageScript(page) {
  try {
    // Update current page state
    window.AppState.currentPage = page;
    
    // Load page-specific module
    const module = await import(`./pages/${page}.js`);
    
    if (module && typeof module.default === 'function') {
      module.default();
    }
    
    // Load analytics script if on analytics page
    if (page === 'analytics') {
      await import('./analytics-enhanced.js');
    }
    
  } catch (error) {
    console.warn(`Page script for ${page} not found or failed to load:`, error);
    
    // Fallback to basic analytics for analytics page
    if (page === 'analytics') {
      try {
        await import('./analytics.js');
      } catch (fallbackError) {
        console.warn('Analytics fallback script also failed:', fallbackError);
      }
    }
  }
}

/**
 * Debounce function for performance optimization
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function for performance optimization
 */
function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Export functions and utilities for global access
window.App = {
  submitWithMethod,
  loadPageScript,
  debounce,
  throttle,
  state: window.AppState,
  error: window.AppErrorHandler
};

// Make functions available globally for debugging and legacy support
window.initNavigation = initNavigation;
window.updateActiveNavItems = updateActiveNavItems;
