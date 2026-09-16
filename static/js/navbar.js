/**
 * Navbar Module
 * Handles navigation, mobile menu, and sticky header behavior with enhanced interactions
 */

class Navbar {
  constructor() {
    this.navToggle = document.querySelector('.nav-toggle');
    this.navMenu = document.querySelector('.nav-menu');
    this.siteHeader = document.querySelector('.site-header');
    this.lastScroll = 0;
    this.isScrollingDown = false;
    this.scrollThreshold = 50;
    
    this.init();
  }

  init() {
    if (this.navToggle && this.navMenu) {
      this.setupMobileMenu();
    }
    
    if (this.siteHeader) {
      this.setupStickyHeader();
    }
    
    this.setupDropdowns();
    this.setupSearchToggle();
    this.setupNavLinks();
  }

  setupMobileMenu() {
    // Toggle mobile menu with animation
    this.navToggle.addEventListener('click', () => {
      this.navMenu.classList.toggle('active');
      const isActive = this.navMenu.classList.contains('active');
      this.navToggle.setAttribute('aria-expanded', isActive);
      
      // Animate hamburger icon
      if (isActive) {
        this.navToggle.classList.add('active');
      } else {
        this.navToggle.classList.remove('active');
      }
    });

    // Close menu when link is clicked
    const navLinks = this.navMenu.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        this.navMenu.classList.remove('active');
        this.navToggle.setAttribute('aria-expanded', 'false');
        this.navToggle.classList.remove('active');
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.site-nav')) {
        this.navMenu.classList.remove('active');
        this.navToggle.setAttribute('aria-expanded', 'false');
        this.navToggle.classList.remove('active');
      }
    });
  }

  setupStickyHeader() {
    // Use requestAnimationFrame for better performance
    let ticking = false;
    
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const currentScroll = window.pageYOffset;
          
          // Add scroll effect with backdrop blur
          if (currentScroll > this.scrollThreshold) {
            this.siteHeader.classList.add('scrolled');
            this.siteHeader.style.backdropFilter = 'blur(10px)';
            this.siteHeader.style.backgroundColor = 'rgba(26, 26, 46, 0.95)';
          } else {
            this.siteHeader.classList.remove('scrolled');
            this.siteHeader.style.backdropFilter = '';
            this.siteHeader.style.backgroundColor = '';
          }
          
          // Detect scroll direction
          this.isScrollingDown = currentScroll > this.lastScroll;
          
          // Auto-hide on scroll down, show on scroll up
          if (this.isScrollingDown && currentScroll > 100) {
            this.siteHeader.classList.add('nav-hidden');
          } else {
            this.siteHeader.classList.remove('nav-hidden');
          }
          
          this.lastScroll = currentScroll;
          ticking = false;
        });
        
        ticking = true;
      }
    });
  }

  setupDropdowns() {
    const dropdownBtns = document.querySelectorAll('.nav-user');
    
    dropdownBtns.forEach(btn => {
      const dropdownMenu = btn.nextElementSibling;
      
      if (!dropdownMenu || !dropdownMenu.classList.contains('dropdown-menu')) return;
      
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const isExpanded = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', !isExpanded);
        dropdownMenu.classList.toggle('show');
        
        // Rotate arrow
        const arrow = btn.querySelector('.dropdown-arrow');
        if (arrow) {
          arrow.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
        }
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!btn.contains(e.target) && !dropdownMenu.contains(e.target)) {
          btn.setAttribute('aria-expanded', 'false');
          dropdownMenu.classList.remove('show');
          
          const arrow = btn.querySelector('.dropdown-arrow');
          if (arrow) {
            arrow.style.transform = 'rotate(0deg)';
          }
        }
      });
      
      // Prevent dropdown from closing when clicking inside
      dropdownMenu.addEventListener('click', (e) => {
        e.stopPropagation();
      });
      
      // Add hover effect for desktop
      if (window.innerWidth > 768) {
        btn.addEventListener('mouseenter', () => {
          btn.setAttribute('aria-expanded', 'true');
          dropdownMenu.classList.add('show');
          
          const arrow = btn.querySelector('.dropdown-arrow');
          if (arrow) {
            arrow.style.transform = 'rotate(180deg)';
          }
        });
        
        btn.addEventListener('mouseleave', () => {
          // Small delay to allow moving to dropdown
          setTimeout(() => {
            if (!dropdownMenu.matches(':hover')) {
              btn.setAttribute('aria-expanded', 'false');
              dropdownMenu.classList.remove('show');
              
              const arrow = btn.querySelector('.dropdown-arrow');
              if (arrow) {
                arrow.style.transform = 'rotate(0deg)';
              }
            }
          }, 100);
        });
        
        dropdownMenu.addEventListener('mouseleave', () => {
          btn.setAttribute('aria-expanded', 'false');
          dropdownMenu.classList.remove('show');
          
          const arrow = btn.querySelector('.dropdown-arrow');
          if (arrow) {
            arrow.style.transform = 'rotate(0deg)';
          }
        });
      }
    });
  }

  setupSearchToggle() {
    const searchToggle = document.getElementById('search-toggle');
    const searchDropdown = document.getElementById('search-dropdown');
    
    if (!searchToggle || !searchDropdown) return;
    
    searchToggle.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      searchDropdown.classList.toggle('show');
      
      // Focus input when opened
      if (searchDropdown.classList.contains('show')) {
        const input = searchDropdown.querySelector('input');
        if (input) {
          setTimeout(() => input.focus(), 100);
        }
      }
    });
    
    // Close search dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!searchToggle.contains(e.target) && !searchDropdown.contains(e.target)) {
        searchDropdown.classList.remove('show');
      }
    });
    
    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && searchDropdown.classList.contains('show')) {
        searchDropdown.classList.remove('show');
      }
    });
  }

  setupNavLinks() {
    // Add hover effects to nav links
    const navLinks = document.querySelectorAll('.nav-link:not(.nav-user):not(.nav-cta)');
    
    navLinks.forEach(link => {
      link.addEventListener('mouseenter', () => {
        link.style.color = 'var(--color-accent)';
      });
      
      link.addEventListener('mouseleave', () => {
        link.style.color = '';
      });
    });
    
    // Add special hover effect for CTA button
    const ctaButton = document.querySelector('.nav-link.nav-cta');
    if (ctaButton) {
      ctaButton.addEventListener('mouseenter', () => {
        ctaButton.style.transform = 'translateY(-2px)';
        ctaButton.style.boxShadow = '0 4px 12px rgba(233, 69, 96, 0.3)';
      });
      
      ctaButton.addEventListener('mouseleave', () => {
        ctaButton.style.transform = '';
        ctaButton.style.boxShadow = '';
      });
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Navbar;
}