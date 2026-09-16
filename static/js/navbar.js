/**
 * Navbar Module
 * Handles navigation, mobile menu, and sticky header behavior
 */

class Navbar {
  constructor() {
    this.navToggle = document.querySelector('.nav-toggle');
    this.navMenu = document.querySelector('.nav-menu');
    this.siteHeader = document.querySelector('.site-header');
    this.lastScroll = 0;
    this.isScrollingDown = false;
    
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
  }

  setupMobileMenu() {
    // Toggle mobile menu
    this.navToggle.addEventListener('click', () => {
      this.navMenu.classList.toggle('active');
      const isActive = this.navMenu.classList.contains('active');
      this.navToggle.setAttribute('aria-expanded', isActive);
    });

    // Close menu when link is clicked
    const navLinks = this.navMenu.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        this.navMenu.classList.remove('active');
        this.navToggle.setAttribute('aria-expanded', 'false');
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.site-nav')) {
        this.navMenu.classList.remove('active');
        this.navToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  setupStickyHeader() {
    window.addEventListener('scroll', () => {
      const currentScroll = window.pageYOffset;
      
      // Add scroll effect
      if (currentScroll > 50) {
        this.siteHeader.classList.add('scrolled');
      } else {
        this.siteHeader.classList.remove('scrolled');
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
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!btn.contains(e.target) && !dropdownMenu.contains(e.target)) {
          btn.setAttribute('aria-expanded', 'false');
          dropdownMenu.classList.remove('show');
        }
      });
      
      // Prevent dropdown from closing when clicking inside
      dropdownMenu.addEventListener('click', (e) => {
        e.stopPropagation();
      });
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
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Navbar;
}