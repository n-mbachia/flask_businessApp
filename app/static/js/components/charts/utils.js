// Chart utility functions
export const debounce = (func, wait) => {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
};

export const validateChartData = (data, requiredFields = []) => {
    if (!data) return false;
    return requiredFields.every(field => {
        const value = data[field];
        return Array.isArray(value) ? value.length > 0 : !!value;
    });
};

export const createLoadingState = (element, message = 'Loading...') => {
    element.innerHTML = `
        <div class="chart-loading">
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">${message}</span>
            </div>
            <span>${message}</span>
        </div>
    `;
};

export const createErrorState = (element, error) => {
    console.error('Chart error:', error);
    element.innerHTML = `
        <div class="chart-error">
            <i class="bi bi-exclamation-triangle"></i>
            <p>Error loading chart: ${error.message || 'Unknown error'}</p>
        </div>
    `;
};

export const createNoDataState = (element, message = 'No data available') => {
    element.innerHTML = `
        <div class="no-data">
            <i class="bi bi-graph-up"></i>
            <p>${message}</p>
        </div>
    `;
};