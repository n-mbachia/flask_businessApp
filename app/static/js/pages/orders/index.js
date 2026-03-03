document.addEventListener('DOMContentLoaded', function() {
    const paginationTracker = document.getElementById('ordersPaginationData');
    let currentPage = Number(paginationTracker?.dataset.currentPage || 1);
    const totalPages = Number(paginationTracker?.dataset.totalPages || 1);
    let isLoading = false;
    let hasMore = currentPage < totalPages;

    const tbody = document.getElementById('ordersTableBody');
    const loader = document.getElementById('infiniteScrollLoader');
    const filterForm = document.getElementById('filtersForm');
    const scrollBuffer = 500; // px buffer from page bottom

    const fetchMoreOrders = () => {
        if (isLoading || !hasMore || !tbody) return;

        const scrollPosition = window.scrollY + window.innerHeight;
        const pageHeight = document.documentElement.scrollHeight - scrollBuffer;

        if (scrollPosition < pageHeight) {
            return;
        }

        isLoading = true;
        if (loader) loader.classList.remove('d-none');

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
            if (loader) loader.classList.add('d-none');
        });
    };

    window.addEventListener('scroll', () => {
        window.requestAnimationFrame(fetchMoreOrders);
    });
    window.addEventListener('resize', fetchMoreOrders);

    if (filterForm) {
        filterForm.querySelectorAll('select, input[type="date"]').forEach(el => {
            el.addEventListener('change', () => {
                const pageInput = document.createElement('input');
                pageInput.type = 'hidden';
                pageInput.name = 'page';
                pageInput.value = '1';
                filterForm.appendChild(pageInput);
                filterForm.submit();
            });
        });
    }
});
