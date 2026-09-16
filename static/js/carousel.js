/**
 * Carousel Module
 * Handles hero carousel and book carousels with enhanced Wuxiaworld-style interactions
 */

class Carousel {
  constructor(container, options = {}) {
    this.container = container;
    this.slides = container.querySelectorAll('.hero-slide, .carousel-slide');
    this.indicators = container.querySelectorAll('.hero-indicator, .carousel-indicator');
    this.prevBtn = container.querySelector('.prev-slide, .carousel-prev');
    this.nextBtn = container.querySelector('.next-slide, .carousel-next');
    
    this.options = {
      autoPlay: options.autoPlay !== false,
      interval: options.interval || 6000,
      pauseOnHover: options.pauseOnHover !== false,
      transitionDuration: options.transitionDuration || 500,
      ...options
    };
    
    this.currentSlide = 0;
    this.autoPlayInterval = null;
    this.isTransitioning = false;
    
    if (this.slides.length > 0) {
      this.init();
    }
  }

  init() {
    this.showSlide(0, false);
    this.setupControls();
    this.setupKeyboardNavigation();
    
    if (this.options.autoPlay && this.slides.length > 1) {
      this.startAutoPlay();
      
      if (this.options.pauseOnHover) {
        this.container.addEventListener('mouseenter', () => this.stopAutoPlay());
        this.container.addEventListener('mouseleave', () => this.startAutoPlay());
      }
    }
  }

  showSlide(index, animate = true) {
    if (this.isTransitioning) return;
    this.isTransitioning = true;
    
    this.slides.forEach((slide, i) => {
      slide.classList.remove('active');
      slide.style.opacity = '0';
      slide.style.transform = 'translateY(20px)';
      
      if (this.indicators[i]) {
        this.indicators[i].classList.remove('active');
      }
    });
    
    if (this.slides[index]) {
      this.slides[index].classList.add('active');
      
      if (animate) {
        // Animate slide in
        setTimeout(() => {
          this.slides[index].style.transition = `opacity ${this.options.transitionDuration}ms ease-in-out, transform ${this.options.transitionDuration}ms ease-in-out`;
          this.slides[index].style.opacity = '1';
          this.slides[index].style.transform = 'translateY(0)';
        }, 50);
      } else {
        this.slides[index].style.opacity = '1';
        this.slides[index].style.transform = 'translateY(0)';
      }
    }
    
    if (this.indicators[index]) {
      this.indicators[index].classList.add('active');
    }
    
    this.currentSlide = index;
    
    // Reset transition lock
    setTimeout(() => {
      this.isTransitioning = false;
    }, this.options.transitionDuration);
  }

  nextSlide() {
    const next = (this.currentSlide + 1) % this.slides.length;
    this.showSlide(next);
  }

  prevSlide() {
    const prev = (this.currentSlide - 1 + this.slides.length) % this.slides.length;
    this.showSlide(prev);
  }

  goToSlide(index) {
    if (index >= 0 && index < this.slides.length) {
      this.showSlide(index);
    }
  }

  setupControls() {
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.prevSlide();
        this.restartAutoPlay();
      });
      
      // Add hover effect
      this.prevBtn.addEventListener('mouseenter', () => {
        this.prevBtn.style.transform = 'scale(1.1)';
      });
      
      this.prevBtn.addEventListener('mouseleave', () => {
        this.prevBtn.style.transform = '';
      });
    }

    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.nextSlide();
        this.restartAutoPlay();
      });
      
      // Add hover effect
      this.nextBtn.addEventListener('mouseenter', () => {
        this.nextBtn.style.transform = 'scale(1.1)';
      });
      
      this.nextBtn.addEventListener('mouseleave', () => {
        this.nextBtn.style.transform = '';
      });
    }

    this.indicators.forEach((indicator, index) => {
      indicator.addEventListener('click', (e) => {
        e.preventDefault();
        this.goToSlide(index);
        this.restartAutoPlay();
      });
      
      // Add hover effect
      indicator.addEventListener('mouseenter', () => {
        indicator.style.transform = 'scale(1.3)';
      });
      
      indicator.addEventListener('mouseleave', () => {
        indicator.style.transform = '';
      });
    });
  }

  setupKeyboardNavigation() {
    this.container.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        this.prevSlide();
        this.restartAutoPlay();
      } else if (e.key === 'ArrowRight') {
        this.nextSlide();
        this.restartAutoPlay();
      }
    });
  }

  startAutoPlay() {
    this.stopAutoPlay();
    this.autoPlayInterval = setInterval(() => this.nextSlide(), this.options.interval);
  }

  stopAutoPlay() {
    if (this.autoPlayInterval) {
      clearInterval(this.autoPlayInterval);
      this.autoPlayInterval = null;
    }
  }

  restartAutoPlay() {
    if (this.options.autoPlay) {
      this.stopAutoPlay();
      this.startAutoPlay();
    }
  }

  destroy() {
    this.stopAutoPlay();
    this.slides.forEach(slide => {
      slide.classList.remove('active');
      slide.style = '';
    });
    this.indicators.forEach(indicator => indicator.classList.remove('active'));
  }
}

// Auto-initialize carousels on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const heroCarousels = document.querySelectorAll('.hero-carousel');
  heroCarousels.forEach(carousel => {
    new Carousel(carousel, {
      autoPlay: true,
      interval: 6000,
      pauseOnHover: true,
      transitionDuration: 500
    });
  });
  
  // Initialize book carousels if they exist
  const bookCarousels = document.querySelectorAll('.book-carousel');
  bookCarousels.forEach(carousel => {
    // Book carousels are horizontal scroll, not auto-playing
    // Just add smooth scroll behavior
    carousel.style.scrollBehavior = 'smooth';
  });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Carousel;
}