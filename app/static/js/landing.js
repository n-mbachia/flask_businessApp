/**
 * Landing Page JavaScript
 * Handles interactions, animations, and dynamic features for the landing page
 */
class LandingPage {
    constructor() {
        this.init();
    }

    /**
     * Initialize landing page
     */
    init() {
        this.setupAnimations();
        this.setupScrollEffects();
        this.setupFormInteractions();
        this.setupLazyLoading();
        this.setupAnalytics();
    }

    /**
     * Setup scroll animations
     */
    setupScrollEffects() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);

        // Observe all feature cards
        document.querySelectorAll('.feature-card').forEach(card => {
            observer.observe(card);
        });

        // Parallax effect for hero section
        window.addEventListener('scroll', () => {
            this.handleParallax();
        });
    }

    /**
     * Setup animations
     */
    setupAnimations() {
        // Animate hero elements on load
        const heroTitle = document.querySelector('.hero-section .display-4');
        const heroLead = document.querySelector('.hero-section .lead');
        const heroButtons = document.querySelectorAll('.hero-section .btn');

        if (heroTitle) {
            setTimeout(() => {
                heroTitle.style.opacity = '1';
                heroTitle.style.transform = 'translateY(0)';
            }, 100);
        }

        if (heroLead) {
            setTimeout(() => {
                heroLead.style.opacity = '1';
                heroLead.style.transform = 'translateY(0)';
            }, 300);
        }

        heroButtons.forEach((button, index) => {
            setTimeout(() => {
                button.style.opacity = '1';
                button.style.transform = 'translateY(0)';
            }, 500 + (index * 100));
        });

        // Counter animation for stats
        this.animateCounters();
    }

    /**
     * Handle parallax scrolling
     */
    handleParallax() {
        const scrolled = window.pageYOffset;
        const heroSection = document.querySelector('.hero-section');
        
        if (heroSection && scrolled < heroSection.offsetHeight) {
            const speed = 0.5;
            heroSection.style.transform = `translateY(${scrolled * speed}px)`;
        }
    }

    /**
     * Setup form interactions
     */
    setupFormInteractions() {
        const ctaButtons = document.querySelectorAll('.btn-lg, .btn-light');
        
        ctaButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleCTAClick(e, button);
            });
        });

        // Add hover effects
        ctaButtons.forEach(button => {
            button.addEventListener('mouseenter', () => {
                this.addRippleEffect(button);
            });
        });
    }

    /**
     * Handle CTA button clicks
     */
    handleCTAClick(e, button) {
        const buttonText = button.textContent.trim();
        
        // Track analytics
        this.trackEvent('cta_click', {
            button_text: buttonText,
            button_url: button.href,
            page_location: 'landing_hero'
        });

        // Add loading state
        const originalContent = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';

        // Simulate navigation delay
        setTimeout(() => {
            button.innerHTML = originalContent;
            button.disabled = false;
        }, 1000);
    }

    /**
     * Animate counters
     */
    animateCounters() {
        const counters = [
            { element: document.querySelector('.users-count'), target: 1000, duration: 2000 },
            { element: document.querySelector('.revenue-count'), target: 500000, duration: 2500 },
            { element: document.querySelector('.growth-count'), target: 150, duration: 1800 }
        ];

        counters.forEach(counter => {
            if (counter.element) {
                this.animateCounter(counter.element, counter.target, counter.duration);
            }
        });
    }

    /**
     * Animate single counter
     */
    animateCounter(element, target, duration) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current).toLocaleString();
        }, 16);
    }

    /**
     * Setup lazy loading for images
     */
    setupLazyLoading() {
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy-load');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            img.classList.add('lazy-load');
            imageObserver.observe(img);
        });
    }

    /**
     * Add ripple effect to buttons
     */
    addRippleEffect(button) {
        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        ripple.style.position = 'absolute';
        ripple.style.borderRadius = '50%';
        ripple.style.background = 'rgba(255,255,255,0.5)';
        ripple.style.transform = 'scale(0)';
        ripple.style.animation = 'ripple-animation 0.6s ease-out';
        ripple.style.width = ripple.style.height = '20px';

        const rect = button.getBoundingClientRect();
        ripple.style.left = `${event.clientX - rect.left - 10}px`;
        ripple.style.top = `${event.clientY - rect.top - 10}px`;

        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
            button.style.overflow = '';
            button.style.position = '';
        }, 600);
    }

    /**
     * Setup analytics tracking
     */
    setupAnalytics() {
        // Track page view
        this.trackEvent('page_view', {
            page_title: document.title,
            page_type: 'landing',
            user_agent: navigator.userAgent,
            timestamp: new Date().toISOString()
        });

        // Track scroll depth
        let maxScroll = 0;
        window.addEventListener('scroll', () => {
            maxScroll = Math.max(maxScroll, window.pageYOffset);
        });

        // Track time on page
        const startTime = Date.now();
        window.addEventListener('beforeunload', () => {
            const timeOnPage = Date.now() - startTime;
            this.trackEvent('page_engagement', {
                time_on_page: timeOnPage,
                max_scroll_depth: maxScroll,
                page_type: 'landing'
            });
        });
    }

    /**
     * Track custom events
     */
    trackEvent(eventName, data = {}) {
        // Send to analytics service
        if (typeof gtag !== 'undefined') {
            gtag('event', eventName, data);
        }

        // Log to console for debugging
        console.log('Analytics Event:', eventName, data);

        // Custom event dispatch
        const event = new CustomEvent('landingPageEvent', {
            detail: {
                eventName,
                data,
                timestamp: new Date().toISOString()
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Smooth scroll to section
     */
    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    /**
     * Add CSS animation keyframes dynamically
     */
    addAnimationStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple-animation {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
            
            .animate-in {
                animation: fadeInUp 0.6s ease-out;
            }
            
            .lazy-load {
                filter: blur(5px);
                transition: filter 0.3s ease;
            }
            
            .lazy-load.loaded {
                filter: blur(0);
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Initialize on DOM ready
     */
    static init() {
        // Add animation styles
        const landingPage = new LandingPage();
        
        // Expose global functions
        window.scrollToSection = (sectionId) => landingPage.scrollToSection(sectionId);
        window.trackLandingEvent = (eventName, data) => landingPage.trackEvent(eventName, data);
        
        // Add loading styles
        landingPage.addAnimationStyles();
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    LandingPage.init();
});

// Export for global access
window.LandingPage = LandingPage;
