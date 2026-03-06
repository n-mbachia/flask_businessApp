/**
 * Orders List Page (index)
 * Handles infinite scroll, filter collapse, and tooltips.
 */
(function() {
    'use strict';

    const paginationData = document.getElementById('ordersPaginationData');
    const tbody = document.getElementById('ordersTableBody');
    const loader = document.getElementById('infiniteScrollLoader');
    const filterBtn = document.querySelector('[data-bs-toggle="collapse"]'); // we'll replace with Alpine
    // Since we use Alpine for collapse, we don't need Bootstrap collapse; we'll handle with Alpine.

    let currentPage = Number(paginationData?.dataset.currentPage || 1);
    const totalPages = Number(paginationData?.dataset.totalPages || 1);
    let isLoading = false;
    let hasMore = currentPage < totalPages;
    const scrollBuffer = 300; // px

    function fetchMoreOrders() {
        if (isLoading || !hasMore || !tbody) return;

        const scrollPosition = window.scrollY + window.innerHeight;
        const pageHeight = document.documentElement.scrollHeight - scrollBuffer;
        if (scrollPosition < pageHeight) return;

        isLoading = true;
        if (loader) loader.classList.remove('hidden');

        const nextPage = currentPage + 1;
        const url = new URL(window.location.href);
        url.searchParams.set('page', nextPage);

        fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(response => response.json())
            .then(data => {
                if (data.html && data.html.trim() !== '') {
                    tbody.insertAdjacentHTML('beforeend', data.html);
                    currentPage = nextPage;
                    hasMore = data.has_next;
                } else {
                    hasMore = false;
                }
            })
            .catch(error => console.error('Error loading more orders:', error))
            .finally(() => {
                isLoading = false;
                if (loader) loader.classList.add('hidden');
            });
    }

    // Throttled scroll listener
    window.addEventListener('scroll', () => {
        window.requestAnimationFrame(fetchMoreOrders);
    });

    window.addEventListener('resize', fetchMoreOrders);

    // Filter form auto-submit on change (excluding search input)
    const filterForm = document.getElementById('filtersForm');
    if (filterForm) {
        filterForm.querySelectorAll('select, input[type="date"]').forEach(el => {
            el.addEventListener('change', () => {
                // Reset page to 1
                const pageInput = document.createElement('input');
                pageInput.type = 'hidden';
                pageInput.name = 'page';
                pageInput.value = '1';
                filterForm.appendChild(pageInput);
                filterForm.submit();
            });
        });
    }

    // Tooltips (native title, no Bootstrap)
    // Already handled by title attribute.
})();