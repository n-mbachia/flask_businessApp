/**
 * UI Utility
 * Provides functions for common UI components and interactions
 */

import { debounce } from './dom';

/**
 * Modal component
 */
class Modal {
  constructor(element, options = {}) {
    this.element = typeof element === 'string' 
      ? document.querySelector(element) 
      : element;
    
    this.options = {
      backdrop: true,
      keyboard: true,
      focus: true,
      backdropClass: 'modal-backdrop',
      showClass: 'show',
      ...options,
    };
    
    this.isOpen = false;
    this.backdrop = null;
    
    // Bind methods
    this.show = this.show.bind(this);
    this.hide = this.hide.bind(this);
    this.toggle = this.toggle.bind(this);
    this.handleKeydown = this.handleKeydown.bind(this);
    this.handleClick = this.handleClick.bind(this);
    
    // Initialize
    this.init();
  }
  
  init() {
    // Add event listeners to toggle buttons
    const toggleButtons = document.querySelectorAll(`[data-toggle="modal"][data-target="#${this.element.id}"]`);
    toggleButtons.forEach(button => {
      button.addEventListener('click', this.toggle);
    });
    
    // Add close button event
    const closeButtons = this.element.querySelectorAll('[data-dismiss="modal"]');
    closeButtons.forEach(button => {
      button.addEventListener('click', this.hide);
    });
  }
  
  show() {
    if (this.isOpen) return;
    
    // Create and show backdrop
    if (this.options.backdrop) {
      this.createBackdrop();
    }
    
    // Show modal
    this.element.style.display = 'block';
    this.element.setAttribute('aria-hidden', 'false');
    this.element.setAttribute('aria-modal', 'true');
    document.body.classList.add('modal-open');
    
    // Add show class with a small delay for transition
    setTimeout(() => {
      this.element.classList.add(this.options.showClass);
    }, 10);
    
    // Focus on first focusable element
    if (this.options.focus) {
      const focusable = this.element.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable.length) {
        focusable[0].focus();
      }
    }
    
    // Add event listeners
    document.addEventListener('keydown', this.handleKeydown);
    this.element.addEventListener('click', this.handleClick);
    
    // Update state
    this.isOpen = true;
    
    // Trigger shown event
    this.element.dispatchEvent(new Event('shown.modal'));
  }
  
  hide() {
    if (!this.isOpen) return;
    
    // Hide modal
    this.element.classList.remove(this.options.showClass);
    
    // Remove modal after transition
    const handleTransitionEnd = () => {
      this.element.style.display = 'none';
      this.element.removeEventListener('transitionend', handleTransitionEnd);
      
      // Remove backdrop
      this.removeBackdrop();
      
      // Update state
      this.isOpen = false;
      
      // Remove event listeners
      document.removeEventListener('keydown', this.handleKeydown);
      this.element.removeEventListener('click', this.handleClick);
      
      // Trigger hidden event
      this.element.dispatchEvent(new Event('hidden.modal'));
    };
    
    this.element.addEventListener('transitionend', handleTransitionEnd);
  }
  
  toggle() {
    this.isOpen ? this.hide() : this.show();
  }
  
  createBackdrop() {
    this.backdrop = document.createElement('div');
    this.backdrop.className = this.options.backdropClass;
    document.body.appendChild(this.backdrop);
    
    // Add show class with a small delay for transition
    setTimeout(() => {
      this.backdrop.classList.add(this.options.showClass);
    }, 10);
    
    // Close modal when clicking on backdrop
    this.backdrop.addEventListener('click', () => {
      this.hide();
    });
  }
  
  removeBackdrop() {
    if (!this.backdrop) return;
    
    this.backdrop.classList.remove(this.options.showClass);
    
    // Remove backdrop after transition
    const handleTransitionEnd = () => {
      if (this.backdrop && this.backdrop.parentNode) {
        this.backdrop.parentNode.removeChild(this.backdrop);
        this.backdrop = null;
      }
    };
    
    this.backdrop.addEventListener('transitionend', handleTransitionEnd);
  }
  
  handleKeydown(event) {
    // Close on ESC key
    if (event.key === 'Escape' && this.options.keyboard) {
      this.hide();
    }
    
    // Trap focus inside modal
    if (event.key === 'Tab' && this.isOpen) {
      const focusable = this.element.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      const firstFocusable = focusable[0];
      const lastFocusable = focusable[focusable.length - 1];
      
      if (event.shiftKey) {
        if (document.activeElement === firstFocusable) {
          event.preventDefault();
          lastFocusable.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          event.preventDefault();
          firstFocusable.focus();
        }
      }
    }
  }
  
  handleClick(event) {
    // Close when clicking on close button or outside modal content
    if (event.target === this.element || event.target.closest('[data-dismiss="modal"]')) {
      this.hide();
    }
  }
  
  dispose() {
    // Remove event listeners
    const toggleButtons = document.querySelectorAll(`[data-toggle="modal"][data-target="#${this.element.id}"]`);
    toggleButtons.forEach(button => {
      button.removeEventListener('click', this.toggle);
    });
    
    const closeButtons = this.element.querySelectorAll('[data-dismiss="modal"]');
    closeButtons.forEach(button => {
      button.removeEventListener('click', this.hide);
    });
    
    // Hide modal if it's open
    if (this.isOpen) {
      this.hide();
    }
    
    // Remove backdrop if it exists
    this.removeBackdrop();
    
    // Reset properties
    this.element = null;
    this.options = null;
    this.isOpen = false;
  }
}

