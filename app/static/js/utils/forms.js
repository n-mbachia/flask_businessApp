/**
 * Forms Utility
 * Provides functions for form handling, validation, and submission
 */

import { debounce } from './dom';
import http from './http';

// Default validation rules
const DEFAULT_RULES = {
  required: {
    validate: (value) => {
      if (value === undefined || value === null) return false;
      if (typeof value === 'string') return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      if (typeof value === 'object' && value !== null) {
        return Object.keys(value).length > 0;
      }
      return true;
    },
    message: 'This field is required',
  },
  email: {
    validate: (value) => {
      if (!value) return true;
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return re.test(String(value).toLowerCase());
    },
    message: 'Please enter a valid email address',
  },
  minLength: {
    validate: (value, length) => {
      if (!value) return true;
      return String(value).length >= length;
    },
    message: (length) => `Must be at least ${length} characters`,
  },
  maxLength: {
    validate: (value, length) => {
      if (!value) return true;
      return String(value).length <= length;
    },
    message: (length) => `Cannot exceed ${length} characters`,
  },
  pattern: {
    validate: (value, pattern) => {
      if (!value) return true;
      return new RegExp(pattern).test(value);
    },
    message: 'Invalid format',
  },
};

/**
 * Form validation class
 */
class FormValidator {
  constructor(form, options = {}) {
    this.form = form;
    this.options = {
      errorClass: 'is-invalid',
      validClass: 'is-valid',
      errorElement: 'div',
      errorClassElement: 'invalid-feedback',
      ...options,
    };
    this.fields = new Map();
    this.errors = new Map();
    this.initialize();
  }

  initialize() {
    // Initialize form fields and event listeners
    this.form.querySelectorAll('[data-validate]').forEach(field => {
      const fieldName = field.name || field.id;
      if (!fieldName) return;

      const rules = this.parseValidationRules(field);
      if (rules.length === 0) return;

      this.fields.set(fieldName, { element: field, rules });
      
      field.addEventListener('blur', () => this.validateField(fieldName));
      field.addEventListener('input', debounce(() => {
        if (field.value) this.validateField(fieldName);
      }, 300));
    });

    this.form.addEventListener('submit', this.handleSubmit.bind(this));
  }

  parseValidationRules(element) {
    const rules = [];
    const validateAttr = element.getAttribute('data-validate');
    if (!validateAttr) return rules;

    validateAttr.split(/[\s|]+/).forEach(ruleString => {
      const [ruleName, param] = ruleString.split(':');
      if (DEFAULT_RULES[ruleName]) {
        rules.push({
          name: ruleName,
          param: param ? this.parseRuleParam(param) : null,
          ...DEFAULT_RULES[ruleName],
        });
      }
    });

    return rules;
  }

  parseRuleParam(param) {
    try {
      return JSON.parse(param);
    } catch (e) {
      return param;
    }
  }

  validateField(fieldName) {
    const field = this.fields.get(fieldName);
    if (!field) return true;

    const { element, rules } = field;
    const value = this.getValue(element);
    let isValid = true;

    this.clearFieldError(fieldName);

    for (const rule of rules) {
      if (!rule.validate(value, rule.param, this.getFormData())) {
        isValid = false;
        const message = typeof rule.message === 'function' 
          ? rule.message(rule.param) 
          : rule.message;
        this.addFieldError(fieldName, message);
        break;
      }
    }

    if (isValid) {
      this.markFieldAsValid(fieldName);
    }

    return isValid;
  }

  validateForm() {
    let isValid = true;
    for (const fieldName of this.fields.keys()) {
      if (!this.validateField(fieldName)) {
        isValid = false;
      }
    }
    return isValid;
  }

  getValue(element) {
    const type = element.type?.toLowerCase() || '';
    
    if (type === 'checkbox') return element.checked;
    if (type === 'radio') {
      const checked = this.form.querySelector(`[name="${element.name}"]:checked`);
      return checked ? checked.value : '';
    }
    if (element.multiple) {
      return Array.from(element.selectedOptions).map(opt => opt.value);
    }
    return element.value;
  }

  getFormData() {
    const formData = {};
    this.fields.forEach((_, name) => {
      formData[name] = this.getValue(this.fields.get(name).element);
    });
    return formData;
  }

  addFieldError(fieldName, message) {
    const field = this.fields.get(fieldName);
    if (!field) return;

    const { element } = field;
    element.classList.add(this.options.errorClass);
    element.classList.remove(this.options.validClass);

    let errorElement = field.errorElement;
    if (!errorElement) {
      errorElement = document.createElement(this.options.errorElement);
      errorElement.className = this.options.errorClassElement;
      field.errorElement = errorElement;
      element.after(errorElement);
    }

    errorElement.textContent = message;
    errorElement.style.display = 'block';
    this.errors.set(fieldName, message);
  }

  clearFieldError(fieldName) {
    const field = this.fields.get(fieldName);
    if (!field) return;

    const { element, errorElement } = field;
    element.classList.remove(this.options.errorClass);
    
    if (errorElement) {
      errorElement.style.display = 'none';
      errorElement.textContent = '';
    }
    
    this.errors.delete(fieldName);
  }

  markFieldAsValid(fieldName) {
    const field = this.fields.get(fieldName);
    if (!field) return;

    const { element } = field;
    element.classList.add(this.options.validClass);
    element.classList.remove(this.options.errorClass);

    if (field.errorElement) {
      field.errorElement.style.display = 'none';
    }
  }

  handleSubmit(event) {
    event?.preventDefault();
    
    if (this.validateForm()) {
      if (this.form.getAttribute('data-ajax') === 'true') {
        this.submitFormAjax();
      } else {
        this.form.submit();
      }
    } else {
      const firstError = this.form.querySelector(`.${this.options.errorClass}`);
      firstError?.focus();
    }
  }

  async submitFormAjax() {
    const formData = new FormData(this.form);
    
    try {
      const response = await http.request(this.form.action, {
        method: this.form.method || 'POST',
        body: formData,
      });
      
      this.form.dispatchEvent(new CustomEvent('form:success', { 
        detail: { response },
        bubbles: true,
      }));
      
    } catch (error) {
      this.form.dispatchEvent(new CustomEvent('form:error', { 
        detail: { error },
        bubbles: true,
      }));
    }
  }

  destroy() {
    this.form.removeEventListener('submit', this.handleSubmit);
    this.fields.forEach(({ element }) => {
      element.removeEventListener('blur', this.validateField);
      element.removeEventListener('input', this.validateField);
    });
    this.fields.clear();
    this.errors.clear();
  }
}

// Helper functions
export function serializeForm(form) {
  return new URLSearchParams(new FormData(form)).toString();
}

export function formToObject(form) {
  const formData = new FormData(form);
  const result = {};
  
  for (const [key, value] of formData.entries()) {
    if (Object.prototype.hasOwnProperty.call(result, key)) {
      if (!Array.isArray(result[key])) {
        result[key] = [result[key]];
      }
      result[key].push(value);
    } else {
      result[key] = value;
    }
  }
  
  return result;
}

export function initForms(selector = 'form[data-validate]', options = {}) {
  const forms = document.querySelectorAll(selector);
  const validators = new Map();
  
  forms.forEach(form => {
    validators.set(form, new FormValidator(form, options));
  });
  
  return validators;
}

export default {
  FormValidator,
  serializeForm,
  formToObject,
  initForms,
};
