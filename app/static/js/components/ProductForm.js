import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { getCategories, createProduct, updateProduct, getProduct } from '../api/products';
import { formatNumber, formatCurrency, parseNumber } from '../utils/formatters';

const ProductForm = ({ productId, onSuccess, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState(null);
  
  const { register, handleSubmit, reset, formState: { errors }, setValue, watch } = useForm({
    defaultValues: {
      name: '',
      category: '',
      sku: '',
      barcode: '',
      cogs_per_unit: 0,
      selling_price_per_unit: 0,
      reorder_level: 10,
      is_active: true,
      description: ''
    }
  });

  // Watch form values for formatting
  const watchCogs = watch('cogs_per_unit');
  const watchPrice = watch('selling_price_per_unit');
  const watchReorderLevel = watch('reorder_level');

  // Format currency inputs
  const formatCurrencyInput = (value, field) => {
    const num = parseNumber(value);
    setValue(field, num, { shouldValidate: true });
    return formatCurrency(num, 'USD', 2);
  };

  // Format number inputs
  const formatNumberInput = (value, field) => {
    const num = parseNumber(value);
    setValue(field, num, { shouldValidate: true });
    return formatNumber(num, 0);
  };

  // Load categories and product data if editing
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // Load categories
        const categoriesData = await getCategories();
        setCategories(categoriesData);
        
        // Load product data if editing
        if (productId) {
          const productData = await getProduct(productId);
          reset({
            ...productData,
            // Format numeric values for display
            cogs_per_unit: formatCurrency(productData.cogs_per_unit),
            selling_price_per_unit: formatCurrency(productData.selling_price_per_unit)
          });
        }
      } catch (err) {
        console.error('Error loading form data:', err);
        setError('Failed to load form data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [productId, reset]);

  const onSubmit = async (data) => {
    try {
      setLoading(true);
      setError(null);
      
      // Parse numeric values before submission
      const formData = {
        ...data,
        cogs_per_unit: parseNumber(data.cogs_per_unit),
        selling_price_per_unit: parseNumber(data.selling_price_per_unit),
        reorder_level: parseInt(data.reorder_level, 10)
      };
      
      if (productId) {
        await updateProduct(productId, formData);
      } else {
        await createProduct(formData);
      }
      
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error('Error saving product:', err);
      setError(err.message || 'Failed to save product. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !productId) {
    return (
      <div className="flex justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}
      
      <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div className="md:grid md:grid-cols-3 md:gap-6">
          <div className="md:col-span-1">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Product Information</h3>
            <p className="mt-1 text-sm text-gray-500">Basic details about the product.</p>
          </div>
          <div className="mt-5 md:mt-0 md:col-span-2">
            <div className="grid grid-cols-6 gap-6">
              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  Product Name *
                </label>
                <input
                  type="text"
                  id="name"
                  {...register('name', { required: 'Product name is required' })}
                  className={`mt-1 block w-full border ${errors.name ? 'border-red-300' : 'border-gray-300'} rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
                />
                {errors.name && (
                  <p className="mt-2 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                  Category
                </label>
                <select
                  id="category"
                  {...register('category')}
                  className="mt-1 block w-full border border-gray-300 bg-white rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="">Select a category</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="sku" className="block text-sm font-medium text-gray-700">
                  SKU
                </label>
                <input
                  type="text"
                  id="sku"
                  {...register('sku')}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="barcode" className="block text-sm font-medium text-gray-700">
                  Barcode
                </label>
                <input
                  type="text"
                  id="barcode"
                  {...register('barcode')}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="cogs_per_unit" className="block text-sm font-medium text-gray-700">
                  Cost per Unit
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">$</span>
                  </div>
                  <input
                    type="text"
                    id="cogs_per_unit"
                    {...register('cogs_per_unit', {
                      required: 'Cost is required',
                      min: { value: 0, message: 'Cost must be positive' },
                      onChange: (e) => {
                        e.target.value = formatCurrencyInput(e.target.value, 'cogs_per_unit');
                      }
                    })}
                    className={`block w-full pl-7 pr-12 border ${errors.cogs_per_unit ? 'border-red-300' : 'border-gray-300'} rounded-md py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
                    placeholder="0.00"
                  />
                </div>
                {errors.cogs_per_unit && (
                  <p className="mt-2 text-sm text-red-600">{errors.cogs_per_unit.message}</p>
                )}
              </div>

              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="selling_price_per_unit" className="block text-sm font-medium text-gray-700">
                  Selling Price *
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">$</span>
                  </div>
                  <input
                    type="text"
                    id="selling_price_per_unit"
                    {...register('selling_price_per_unit', {
                      required: 'Price is required',
                      min: { value: 0, message: 'Price must be positive' },
                      validate: (value) => {
                        const price = parseNumber(value);
                        const cost = parseNumber(watchCogs);
                        return price >= cost || 'Price must be greater than or equal to cost';
                      },
                      onChange: (e) => {
                        e.target.value = formatCurrencyInput(e.target.value, 'selling_price_per_unit');
                      }
                    })}
                    className={`block w-full pl-7 pr-12 border ${errors.selling_price_per_unit ? 'border-red-300' : 'border-gray-300'} rounded-md py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
                    placeholder="0.00"
                  />
                </div>
                {errors.selling_price_per_unit && (
                  <p className="mt-2 text-sm text-red-600">{errors.selling_price_per_unit.message}</p>
                )}
              </div>

              <div className="col-span-6 sm:col-span-3">
                <label htmlFor="reorder_level" className="block text-sm font-medium text-gray-700">
                  Reorder Level
                </label>
                <input
                  type="text"
                  id="reorder_level"
                  {...register('reorder_level', {
                    required: 'Reorder level is required',
                    min: { value: 0, message: 'Must be 0 or greater' },
                    onChange: (e) => {
                      e.target.value = formatNumberInput(e.target.value, 'reorder_level');
                    }
                  })}
                  className={`mt-1 block w-full border ${errors.reorder_level ? 'border-red-300' : 'border-gray-300'} rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
                />
                {errors.reorder_level && (
                  <p className="mt-2 text-sm text-red-600">{errors.reorder_level.message}</p>
                )}
              </div>

              <div className="col-span-6 sm:col-span-3 flex items-end">
                <div className="flex items-center h-5">
                  <input
                    id="is_active"
                    type="checkbox"
                    {...register('is_active')}
                    className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
                  />
                </div>
                <div className="ml-3 text-sm">
                  <label htmlFor="is_active" className="font-medium text-gray-700">
                    Active Product
                  </label>
                  <p className="text-gray-500">Product will be available for sale</p>
                </div>
              </div>

              <div className="col-span-6">
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <div className="mt-1">
                  <textarea
                    id="description"
                    rows={3}
                    {...register('description')}
                    className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full border border-gray-300 rounded-md sm:text-sm"
                    placeholder="Product description..."
                  />
                </div>
                <p className="mt-2 text-sm text-gray-500">
                  Brief description for the product.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="ml-3 inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : productId ? 'Update Product' : 'Create Product'}
        </button>
      </div>
    </form>
  );
};

export default ProductForm;
