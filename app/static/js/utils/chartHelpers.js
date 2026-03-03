/**
 * Chart Rendering Helpers
 * Provides generic functions for rendering charts with Chart.js
 */

export function renderLineChart(ctx, labels, dataset, options = {}) {
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [dataset]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...options
    }
  });
}

export function renderDoughnutChart(ctx, labels, dataset, options = {}) {
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [dataset]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...options
    }
  });
}

export function renderBarChart(ctx, labels, dataset, options = {}) {
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [dataset]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...options
    }
  });
}
