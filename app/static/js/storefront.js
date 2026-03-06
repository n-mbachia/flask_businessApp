// storefront.js
document.querySelectorAll('.storefront-order-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const productId = btn.dataset.productId;
        const productName = btn.dataset.productName;
        const productPrice = btn.dataset.productPrice;
        const vendorId = btn.dataset.vendorId;
        window.dispatchEvent(new CustomEvent('open-order-modal', {
            detail: { productId, productName, productPrice, vendorId }
        }));
    });
});