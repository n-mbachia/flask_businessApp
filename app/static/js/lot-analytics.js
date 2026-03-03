/**
 * Lot Analytics Table JavaScript
 * Handles sorting, filtering, pagination, and data management
 */
class LotAnalyticsTable {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            pageSize: options.pageSize || 10,
            sortable: options.sortable !== false,
            filterable: options.filterable !== false,
            exportable: options.exportable !== false,
            apiUrl: options.apiUrl || '/api/v1/lot-analytics',
            ...options
        };
        
        this.data = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.filters = {};
        this.loading = false;
        
        this.init();
    }

    /**
     * Initialize the table
     */
    init() {
        this.createTableStructure();
        this.setupEventListeners();
        this.loadData();
    }

    /**
     * Create table structure
     */
    createTableStructure() {
        this.container.innerHTML = `
            <div class="lot-analytics-container">
                <div class="lot-analytics-header">
                    <h2 class="lot-analytics-title">
                        <i class="fas fa-boxes me-2"></i>
                        Lot Analytics
                    </h2>
                    <div class="lot-analytics-actions">
                        <button class="btn btn-primary btn-sm" onclick="window.lotAnalyticsTable.refreshData()">
                            <i class="fas fa-sync-alt me-1"></i>Refresh
                        </button>
                        ${this.options.exportable ? this.createExportDropdown() : ''}
                    </div>
                </div>
                
                ${this.options.filterable ? this.createFilterSection() : ''}
                
                <div class="table-responsive">
                    <table class="lot-analytics-table" id="lotAnalyticsTable">
                        <thead>
                            <tr>
                                <th data-column="lot_number" class="sortable">Lot Number</th>
                                <th data-column="product_name" class="sortable">Product</th>
                                <th data-column="quantity_received" class="sortable">Received</th>
                                <th data-column="quantity_sold" class="sortable">Sold</th>
                                <th data-column="quantity_remaining" class="sortable">Remaining</th>
                                <th data-column="sell_through_rate" class="sortable">Sell-Through</th>
                                <th data-column="gross_margin" class="sortable">Margin</th>
                                <th data-column="status" class="sortable">Status</th>
                                <th data-column="created_at" class="sortable">Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="lotTableBody">
                            <tr>
                                <td colspan="10" class="table-loading">
                                    <div class="loading-spinner"></div>
                                    <div>Loading lot analytics data...</div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                ${this.createPaginationSection()}
            </div>
        `;
    }

    /**
     * Create export dropdown
     */
    createExportDropdown() {
        return `
            <div class="export-dropdown">
                <button class="btn btn-success btn-sm" onclick="window.lotAnalyticsTable.toggleExportMenu()">
                    <i class="fas fa-download me-1"></i>Export
                </button>
                <div class="export-menu" id="exportMenu">
                    <button class="export-item" onclick="window.lotAnalyticsTable.exportData('csv')">
                        <i class="fas fa-file-csv me-2"></i>Export as CSV
                    </button>
                    <button class="export-item" onclick="window.lotAnalyticsTable.exportData('excel')">
                        <i class="fas fa-file-excel me-2"></i>Export as Excel
                    </button>
                    <button class="export-item" onclick="window.lotAnalyticsTable.exportData('pdf')">
                        <i class="fas fa-file-pdf me-2"></i>Export as PDF
                    </button>
                    <button class="export-item" onclick="window.lotAnalyticsTable.printData()">
                        <i class="fas fa-print me-2"></i>Print
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Create filter section
     */
    createFilterSection() {
        return `
            <div class="lot-analytics-filters">
                <div class="filter-group">
                    <input type="text" 
                           class="search-input" 
                           id="lotSearchInput"
                           placeholder="Search lots...">
                    
                    <select class="filter-select" id="statusFilter">
                        <option value="">All Statuses</option>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="sold_out">Sold Out</option>
                        <option value="partial">Partial</option>
                    </select>
                    
                    <select class="filter-select" id="productFilter">
                        <option value="">All Products</option>
                    </select>
                    
                    <select class="filter-select" id="dateRangeFilter">
                        <option value="">All Time</option>
                        <option value="7">Last 7 Days</option>
                        <option value="30">Last 30 Days</option>
                        <option value="90">Last 90 Days</option>
                        <option value="365">Last Year</option>
                    </select>
                    
                    <button class="btn btn-secondary btn-sm" onclick="window.lotAnalyticsTable.clearFilters()">
                        <i class="fas fa-times me-1"></i>Clear
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Create pagination section
     */
    createPaginationSection() {
        return `
            <div class="lot-analytics-pagination">
                <div class="pagination-info">
                    Showing <span id="startRecord">0</span> to <span id="endRecord">0</span> 
                    of <span id="totalRecords">0</span> lots
                </div>
                
                <div class="pagination-controls">
                    <button class="pagination-btn" id="firstPageBtn" onclick="window.lotAnalyticsTable.goToFirstPage()">
                        <i class="fas fa-angle-double-left"></i>
                    </button>
                    <button class="pagination-btn" id="prevPageBtn" onclick="window.lotAnalyticsTable.goToPrevPage()">
                        <i class="fas fa-angle-left"></i>
                    </button>
                    
                    <div id="pageNumbers"></div>
                    
                    <button class="pagination-btn" id="nextPageBtn" onclick="window.lotAnalyticsTable.goToNextPage()">
                        <i class="fas fa-angle-right"></i>
                    </button>
                    <button class="pagination-btn" id="lastPageBtn" onclick="window.lotAnalyticsTable.goToLastPage()">
                        <i class="fas fa-angle-double-right"></i>
                    </button>
                </div>
                
                <div class="page-size-selector">
                    Show
                    <select class="page-size-select" id="pageSizeSelect" onchange="window.lotAnalyticsTable.changePageSize()">
                        <option value="10">10</option>
                        <option value="25">25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                    </select>
                    per page
                </div>
            </div>
        `;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('lotSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.filters.search = e.target.value;
                this.applyFilters();
            }, 300));
        }

        // Filter selects
        const filterSelects = document.querySelectorAll('.filter-select');
        filterSelects.forEach(select => {
            select.addEventListener('change', (e) => {
                const filterName = e.target.id.replace('Filter', '');
                this.filters[filterName] = e.target.value;
                this.applyFilters();
            });
        });

        // Sortable columns
        if (this.options.sortable) {
            const sortableHeaders = this.container.querySelectorAll('.sortable');
            sortableHeaders.forEach(header => {
                header.addEventListener('click', () => {
                    const column = header.dataset.column;
                    this.sortData(column);
                });
            });
        }

        // Close export menu when clicking outside
        document.addEventListener('click', (e) => {
            const exportMenu = document.getElementById('exportMenu');
            if (exportMenu && !e.target.closest('.export-dropdown')) {
                exportMenu.classList.remove('show');
            }
        });
    }

    /**
     * Load data from API
     */
    async loadData() {
        try {
            this.loading = true;
            this.showLoadingState();

            const params = new URLSearchParams({
                page: this.currentPage,
                page_size: this.options.pageSize,
                ...this.filters
            });

            if (this.sortColumn) {
                params.append('sort_by', this.sortColumn);
                params.append('sort_direction', this.sortDirection);
            }

            const response = await this.fetchWithTimeout(
                `${this.options.apiUrl}?${params}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.data = result.data || [];
            this.filteredData = [...this.data];
            
            this.updateProductFilter(result.products || []);
            this.renderTable();
            this.updatePagination(result.pagination || {});

        } catch (error) {
            console.error('Error loading lot analytics data:', error);
            this.showErrorState('Failed to load lot analytics data');
        } finally {
            this.loading = false;
            this.hideLoadingState();
        }
    }

    /**
     * Refresh data
     */
    async refreshData() {
        await this.loadData();
    }

    /**
     * Apply filters
     */
    applyFilters() {
        this.currentPage = 1;
        this.loadData();
    }

    /**
     * Clear filters
     */
    clearFilters() {
        this.filters = {};
        
        // Reset filter inputs
        const searchInput = document.getElementById('lotSearchInput');
        if (searchInput) searchInput.value = '';
        
        const filterSelects = document.querySelectorAll('.filter-select');
        filterSelects.forEach(select => {
            select.selectedIndex = 0;
        });
        
        this.applyFilters();
    }

    /**
     * Sort data
     */
    sortData(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        this.updateSortHeaders();
        this.loadData();
    }

    /**
     * Update sort headers
     */
    updateSortHeaders() {
        const headers = this.container.querySelectorAll('.sortable');
        headers.forEach(header => {
            header.classList.remove('sorted-asc', 'sorted-desc');
            
            if (header.dataset.column === this.sortColumn) {
                header.classList.add(`sorted-${this.sortDirection}`);
            }
        });
    }

    /**
     * Render table
     */
    renderTable() {
        const tbody = document.getElementById('lotTableBody');
        if (!tbody) return;

        if (this.filteredData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-state">
                        <div class="empty-state-icon">
                            <i class="fas fa-box-open"></i>
                        </div>
                        <div class="empty-state-title">No lots found</div>
                        <div class="empty-state-description">
                            Try adjusting your filters or search criteria
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        const startIndex = (this.currentPage - 1) * this.options.pageSize;
        const endIndex = Math.min(startIndex + this.options.pageSize, this.filteredData.length);
        const pageData = this.filteredData.slice(startIndex, endIndex);

        tbody.innerHTML = pageData.map(lot => this.createTableRow(lot)).join('');
    }

    /**
     * Create table row
     */
    createTableRow(lot) {
        const sellThroughRate = this.calculateSellThroughRate(lot);
        const statusClass = this.getStatusClass(lot.status);
        const marginClass = this.getMarginClass(lot.gross_margin);

        return `
            <tr data-lot-id="${lot.id}">
                <td>
                    <a href="/lots/${lot.id}" class="lot-number">${lot.lot_number}</a>
                </td>
                <td>${lot.product_name}</td>
                <td>${lot.quantity_received.toLocaleString()}</td>
                <td>${lot.quantity_sold.toLocaleString()}</td>
                <td>${lot.quantity_remaining.toLocaleString()}</td>
                <td>
                    <div class="performance-indicator">
                        <div class="sell-through-progress">
                            <div class="sell-through-fill ${sellThroughRate.class}" 
                                 style="width: ${sellThroughRate.percentage}%"></div>
                        </div>
                        <span class="performance-value">${sellThroughRate.value}%</span>
                    </div>
                </td>
                <td>
                    <div class="performance-indicator">
                        <div class="performance-bar">
                            <div class="performance-fill ${marginClass}" 
                                 style="width: ${Math.min(Math.abs(lot.gross_margin || 0), 100)}%"></div>
                        </div>
                        <span class="performance-value">${(lot.gross_margin || 0).toFixed(1)}%</span>
                    </div>
                </td>
                <td>
                    <span class="lot-status ${statusClass}">${lot.status}</span>
                </td>
                <td>${this.formatDate(lot.created_at)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-action view" 
                                onclick="window.lotAnalyticsTable.viewLot(${lot.id})"
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-action edit" 
                                onclick="window.lotAnalyticsTable.editLot(${lot.id})"
                                title="Edit Lot">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-action delete" 
                                onclick="window.lotAnalyticsTable.deleteLot(${lot.id})"
                                title="Delete Lot">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * Calculate sell-through rate
     */
    calculateSellThroughRate(lot) {
        const rate = lot.quantity_received > 0 
            ? (lot.quantity_sold / lot.quantity_received) * 100 
            : 0;
        
        return {
            value: rate.toFixed(1),
            percentage: Math.min(rate, 100),
            class: rate >= 80 ? 'high' : rate >= 50 ? 'medium' : 'low'
        };
    }

    /**
     * Get status class
     */
    getStatusClass(status) {
        const statusMap = {
            'active': 'status-active',
            'inactive': 'status-inactive',
            'sold_out': 'status-sold-out',
            'partial': 'status-partial'
        };
        return statusMap[status] || 'status-inactive';
    }

    /**
     * Get margin class
     */
    getMarginClass(margin) {
        if (margin >= 30) return 'high';
        if (margin >= 15) return 'medium';
        return 'low';
    }

    /**
     * Update pagination
     */
    updatePagination(pagination) {
        const startRecord = document.getElementById('startRecord');
        const endRecord = document.getElementById('endRecord');
        const totalRecords = document.getElementById('totalRecords');

        if (startRecord) startRecord.textContent = pagination.start || 0;
        if (endRecord) endRecord.textContent = pagination.end || 0;
        if (totalRecords) totalRecords.textContent = pagination.total || 0;

        this.updatePaginationButtons(pagination);
        this.updatePageNumbers(pagination);
    }

    /**
     * Update pagination buttons
     */
    updatePaginationButtons(pagination) {
        const firstBtn = document.getElementById('firstPageBtn');
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const lastBtn = document.getElementById('lastPageBtn');

        const hasPrev = pagination.has_prev;
        const hasNext = pagination.has_next;

        if (firstBtn) firstBtn.disabled = !hasPrev;
        if (prevBtn) prevBtn.disabled = !hasPrev;
        if (nextBtn) nextBtn.disabled = !hasNext;
        if (lastBtn) lastBtn.disabled = !hasNext;
    }

    /**
     * Update page numbers
     */
    updatePageNumbers(pagination) {
        const pageNumbers = document.getElementById('pageNumbers');
        if (!pageNumbers) return;

        const currentPage = pagination.page || 1;
        const totalPages = pagination.total_pages || 1;
        const pages = this.calculatePageNumbers(currentPage, totalPages);

        pageNumbers.innerHTML = pages.map(page => {
            if (page === '...') {
                return '<span class="pagination-ellipsis">...</span>';
            }
            return `
                <button class="pagination-btn ${page === currentPage ? 'active' : ''}" 
                        onclick="window.lotAnalyticsTable.goToPage(${page})">
                    ${page}
                </button>
            `;
        }).join('');
    }

    /**
     * Calculate page numbers to display
     */
    calculatePageNumbers(currentPage, totalPages) {
        const delta = 2;
        const range = [];
        const rangeWithDots = [];
        let l;

        for (let i = 1; i <= totalPages; i++) {
            if (i == 1 || i == totalPages || (i >= currentPage - delta && i <= currentPage + delta)) {
                range.push(i);
            }
        }

        range.forEach((i) => {
            if (l) {
                if (i - l === 2) {
                    rangeWithDots.push(l + 1);
                } else if (i - l !== 1) {
                    rangeWithDots.push('...');
                }
            }
            rangeWithDots.push(i);
            l = i;
        });

        return rangeWithDots;
    }

    /**
     * Navigation methods
     */
    goToFirstPage() {
        this.currentPage = 1;
        this.loadData();
    }

    goToPrevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadData();
        }
    }

    goToNextPage() {
        this.currentPage++;
        this.loadData();
    }

    goToLastPage() {
        // This would be set from pagination data
        this.currentPage = this.totalPages || 1;
        this.loadData();
    }

    goToPage(page) {
        this.currentPage = page;
        this.loadData();
    }

    /**
     * Change page size
     */
    changePageSize() {
        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) {
            this.options.pageSize = parseInt(pageSizeSelect.value);
            this.currentPage = 1;
            this.loadData();
        }
    }

    /**
     * Update product filter
     */
    updateProductFilter(products) {
        const productFilter = document.getElementById('productFilter');
        if (!productFilter || !products) return;

        const currentValue = productFilter.value;
        productFilter.innerHTML = '<option value="">All Products</option>';
        
        products.forEach(product => {
            const option = document.createElement('option');
            option.value = product.id;
            option.textContent = product.name;
            if (product.id == currentValue) {
                option.selected = true;
            }
            productFilter.appendChild(option);
        });
    }

    /**
     * Export data
     */
    async exportData(format) {
        try {
            this.showLoadingState();

            const params = new URLSearchParams({
                format: format,
                ...this.filters
            });

            if (this.sortColumn) {
                params.append('sort_by', this.sortColumn);
                params.append('sort_direction', this.sortDirection);
            }

            const response = await this.fetchWithTimeout(
                `${this.options.apiUrl}/export?${params}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `lot-analytics.${format}`;
            a.click();
            window.URL.revokeObjectURL(url);

            this.showNotification(`Data exported successfully as ${format.toUpperCase()}`, 'success');

        } catch (error) {
            console.error('Error exporting data:', error);
            this.showNotification('Error exporting data', 'error');
        } finally {
            this.hideLoadingState();
        }
    }

    /**
     * Print data
     */
    printData() {
        window.print();
    }

    /**
     * Toggle export menu
     */
    toggleExportMenu() {
        const exportMenu = document.getElementById('exportMenu');
        if (exportMenu) {
            exportMenu.classList.toggle('show');
        }
    }

    /**
     * View lot details
     */
    viewLot(lotId) {
        window.location.href = `/lots/${lotId}`;
    }

    /**
     * Edit lot
     */
    editLot(lotId) {
        window.location.href = `/lots/${lotId}/edit`;
    }

    /**
     * Delete lot
     */
    async deleteLot(lotId) {
        if (!confirm('Are you sure you want to delete this lot? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`${this.options.apiUrl}/${lotId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Remove the row from the table
            const row = document.querySelector(`tr[data-lot-id="${lotId}"]`);
            if (row) {
                row.remove();
            }

            // Update data array
            this.data = this.data.filter(lot => lot.id !== lotId);
            this.filteredData = this.filteredData.filter(lot => lot.id !== lotId);

            this.showNotification('Lot deleted successfully', 'success');
            this.renderTable();
            this.updatePagination({});

        } catch (error) {
            console.error('Error deleting lot:', error);
            this.showNotification('Error deleting lot', 'error');
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const tbody = document.getElementById('lotTableBody');
        if (tbody && !this.loading) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="table-loading">
                        <div class="loading-spinner"></div>
                        <div>Loading...</div>
                    </td>
                </tr>
            `;
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        // Loading state is hidden when table is rendered
    }

    /**
     * Show error state
     */
    showErrorState(message) {
        const tbody = document.getElementById('lotTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-state">
                        <div class="empty-state-icon">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                        <div class="empty-state-title">Error</div>
                        <div class="empty-state-description">${message}</div>
                    </td>
                </tr>
            `;
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    /**
     * Debounce function
     */
    debounce(func, wait) {
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
     * Fetch with timeout
     */
    async fetchWithTimeout(url, timeout = 10000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    /**
     * Destroy the table
     */
    destroy() {
        // Clean up event listeners and timers
        this.container.innerHTML = '';
    }
}

// Export for global access
window.LotAnalyticsTable = LotAnalyticsTable;
