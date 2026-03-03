/**
 * Products API Client
 * Handles all product-related API interactions
 */

import api from '../utils/api';

const PRODUCTS_ENDPOINT = '/api/products';

/**
 * Fetch products with optional filters and pagination
 * @param {Object} options - Query parameters
 * @param {number} options.page - Page number (default: 1)
 * @param {number} options.per_page - Items per page (default: 10)
 * @param {string} options.search - Search term
 * @param {string} options.category - Filter by category
 * @param {boolean} options.in_stock - Filter by stock status
 * @returns {Promise<Object>} Paginated products data
 */
export const getProducts = async ({
  page = 1,
  per_page = 10,
  search = '',
  category = '',
  in_stock = null
} = {}) => {
  const params = new URLSearchParams({
    page,
    per_page,
    ...(search && { search }),
    ...(category && { category }),
    ...(in_stock !== null && { in_stock })
  });

  return api.get(`${PRODUCTS_ENDPOINT}?${params.toString()}`);
};

/**
 * Fetch a single product by ID
 * @param {number|string} productId - Product ID
 * @returns {Promise<Object>} Product data
 */
export const getProduct = async (productId) => {
  return api.get(`${PRODUCTS_ENDPOINT}/${productId}`);
};

/**
 * Create a new product
 * @param {Object} productData - Product data
 * @returns {Promise<Object>} Created product data
 */
export const createProduct = async (productData) => {
  return api.post(PRODUCTS_ENDPOINT, productData);
};

/**
 * Update an existing product
 * @param {number|string} productId - Product ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated product data
 */
export const updateProduct = async (productId, updates) => {
  return api.put(`${PRODUCTS_ENDPOINT}/${productId}`, updates);
};

/**
 * Delete a product
 * @param {number|string} productId - Product ID
 * @returns {Promise<void>}
 */
export const deleteProduct = async (productId) => {
  return api.del(`${PRODUCTS_ENDPOINT}/${productId}`);
};

/**
 * Get inventory history for a product
 * @param {number|string} productId - Product ID
 * @param {Object} options - Query parameters
 * @param {number} options.page - Page number (default: 1)
 * @param {number} options.per_page - Items per page (default: 10)
 * @returns {Promise<Object>} Paginated inventory movements
 */
export const getInventoryHistory = async (productId, { page = 1, per_page = 10 } = {}) => {
  const params = new URLSearchParams({ page, per_page });
  return api.get(`${PRODUCTS_ENDPOINT}/${productId}/inventory?${params.toString()}`);
};

/**
 * Adjust product inventory
 * @param {number|string} productId - Product ID
 * @param {Object} movementData - Inventory movement data
 * @param {number} movementData.quantity - Quantity to adjust
 * @param {string} movementData.movement_type - Type of movement (e.g., 'purchase', 'sale')
 * @param {string} movementData.notes - Notes about the movement
 * @param {string} movementData.reference_number - Reference number
 * @param {string} movementData.movement_date - ISO date string
 * @returns {Promise<Object>} Updated inventory data
 */
export const adjustInventory = async (productId, movementData) => {
  return api.post(`${PRODUCTS_ENDPOINT}/${productId}/inventory`, movementData);
};

/**
 * Get list of product categories
 * @returns {Promise<Object>} List of categories
 */
export const getCategories = async () => {
  return api.get(`${PRODUCTS_ENDPOINT}/categories`);
};

// Export all methods
export default {
  getProducts,
  getProduct,
  createProduct,
  updateProduct,
  deleteProduct,
  getInventoryHistory,
  adjustInventory,
  getCategories
};