/**
 * Toast component
 */
class Toast {
  constructor(element, options = {}) {
    this.element = typeof element === 'string' 
      ? document.querySelector(element) 
      : element;
    
    this.options = {
      autohide: true,
      delay: 5000,
      animation: true,
      animationClass: 'fade',
      showClass: 'show',
      ...options,
    };
    
    this.timeout = null;
    this.isShown = false;
    
    // Bind methods
    this.show = this.show.bind(this);
    this.hide = this.hide.bind(this);
    
    // Initialize
    this.init();
  }
  
  init() {
    // Add close button event
    const closeButton = this.element.querySelector('[data-dismiss="toast"]');
    if (closeButton) {
      closeButton.addEventListener('click', this.hide);
    }
  }
  
  show() {
    if (this.isShown) return;
    
    // Show toast
    this.element.style.display = 'block';
    
    // Trigger show event
    const showEvent = new Event('show.toast');
    this.element.dispatchEvent(showEvent);
    
    // Add show class with a small delay for transition
    setTimeout(() => {
      this.element.classList.add(this.options.showClass);
      
      // Auto-hide if enabled
      if (this.options.autohide) {
        this.timeout = setTimeout(() => {
          this.hide();
        }, this.options.delay);
      }
      
      // Update state
      this.isShown = true;
      
      // Trigger shown event
      this.element.dispatchEvent(new Event('shown.toast'));
    }, 10);
  }
  
  hide() {
    if (!this.isShown) return;
    
    // Clear timeout if exists
    if (this.timeout) {
      clearTimeout(this.timeout);
      this.timeout = null;
    }
    
    // Trigger hide event
    const hideEvent = new Event('hide.toast');
    this.element.dispatchEvent(hideEvent);
    
    // Hide toast
    this.element.classList.remove(this.options.showClass);
    
    // Remove toast after transition
    const handleTransitionEnd = () => {
      this.element.style.display = 'none';
      this.element.removeEventListener('transitionend', handleTransitionEnd);
      
      // Update state
      this.isShown = false;
      
      // Trigger hidden event
      this.element.dispatchEvent(new Event('hidden.toast'));
    };
    
    this.element.addEventListener('transitionend', handleTransitionEnd);
  }
  
  dispose() {
    // Hide toast if it's shown
    if (this.isShown) {
      this.hide();
    }
    
    // Remove event listeners
    const closeButton = this.element.querySelector('[data-dismiss="toast"]');
    if (closeButton) {
      closeButton.removeEventListener('click', this.hide);
    }
    
    // Reset properties
    this.element = null;
    this.options = null;
    this.isShown = false;
  }
}

/**
 * Tab component
 */
class Tab {
  constructor(element, options = {}) {
    this.element = typeof element === 'string' 
      ? document.querySelector(element) 
      : element;
    
    this.options = {
      activeClass: 'active',
      showClass: 'show',
      ...options,
    };
    
    // Find tab links and panes
    this.tabList = this.element.querySelector('[role="tablist"]');
    this.tabLinks = Array.from(this.element.querySelectorAll('[role="tab"]'));
    this.tabPanes = Array.from(this.element.querySelectorAll('[role="tabpanel"]'));
    
    // Bind methods
    this.show = this.show.bind(this);
    this.handleClick = this.handleClick.bind(this);
    this.handleKeydown = this.handleKeydown.bind(this);
    
    // Initialize
    this.init();
  }
  
  init() {
    // Add event listeners
    this.tabLinks.forEach(tabLink => {
      tabLink.addEventListener('click', this.handleClick);
      tabLink.addEventListener('keydown', this.handleKeydown);
    });
    
    // Show first tab by default if none is active
    const activeTab = this.element.querySelector(`[role="tab"].${this.options.activeClass}`);
    if (!activeTab && this.tabLinks.length > 0) {
      this.show(this.tabLinks[0]);
    }
  }
  
