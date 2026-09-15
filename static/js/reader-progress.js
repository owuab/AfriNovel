/**
 * Reader Progress Module
 * Handles reading progress tracking, scroll position, and progress bar
 */

class ReaderProgress {
  constructor(options = {}) {
    this.progressFill = document.getElementById('progressFill');
    this.readerContent = document.getElementById('readerContent');
    this.bookSlug = options.bookSlug;
    this.bookId = options.bookId;
    this.chapterNumber = options.chapterNumber;
    
    this.lastScrollY = 0;
    this.saveTimeout = null;
    this.throttleDelay = 1500; // Save progress every 1.5 seconds
    
    this.init();
  }

  init() {
    if (!this.progressFill) return;
    
    this.setupScrollTracking();
    this.setupKeyboardNavigation();
    this.loadProgress();
  }

  setupScrollTracking() {
    window.addEventListener('scroll', () => {
      this.updateProgressBar();
      this.throttledSaveProgress();
    });
  }

  updateProgressBar() {
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const currentScroll = window.pageYOffset;
    const progress = maxScroll > 0 ? (currentScroll / maxScroll) * 100 : 0;
    
    if (this.progressFill) {
      this.progressFill.style.width = `${Math.min(progress, 100)}%`;
    }
  }

  throttledSaveProgress() {
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }
    
    this.saveTimeout = setTimeout(() => {
      this.saveProgress();
    }, this.throttleDelay);
  }

  saveProgress() {
    const scrollPosition = window.pageYOffset;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const percentage = maxScroll > 0 ? (scrollPosition / maxScroll) * 100 : 0;
    
    const progressData = {
      bookSlug: this.bookSlug,
      bookId: this.bookId,
      chapterNumber: this.chapterNumber,
      scrollPosition: scrollPosition,
      percentage: Math.round(percentage),
      timestamp: new Date().toISOString()
    };
    
    // Save to localStorage for guests
    localStorage.setItem('afrinovel_reading_progress', JSON.stringify(progressData));
    
    // If user is authenticated, save to server
    if (this.bookSlug && this.chapterNumber) {
      this.saveToServer(progressData);
    }
  }

  async saveToServer(progressData) {
    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      
      // Use the correct API endpoint pattern: /api/books/<book_id>/progress/
      // Since we're working with slugs, we need to get the book ID from the page or use a different approach
      // For now, we'll save to localStorage and implement server-side saving when the endpoint is available
      const bookId = this.readerContent?.dataset.bookId;
      
      if (bookId) {
        const response = await fetch(`/api/books/${bookId}/progress/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(progressData)
        });
        
        if (response.ok) {
          console.log('Reading progress saved to server');
        }
      } else {
        console.log('Book ID not found, progress saved to localStorage only');
      }
    } catch (error) {
      console.error('Failed to save reading progress:', error);
    }
  }

  loadProgress() {
    // Load from localStorage
    const savedProgress = localStorage.getItem('afrinovel_reading_progress');
    if (savedProgress) {
      try {
        const progress = JSON.parse(savedProgress);
        
        // Check if this is the same book and chapter (use bookId if available, otherwise slug)
        const matchesBook = this.bookId ? progress.bookId === this.bookId : progress.bookSlug === this.bookSlug;
        
        if (matchesBook && progress.chapterNumber === this.chapterNumber) {
          this.restoreScrollPosition(progress.scrollPosition);
          this.showContinueOption(progress);
        }
      } catch (error) {
        console.error('Failed to load reading progress:', error);
      }
    }
  }

  restoreScrollPosition(scrollPosition) {
    if (scrollPosition > 0) {
      setTimeout(() => {
        window.scrollTo(0, scrollPosition);
      }, 100);
    }
  }

  showContinueOption(progress) {
    if (progress.percentage > 10) {
      // Use the global toast manager if available
      if (typeof toast !== 'undefined' && toast.show) {
        toast.show(`Continue from ${progress.percentage}%`, 'info', 5000);
      } else {
        // Fallback to inline toast
        const toast = document.createElement('div');
        toast.className = 'toast show';
        toast.textContent = `Continue from ${progress.percentage}%`;
        toast.style.cssText = `
          position: fixed;
          bottom: 80px;
          right: 20px;
          background: var(--color-accent);
          color: white;
          padding: 12px 16px;
          border-radius: 8px;
          z-index: 1000;
          animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
          toast.style.opacity = '0';
          setTimeout(() => toast.remove(), 300);
        }, 3000);
      }
    }
  }

  setupKeyboardNavigation() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        const prevBtn = document.getElementById('prevChapter') || document.getElementById('prevChapterBottom');
        if (prevBtn) prevBtn.click();
      } else if (e.key === 'ArrowRight') {
        const nextBtn = document.getElementById('nextChapter') || document.getElementById('nextChapterBottom');
        if (nextBtn) nextBtn.click();
      }
    });
  }

  getProgress() {
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const currentScroll = window.pageYOffset;
    return maxScroll > 0 ? Math.round((currentScroll / maxScroll) * 100) : 0;
  }
}

// Auto-initialize on reader pages
document.addEventListener('DOMContentLoaded', () => {
  const readerContent = document.getElementById('readerContent');
  if (readerContent) {
    // Extract book and chapter info from data attributes or URL
    const bookSlug = readerContent.dataset.bookSlug;
    const bookId = readerContent.dataset.bookId;
    const chapterNumber = readerContent.dataset.chapterNumber;
    
    new ReaderProgress({ bookSlug, bookId, chapterNumber });
  }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ReaderProgress;
}