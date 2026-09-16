/**
 * Novels Catalogue - Dynamic JavaScript-rendered catalogue
 */

class NovelsCatalogue {
  constructor() {
    this.apiEndpoint = '/api/novels/';
    this.grid = document.getElementById('novels-grid');
    this.pagination = document.getElementById('pagination');
    this.searchInput = document.getElementById('search-input');
    this.genreFilter = document.getElementById('genre-filter');
    this.statusFilter = document.getElementById('status-filter');
    this.sortFilter = document.getElementById('sort-filter');
    this.resultsTitle = document.getElementById('results-title');
    this.resultsCount = document.getElementById('results-count');
    
    this.state = {
      page: 1,
      pageSize: 24,
      search: '',
      genre: '',
      status: '',
      sort: 'trending',
      total: 0,
      totalPages: 0,
      isLoading: false
    };
    
    this.genres = [];
    this.debounceTimer = null;
    
    this.init();
  }

  init() {
    this.loadGenres();
    this.setupEventListeners();
    this.loadFromURL();
    this.fetchNovels();
  }

  setupEventListeners() {
    // Search with debouncing
    this.searchInput.addEventListener('input', () => {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.state.search = this.searchInput.value.trim();
        this.state.page = 1;
        this.updateURL();
        this.fetchNovels();
      }, 300);
    });

    // Genre filter
    this.genreFilter.addEventListener('change', () => {
      this.state.genre = this.genreFilter.value;
      this.state.page = 1;
      this.updateURL();
      this.fetchNovels();
    });

    // Status filter
    this.statusFilter.addEventListener('change', () => {
      this.state.status = this.statusFilter.value;
      this.state.page = 1;
      this.updateURL();
      this.fetchNovels();
    });

    // Sort filter
    this.sortFilter.addEventListener('change', () => {
      this.state.sort = this.sortFilter.value;
      this.state.page = 1;
      this.updateURL();
      this.fetchNovels();
    });

    // Handle browser back/forward
    window.addEventListener('popstate', () => {
      this.loadFromURL();
      this.fetchNovels();
    });
  }

  loadFromURL() {
    const params = new URLSearchParams(window.location.search);
    this.state.search = params.get('search') || '';
    this.state.genre = params.get('genre') || '';
    this.state.status = params.get('status') || '';
    this.state.sort = params.get('sort') || 'trending';
    this.state.page = parseInt(params.get('page')) || 1;

    // Update UI elements
    this.searchInput.value = this.state.search;
    this.genreFilter.value = this.state.genre;
    this.statusFilter.value = this.state.status;
    this.sortFilter.value = this.state.sort;
  }

  updateURL() {
    const params = new URLSearchParams();
    if (this.state.search) params.set('search', this.state.search);
    if (this.state.genre) params.set('genre', this.state.genre);
    if (this.state.status) params.set('status', this.state.status);
    if (this.state.sort !== 'trending') params.set('sort', this.state.sort);
    if (this.state.page > 1) params.set('page', this.state.page);
    
    const newURL = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;
    window.history.pushState({}, '', newURL);
  }

  async loadGenres() {
    try {
      const response = await fetch(this.apiEndpoint);
      const data = await response.json();
      if (data.genres) {
        this.genres = data.genres;
        this.populateGenreFilter();
      }
    } catch (error) {
      console.error('Error loading genres:', error);
    }
  }

  populateGenreFilter() {
    this.genreFilter.innerHTML = '<option value="">All Genres</option>';
    this.genres.forEach(genre => {
      const option = document.createElement('option');
      option.value = genre.slug;
      option.textContent = `${genre.name} (${genre.book_count})`;
      this.genreFilter.appendChild(option);
    });
    this.genreFilter.value = this.state.genre;
  }

  async fetchNovels() {
    if (this.state.isLoading) return;
    
    this.state.isLoading = true;
    this.renderSkeleton();
    
    try {
      const params = new URLSearchParams({
        page: this.state.page,
        page_size: this.state.pageSize,
        search: this.state.search,
        genre: this.state.genre,
        status: this.state.status,
        sort: this.state.sort
      });

      const response = await fetch(`${this.apiEndpoint}?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      this.state.total = data.total;
      this.state.totalPages = data.total_pages;
      
      this.updateResultsInfo(data);
      this.renderNovels(data.results);
      this.renderPagination(data);
      
    } catch (error) {
      console.error('Error fetching novels:', error);
      this.renderError();
    } finally {
      this.state.isLoading = false;
    }
  }

  updateResultsInfo(data) {
    // Update title
    if (this.state.search) {
      this.resultsTitle.textContent = `Results for "${this.state.search}"`;
    } else {
      this.resultsTitle.textContent = 'All Novels';
    }
    
    // Update count
    this.resultsCount.textContent = `${data.total} novels found`;
  }

  renderSkeleton() {
    this.grid.innerHTML = '';
    for (let i = 0; i < 6; i++) {
      const skeleton = document.createElement('div');
      skeleton.className = 'skeleton-card';
      skeleton.innerHTML = `
        <div class="skeleton-cover"></div>
        <div class="skeleton-content">
          <div class="skeleton-title"></div>
          <div class="skeleton-meta"></div>
        </div>
      `;
      this.grid.appendChild(skeleton);
    }
  }

  renderNovels(novels) {
    this.grid.innerHTML = '';
    
    if (novels.length === 0) {
      this.renderEmptyState();
      return;
    }
    
    novels.forEach(novel => {
      const card = this.createNovelCard(novel);
      this.grid.appendChild(card);
    });
  }

  createNovelCard(novel) {
    const card = document.createElement('a');
    card.href = novel.url;
    card.className = 'novel-card';
    
    const coverHtml = novel.cover_url 
      ? `<img src="${novel.cover_url}" alt="${novel.title}" loading="lazy">`
      : `<div class="novel-card-cover-placeholder" style="background: ${novel.cover_color}"></div>`;
    
    const statusHtml = novel.novel_status ? 
      `<span class="novel-card-status ${novel.novel_status}">${novel.novel_status}</span>` : '';
    
    const ratingHtml = novel.rating > 0 ? 
      `<span class="novel-card-rating">★ ${novel.rating.toFixed(1)}</span>` : '';
    
    const genresHtml = novel.genres && novel.genres.length > 0 
      ? `<div class="novel-card-genres">
          ${novel.genres.slice(0, 2).map(g => `<span class="novel-card-genre">${g.name}</span>`).join('')}
         </div>` : '';
    
    card.innerHTML = `
      <div class="novel-card-cover">
        ${coverHtml}
        ${statusHtml}
      </div>
      <div class="novel-card-content">
        <h3 class="novel-card-title">${novel.title}</h3>
        <div class="novel-card-author">${novel.author}</div>
        <div class="novel-card-meta">
          ${ratingHtml}
          <span>${novel.chapter_count} chapters</span>
        </div>
        ${genresHtml}
      </div>
    `;
    
    return card;
  }

  renderEmptyState() {
    this.grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <h3>No novels found</h3>
        <p>Try changing your search or filters</p>
      </div>
    `;
  }

  renderError() {
    this.grid.innerHTML = `
      <div class="error-state">
        <h3>Unable to load novels</h3>
        <p>Please try again later</p>
        <button class="retry-button" onclick="window.location.reload()">Retry</button>
      </div>
    `;
  }

  renderPagination(data) {
    this.pagination.innerHTML = '';
    
    if (this.state.totalPages <= 1) return;
    
    // Previous button
    const prevButton = document.createElement('button');
    prevButton.textContent = 'Previous';
    prevButton.disabled = !data.has_previous;
    prevButton.onclick = () => {
      if (this.state.page > 1) {
        this.state.page--;
        this.updateURL();
        this.fetchNovels();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    };
    this.pagination.appendChild(prevButton);
    
    // Page numbers
    const maxVisiblePages = 5;
    let startPage = Math.max(1, this.state.page - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(this.state.totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
      const pageButton = document.createElement('button');
      pageButton.textContent = i;
      if (i === this.state.page) {
        pageButton.className = 'active';
      }
      pageButton.onclick = () => {
        this.state.page = i;
        this.updateURL();
        this.fetchNovels();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      };
      this.pagination.appendChild(pageButton);
    }
    
    // Next button
    const nextButton = document.createElement('button');
    nextButton.textContent = 'Next';
    nextButton.disabled = !data.has_next;
    nextButton.onclick = () => {
      if (this.state.page < this.state.totalPages) {
        this.state.page++;
        this.updateURL();
        this.fetchNovels();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    };
    this.pagination.appendChild(nextButton);
  }
}

// Initialize the catalogue when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new NovelsCatalogue();
});