  show(tabLink) {
    // Find the tab link if a selector or index was passed
    if (typeof tabLink === 'string') {
      tabLink = this.element.querySelector(`[role="tab"][href="${tabLink}"]`);
    } else if (typeof tabLink === 'number') {
      tabLink = this.tabLinks[tabLink];
    }
    
    if (!tabLink || tabLink.getAttribute('aria-disabled') === 'true') {
      return;
    }
    
    // Find the target tab panel
    const targetId = tabLink.getAttribute('href') || tabLink.getAttribute('data-target');
    const targetPane = this.element.querySelector(targetId);
    
    if (!targetPane) return;
    
    // Find the currently active tab and pane
    const currentTab = this.element.querySelector(`[role="tab"].${this.options.activeClass}`);
    const currentPane = currentTab 
      ? this.element.querySelector(currentTab.getAttribute('href') || currentTab.getAttribute('data-target'))
      : null;
    
    // Trigger hide event on current tab
    if (currentTab) {
      const hideEvent = new Event('hide.tab');
      currentTab.dispatchEvent(hideEvent);
      
      // Stop if hide was prevented
      if (hideEvent.defaultPrevented) {
        return;
      }
      
      // Hide current tab and pane
      currentTab.classList.remove(this.options.activeClass);
      currentTab.setAttribute('aria-selected', 'false');
      
      if (currentPane) {
        currentPane.classList.remove(this.options.showClass, this.options.activeClass);
        currentPane.setAttribute('aria-hidden', 'true');
      }
      
      // Trigger hidden event
      const hiddenEvent = new Event('hidden.tab');
      currentTab.dispatchEvent(hiddenEvent);
    }
    
    // Show new tab and pane
    tabLink.classList.add(this.options.activeClass);
    tabLink.setAttribute('aria-selected', 'true');
    tabLink.focus();
    
    targetPane.classList.add(this.options.showClass, this.options.activeClass);
    targetPane.setAttribute('aria-hidden', 'false');
    
    // Trigger shown event
    const shownEvent = new Event('shown.tab');
    tabLink.dispatchEvent(shownEvent);
  }
  
  handleClick(event) {
    event.preventDefault();
    this.show(event.currentTarget);
  }
  
  handleKeydown(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      return;
    }
    
    event.preventDefault();
    
    const currentIndex = this.tabLinks.indexOf(event.currentTarget);
    let newIndex = currentIndex;
    
    switch (event.key) {
      case 'ArrowLeft':
        newIndex = currentIndex > 0 ? currentIndex - 1 : this.tabLinks.length - 1;
        break;
      case 'ArrowRight':
        newIndex = currentIndex < this.tabLinks.length - 1 ? currentIndex + 1 : 0;
        break;
      case 'Home':
        newIndex = 0;
        break;
      case 'End':
        newIndex = this.tabLinks.length - 1;
        break;
    }
    
    if (newIndex !== currentIndex) {
      this.show(newIndex);
    }
  }
  
  dispose() {
    // Remove event listeners
    this.tabLinks.forEach(tabLink => {
      tabLink.removeEventListener('click', this.handleClick);
      tabLink.removeEventListener('keydown', this.handleKeydown);
    });
    
    // Reset properties
    this.element = null;
    this.options = null;
    this.tabList = null;
    this.tabLinks = [];
    this.tabPanes = [];
  }
}

// Export components
export { Modal, Toast, Tab };

// Initialize components automatically when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Initialize modals
  const modals = document.querySelectorAll('.modal');
  modals.forEach(modal => {
    new Modal(modal);
  });
  
  // Initialize toasts
  const toasts = document.querySelectorAll('.toast[data-autohide!="false"]');
  toasts.forEach(toast => {
    const instance = new Toast(toast, {
      autohide: toast.dataset.autohide !== 'false',
      delay: parseInt(toast.dataset.delay, 10) || 5000,
    });
    
    // Show toast if it has the 'show' class
    if (toast.classList.contains('show')) {
      instance.show();
    }
  });
  
  // Initialize tabs
  const tabPanes = document.querySelectorAll('[role="tabpanel"]');
  const tabContainers = new Set(
    Array.from(tabPanes).map(pane => 
      pane.closest('[data-toggle="tabs"]') || pane.closest('.tab-content')
    )
  );
  
  tabContainers.forEach(container => {
    if (container) {
      new Tab(container);
    }
  });
});

export default {
  Modal,
  Toast,
  Tab,
};
