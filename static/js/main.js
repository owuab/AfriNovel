/**
 * BookClub Design System - Global JavaScript
 */

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeUI);

function initializeUI() {
  // Initialize message close buttons
  initializeMessages();
  
  // Initialize form enhancements
  initializeForms();
  
  // Initialize accessibility features
  initializeAccessibility();
  
  // Initialize enhanced hover effects
  initializeHoverEffects();
  
  // Initialize smooth scroll behavior
  initializeSmoothScroll();
  
  // Navigation is now handled by navbar.js module
  // Carousel is now handled by carousel.js module
}

/**
 * Message Dismissal
 */
function initializeMessages() {
  const closeButtons = document.querySelectorAll('.message-close');
  
  closeButtons.forEach(button => {
    button.addEventListener('click', function() {
      const message = this.closest('.message');
      if (message) {
        message.style.animation = 'slideOut 300ms ease-out forwards';
        setTimeout(() => message.remove(), 300);
      }
    });
  });
  
  // Auto-dismiss success messages after 5 seconds
  const successMessages = document.querySelectorAll('.message.success');
  successMessages.forEach(message => {
    setTimeout(() => {
      message.style.animation = 'slideOut 300ms ease-out forwards';
      setTimeout(() => message.remove(), 300);
    }, 5000);
  });
}

/**
 * Form Enhancements
 */
function initializeForms() {
  // Add focus classes to form inputs
  const inputs = document.querySelectorAll('input, textarea, select');
  
  inputs.forEach(input => {
    input.addEventListener('focus', function() {
      this.closest('.form-group')?.classList.add('focused');
    });
    
    input.addEventListener('blur', function() {
      this.closest('.form-group')?.classList.remove('focused');
    });
    
    // Add filled class if input has value
    input.addEventListener('change', updateInputState);
    input.addEventListener('input', updateInputState);
    
    // Check initial state
    if (input.value) {
      input.closest('.form-group')?.classList.add('filled');
    }
  });
  
  // Form validation on submit
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      if (!validateForm(this)) {
        e.preventDefault();
      }
    });
  });
}

function updateInputState() {
  const formGroup = this.closest('.form-group');
  if (formGroup) {
    if (this.value) {
      formGroup.classList.add('filled');
    } else {
      formGroup.classList.remove('filled');
    }
  }
}

function validateForm(form) {
  let isValid = true;
  const inputs = form.querySelectorAll('[required]');
  
  inputs.forEach(input => {
    if (!validateInput(input)) {
      isValid = false;
    }
  });
  
  return isValid;
}

function validateInput(input) {
  const formGroup = input.closest('.form-group');
  const isValid = input.value.trim() !== '';
  
  if (isValid) {
    input.classList.remove('error');
    formGroup?.classList.remove('has-error');
  } else {
    input.classList.add('error');
    formGroup?.classList.add('has-error');
  }
  
  return isValid;
}

/**
 * Enhanced Hover Effects
 */
function initializeHoverEffects() {
  // Enhanced book card hover effects
  const bookCards = document.querySelectorAll('.book-card-premium');
  
  bookCards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      // Add subtle glow effect
      this.style.boxShadow = '0 8px 25px rgba(233, 69, 96, 0.2)';
    });
    
    card.addEventListener('mouseleave', function() {
      // Remove glow effect
      this.style.boxShadow = '';
    });
  });
  
  // Enhanced button hover effects
  const buttons = document.querySelectorAll('.button, .action-button');
  
  buttons.forEach(button => {
    button.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-2px)';
    });
    
    button.addEventListener('mouseleave', function() {
      this.style.transform = '';
    });
  });
  
  // Enhanced genre card hover effects
  const genreCards = document.querySelectorAll('.genre-card');
  
  genreCards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-4px) scale(1.02)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = '';
    });
  });
}

/**
 * Smooth Scroll Behavior
 */
function initializeSmoothScroll() {
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
}

/**
 * Accessibility Enhancements
 */
function initializeAccessibility() {
  // Add keyboard navigation to buttons
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      // Close mobile menu on escape
      const navMenu = document.querySelector('.nav-menu');
      if (navMenu) {
        navMenu.classList.remove('active');
      }
      
      // Close dropdowns on escape
      const dropdowns = document.querySelectorAll('.dropdown-menu.show, .nav-search-dropdown.show');
      dropdowns.forEach(dropdown => {
        dropdown.classList.remove('show');
      });
    }
  });
  
  // Ensure all focusable elements are properly focused
  setUpFocusVisiblePolyfill();
}

/**
 * Focus Visible Polyfill for older browsers
 */
function setUpFocusVisiblePolyfill() {
  const focusVisibleElements = document.querySelectorAll('button, a, input, textarea, select');
  
  focusVisibleElements.forEach(element => {
    element.addEventListener('mousedown', () => {
      element.classList.remove('focus-visible');
    });
    
    element.addEventListener('keydown', () => {
      element.classList.add('focus-visible');
    });
  });
}

/**
 * Utility: Add animation keyframes
 */
function addAnimationStyles() {
  if (document.getElementById('bookclub-animations')) return;
  
  const style = document.createElement('style');
  style.id = 'bookclub-animations';
  style.textContent = `
    @keyframes slideOut {
      from {
        opacity: 1;
        transform: translateX(0);
      }
      to {
        opacity: 0;
        transform: translateX(100%);
      }
    }
  `;
  document.head.appendChild(style);
}

// Add animation styles
addAnimationStyles();

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initializeUI,
    initializeMessages,
    initializeForms,
    initializeAccessibility,
    initializeHoverEffects,
    initializeSmoothScroll,
  };
}
