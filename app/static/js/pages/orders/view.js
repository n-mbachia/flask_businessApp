document.addEventListener('DOMContentLoaded', function() {
    // Format currency and dates
    document.querySelectorAll('.currency').forEach(el => {
        const val = parseFloat(el.textContent);
        if (!isNaN(val)) {
            el.textContent = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
        }
    });
    document.querySelectorAll('time').forEach(el => {
        const date = new Date(el.getAttribute('datetime'));
        if (!isNaN(date)) {
            el.textContent = new Intl.DateTimeFormat('en-US', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit'
            }).format(date);
        }
    });

    // Handle complete order modal
    const completeModal = document.getElementById('completeOrderModal');
    if (completeModal) {
        const confirmBtn = document.getElementById('confirmCompleteBtn');
        const notes = document.getElementById('completion_notes');
        const errorDiv = document.getElementById('completeError');

        completeModal.addEventListener('show.bs.modal', function() {
            errorDiv.classList.add('d-none');
            if (notes) notes.value = '';
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span><span class="btn-text">Mark as Completed</span>';
        });

        confirmBtn.addEventListener('click', function() {
            const spinner = this.querySelector('.spinner-border');
            const btnText = this.querySelector('.btn-text');
            spinner.classList.remove('d-none');
            btnText.textContent = 'Processing...';
            this.disabled = true;

            fetch(`/orders/{{ order.id }}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ notes: notes ? notes.value : '' })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    bootstrap.Modal.getInstance(completeModal).hide();
                    window.location.reload();
                } else {
                    errorDiv.textContent = data.message || 'Failed to complete order.';
                    errorDiv.classList.remove('d-none');
                    spinner.classList.add('d-none');
                    btnText.textContent = 'Mark as Completed';
                    this.disabled = false;
                }
            })
            .catch(err => {
                errorDiv.textContent = 'An error occurred. Please try again.';
                errorDiv.classList.remove('d-none');
                spinner.classList.add('d-none');
                btnText.textContent = 'Mark as Completed';
                this.disabled = false;
            });
        });
    }
});
