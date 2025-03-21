/**
 * Animations for SpeakDB landing page
 * Uses Intersection Observer for scroll-based animations
 */

document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll behavior
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // Initialize scroll animations using Intersection Observer
    const animatedElements = document.querySelectorAll('.fade-up, .fade-in, .zoom-in');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Unobserve after animation is triggered
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,  // Trigger when at least 10% of the element is visible
        rootMargin: '0px 0px -100px 0px'  // Negative bottom margin to trigger earlier
    });
    
    animatedElements.forEach(element => {
        observer.observe(element);
    });

    // Add delay to children elements for staggered animations
    const staggeredParents = document.querySelectorAll('.staggered-parent');
    staggeredParents.forEach(parent => {
        const children = parent.querySelectorAll('.staggered-child');
        children.forEach((child, index) => {
            child.style.transitionDelay = `${index * 0.1}s`;
        });
    });

    // Initialize pricing toggle if it exists
    const annualToggle = document.getElementById('annual-toggle');
    if (annualToggle) {
        annualToggle.addEventListener('change', function() {
            const monthlyPrices = document.querySelectorAll('.monthly-price');
            const annualPrices = document.querySelectorAll('.annual-price');
            
            if (this.checked) {
                // Show annual prices
                monthlyPrices.forEach(el => el.classList.add('d-none'));
                annualPrices.forEach(el => el.classList.remove('d-none'));
            } else {
                // Show monthly prices
                monthlyPrices.forEach(el => el.classList.remove('d-none'));
                annualPrices.forEach(el => el.classList.add('d-none'));
            }
        });
    }
    
    // Initialize Firebase auth UI if on login/signup page
    initFirebaseAuthUI();
});

/**
 * Initialize Firebase Authentication UI
 */
function initFirebaseAuthUI() {
    const googleLoginBtn = document.getElementById('google-login-btn');
    if (googleLoginBtn) {
        googleLoginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const provider = new firebase.auth.GoogleAuthProvider();
            firebase.auth().signInWithPopup(provider)
                .then((result) => {
                    // Get the ID token
                    return result.user.getIdToken();
                })
                .then((idToken) => {
                    // Send the token to the server
                    window.location.href = `/auth/firebase/callback?idToken=${idToken}&next=${encodeURIComponent(googleLoginBtn.dataset.next || '/')}`;
                })
                .catch((error) => {
                    console.error('Firebase auth error:', error);
                    const errorMessage = document.getElementById('error-message');
                    if (errorMessage) {
                        errorMessage.textContent = error.message;
                        errorMessage.classList.remove('d-none');
                    }
                });
        });
    }
}