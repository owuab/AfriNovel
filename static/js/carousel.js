/**
 * Carousel Module
 * Handles hero carousel and book carousels
 */

class Carousel {
  constructor(container, options = {}) {
    this.container = container;
    this.slides = container.querySelectorAll('.hero-slide, .carousel-slide');
    this.indicators = container.querySelectorAll('.hero-indicator, .carousel-indicator');
    this.prevBtn = container.querySelector('.prev-slide, .carousel-prev');
    this.nextBtn = container.querySelector('.next-slide, .carousel-next');
    
    this.options = {
      autoPlay: options.autoPlay || true,
      interval: options.interval || 5000,
      pauseOnHover: options.pauseOnHover !== false,
      ...options
    };
    
    this.currentSlide = 0;
    this.autoPlayInterval = null;
    
    if (this.slides.length > 0) {
      this.init();
    }
  }

  init() {
    this.showSlide(0);
    this.setupControls();
    
    if (this.options.autoPlay && this.slides.length > 1) {
      this.startAutoPlay();
      
      if (this.options.pauseOnHover) {
        this.container.addEventListener('mouseenter', () => this.stopAutoPlay());
        this.container.addEventListener('mouseleave', () => this.startAutoPlay());
      }
    }
  }

  showSlide(index) {
    this.slides.forEach((slide, i) => {
      slide.classList.remove('active');
      if (this.indicators[i]) {
        this.indicators[i].classList.remove('active');
      }
    });
    
    if (this.slides[index]) {
      this.slides[index].classList.add('active');
    }
    if (this.indicators[index]) {
      this.indicators[index].classList.add('active');
    }
    
    this.currentSlide = index;
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
    this.showSlide(index);
  }

  setupControls() {
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', () => {
        this.prevSlide();
        this.restartAutoPlay();
      });
    }

    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', () => {
        this.nextSlide();
        this.restartAutoPlay();
      });
    }

    this.indicators.forEach((indicator, index) => {
      indicator.addEventListener('click', () => {
        this.goToSlide(index);
        this.restartAutoPlay();
      });
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
    this.slides.forEach(slide => slide.classList.remove('active'));
    this.indicators.forEach(indicator => indicator.classList.remove('active'));
  }
}

// Auto-initialize carousels on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const heroCarousels = document.querySelectorAll('.hero-carousel');
  heroCarousels.forEach(carousel => {
    new Carousel(carousel, {
      autoPlay: true,
      interval: 5000,
      pauseOnHover: true
    });
  });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Carousel;
}