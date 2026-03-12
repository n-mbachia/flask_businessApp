/**
 * Dashboard/Analytics API Fetch Utility
 * Provides unified functions for fetching dashboard and analytics data
 */

import { handleResponse, getDefaultHeaders } from './api.js';

export async function fetchKPIData(startDate, endDate) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate
  });
  const response = await fetch(`/api/v1/analytics/kpi?${params}`, {
    headers: getDefaultHeaders()
  });
  return handleResponse(response);
}

export async function fetchRevenueData(startDate, endDate) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate
  });
  const response = await fetch(`/api/v1/analytics/revenue?${params}`, {
    headers: getDefaultHeaders()
  });
  return handleResponse(response);
}

export async function fetchCategoryData(startDate, endDate) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate
  });
  const response = await fetch(`/api/v1/analytics/categories?${params}`, {
    headers: getDefaultHeaders()
  });
  return handleResponse(response);
}

export async function fetchTopProducts(startDate, endDate, limit = 5) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
    limit: limit
  });
  const response = await fetch(`/api/v1/analytics/products/top?${params}`, {
    headers: getDefaultHeaders()
  });
  return handleResponse(response);
}
