/**
 * AJAX Utility Module
 * Handles asynchronous requests with CSRF protection and error handling
 */

class AjaxHelper {
  constructor() {
    this.getCSRFToken();
  }

  getCSRFToken() {
    this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    // If not found in form, try to get from cookie
    if (!this.csrfToken) {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
          this.csrfToken = value;
          break;
        }
      }
    }
  }

  async get(url, options = {}) {
    return this.request(url, {
      method: 'GET',
      ...options
    });
  }

  async post(url, data, options = {}) {
    return this.request(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfToken
      },
      body: JSON.stringify(data),
      ...options
    });
  }

  async put(url, data, options = {}) {
    return this.request(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfToken
      },
      body: JSON.stringify(data),
      ...options
    });
  }

  async delete(url, options = {}) {
    return this.request(url, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': this.csrfToken
      },
      ...options
    });
  }

  async request(url, options = {}) {
    const defaultOptions = {
      headers: {
        'Accept': 'application/json'
      }
    };

    const finalOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers
      }
    };

    try {
      const response = await fetch(url, finalOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      console.error('AJAX request failed:', error);
      throw error;
    }
  }

  // Debounce utility for search and other input events
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Throttle utility for scroll events
  throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AjaxHelper;
}

// Global AJAX helper instance for use in browser
window.ajax = new AjaxHelper();