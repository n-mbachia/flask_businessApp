/**
 * Formatters utility
 * Provides functions for formatting various data types
 */

/**
 * Format a number with commas as thousand separators
 * @param {number} number - The number to format
 * @param {number} [decimals=0] - Number of decimal places
 * @returns {string} Formatted number string
 */
export const formatNumber = (number, decimals = 0) => {
  if (number === null || number === undefined) return 'N/A';
  
  // Handle both string and number inputs
  const num = typeof number === 'string' ? parseFloat(number) : number;
  
  if (isNaN(num)) return 'N/A';
  
  return num.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};

/**
 * Format a number as currency
 * @param {number} amount - The amount to format
 * @param {string} [currency='USD'] - Currency code (e.g., 'USD', 'EUR')
 * @param {number} [decimals=2] - Number of decimal places
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, currency = 'USD', decimals = 2) => {
  if (amount === null || amount === undefined) return 'N/A';
  
  // Handle both string and number inputs
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  
  if (isNaN(num)) return 'N/A';
  
  return num.toLocaleString(undefined, {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};

/**
 * Format a date string or timestamp
 * @param {string|number|Date} date - Date to format (string, timestamp, or Date object)
 * @param {string} [locale='en-US'] - Locale string
 * @param {Object} [options] - Intl.DateTimeFormat options
 * @returns {string} Formatted date string
 */
export const formatDate = (date, locale = 'en-US', options = {}) => {
  if (!date) return 'N/A';
  
  try {
    const dateObj = date instanceof Date ? date : new Date(date);
    
    // Default options if none provided
    const defaultOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options
    };
    
    return new Intl.DateTimeFormat(locale, defaultOptions).format(dateObj);
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Invalid date';
  }
};

/**
 * Format a duration in seconds to a human-readable format (e.g., '2h 30m')
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration
 */
export const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined) return 'N/A';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  
  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0 || hours > 0) parts.push(`${minutes}m`);
  if (seconds < 60) parts.push(`${remainingSeconds}s`);
  
  return parts.join(' ') || '0s';
};

/**
 * Truncate text to a specified length and add ellipsis if needed
 * @param {string} text - The text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated text with ellipsis if needed
 */
export const truncateText = (text, maxLength = 50) => {
  if (typeof text !== 'string') return '';
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};

/**
 * Format file size in bytes to a human-readable format (e.g., '1.5 MB')
 * @param {number} bytes - File size in bytes
 * @param {number} [decimals=2] - Number of decimal places
 * @returns {string} Formatted file size
 */
export const formatFileSize = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

/**
 * Format a percentage value
 * @param {number} value - The value to format as a percentage (0-1 or 0-100)
 * @param {boolean} [isDecimal=true] - Whether the input is a decimal (0-1) or not (0-100)
 * @param {number} [decimals=1] - Number of decimal places
 * @returns {string} Formatted percentage string
 */
export const formatPercentage = (value, isDecimal = true, decimals = 1) => {
  if (value === null || value === undefined) return 'N/A';
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return 'N/A';
  
  const percentage = isDecimal ? num * 100 : num;
  
  return `${percentage.toFixed(decimals)}%`;
};

/**
 * Format a phone number into a standard format
 * @param {string} phoneNumber - The phone number to format
 * @returns {string} Formatted phone number
 */
export const formatPhoneNumber = (phoneNumber) => {
  if (!phoneNumber) return 'N/A';
  
  // Remove all non-digit characters
  const cleaned = `${phoneNumber}`.replace(/\D/g, '');
  
  // Check if the number has an international code
  if (cleaned.length > 10) {
    return `+${cleaned.substring(0, cleaned.length - 10)} (${cleaned.substring(cleaned.length - 10, cleaned.length - 7)}) ${cleaned.substring(cleaned.length - 7, cleaned.length - 4)}-${cleaned.substring(cleaned.length - 4)}`;
  }
  
  // Format as US number
  const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);
  if (match) {
    return `(${match[1]}) ${match[2]}-${match[3]}`;
  }
  
  // Return original if format doesn't match
  return phoneNumber;
};
