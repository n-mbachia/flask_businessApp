// Handle login form submission
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        // Toggle password visibility
        const togglePassword = loginForm.querySelector('.toggle-password');
        if (togglePassword) {
            togglePassword.addEventListener('click', function() {
                const passwordInput = this.closest('.input-group').querySelector('input[name="password"]');
                const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordInput.setAttribute('type', type);
                this.querySelector('i').classList.toggle('bi-eye');
                this.querySelector('i').classList.toggle('bi-eye-slash');
            });
        }

        // Handle form submission
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitButton = loginForm.querySelector('button[type="submit"]');
            const buttonText = submitButton.querySelector('.button-text');
            const spinner = document.createElement('span');
            spinner.className = 'spinner-border spinner-border-sm ms-2';
            spinner.setAttribute('role', 'status');
            spinner.setAttribute('aria-hidden', 'true');
            
            try {
                // Show loading state
                submitButton.disabled = true;
                buttonText.textContent = 'Signing in...';
                submitButton.appendChild(spinner);
                
                // Submit form data
                const formData = new FormData(loginForm);
                const response = await fetch(loginForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Redirect on success
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    } else {
                        window.location.reload();
                    }
                } else {
                    // Handle errors
                    throw new Error(data.message || 'Login failed. Please check your credentials.');
                }
                
            } catch (error) {
                console.error('Login error:', error);
                
                // Remove any existing alerts
                const existingAlert = loginForm.querySelector('.alert');
                if (existingAlert) {
                    existingAlert.remove();
                }
                
                // Show error message
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger alert-dismissible fade show mb-4';
                alert.role = 'alert';
                alert.innerHTML = `
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                
                // Insert alert after the form title
                const formTitle = loginForm.querySelector('h2');
                if (formTitle) {
                    formTitle.parentNode.insertBefore(alert, formTitle.nextSibling);
                } else {
                    loginForm.prepend(alert);
                }
                
                // Focus on the first invalid input if any
                const firstInvalid = loginForm.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
                
            } finally {
                // Reset button state
                submitButton.disabled = false;
                buttonText.textContent = 'Sign In';
                const spinner = submitButton.querySelector('.spinner-border');
                if (spinner) {
                    spinner.remove();
                }
            }
        });
    }
});
