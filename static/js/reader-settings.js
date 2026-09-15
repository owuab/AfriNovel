/**
 * Reader Settings Module
 * Handles reader customization: theme, font size, line height, etc.
 */

class ReaderSettings {
  constructor(options = {}) {
    this.settingsPanel = document.getElementById('settingsPanel');
    this.settingsBtn = document.getElementById('settingsBtn');
    this.readerContent = document.getElementById('readerContent');
    
    this.settings = {
      theme: localStorage.getItem('afrinovel_reader_theme') || 'dark',
      fontSize: localStorage.getItem('afrinovel_reader_fontsize') || '18',
      lineHeight: localStorage.getItem('afrinovel_reader_lineheight') || '1.9',
      contentWidth: localStorage.getItem('afrinovel_reader_width') || '46',
      fontFamily: localStorage.getItem('afrinovel_reader_fontfamily') || 'Georgia, serif'
    };
    
    this.init();
  }

  init() {
    if (!this.settingsPanel || !this.settingsBtn) return;
    
    this.setupPanelToggle();
    this.setupThemeSwitching();
    this.setupFontSize();
    this.setupLineHeight();
    this.setupContentWidth();
    this.setupFontFamily();
    this.applySettings();
  }

  setupPanelToggle() {
    this.settingsBtn.addEventListener('click', () => {
      this.settingsPanel.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!this.settingsPanel.contains(e.target) && !this.settingsBtn.contains(e.target)) {
        this.settingsPanel.classList.remove('open');
      }
    });
  }

  setupThemeSwitching() {
    const themeButtons = document.querySelectorAll('.theme-btn');
    themeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const theme = btn.dataset.theme;
        this.settings.theme = theme;
        this.applyTheme();
        this.saveSettings();
        
        themeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  }

  setupFontSize() {
    const fontSize = document.getElementById('fontSize');
    if (!fontSize) return;
    
    fontSize.value = this.settings.fontSize;
    fontSize.addEventListener('input', () => {
      this.settings.fontSize = fontSize.value;
      this.applyFontSize();
      this.saveSettings();
    });
  }

  setupLineHeight() {
    const lineHeight = document.getElementById('lineHeight');
    if (!lineHeight) return;
    
    lineHeight.value = this.settings.lineHeight;
    lineHeight.addEventListener('input', () => {
      this.settings.lineHeight = lineHeight.value;
      this.applyLineHeight();
      this.saveSettings();
    });
  }

  setupContentWidth() {
    const contentWidth = document.getElementById('contentWidth');
    if (!contentWidth) return;
    
    contentWidth.value = this.settings.contentWidth;
    contentWidth.addEventListener('input', () => {
      this.settings.contentWidth = contentWidth.value;
      this.applyContentWidth();
      this.saveSettings();
    });
  }

  setupFontFamily() {
    const fontFamily = document.getElementById('fontFamily');
    if (!fontFamily) return;
    
    fontFamily.value = this.settings.fontFamily;
    fontFamily.addEventListener('change', () => {
      this.settings.fontFamily = fontFamily.value;
      this.applyFontFamily();
      this.saveSettings();
    });
  }

  applySettings() {
    this.applyTheme();
    this.applyFontSize();
    this.applyLineHeight();
    this.applyContentWidth();
    this.applyFontFamily();
  }

  applyTheme() {
    document.body.classList.remove('theme-sepia', 'theme-dark', 'theme-light');
    if (this.settings.theme !== 'dark') {
      document.body.classList.add(`theme-${this.settings.theme}`);
    }
    
    const activeBtn = document.querySelector(`[data-theme="${this.settings.theme}"]`);
    if (activeBtn) {
      document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
      activeBtn.classList.add('active');
    }
  }

  applyFontSize() {
    document.documentElement.style.setProperty('--reading-size', `${this.settings.fontSize}px`);
  }

  applyLineHeight() {
    document.documentElement.style.setProperty('--reading-leading', this.settings.lineHeight);
  }

  applyContentWidth() {
    document.documentElement.style.setProperty('--reading-width', `${this.settings.contentWidth}rem`);
  }

  applyFontFamily() {
    if (this.readerContent) {
      this.readerContent.style.fontFamily = this.settings.fontFamily;
    }
  }

  saveSettings() {
    localStorage.setItem('afrinovel_reader_theme', this.settings.theme);
    localStorage.setItem('afrinovel_reader_fontsize', this.settings.fontSize);
    localStorage.setItem('afrinovel_reader_lineheight', this.settings.lineHeight);
    localStorage.setItem('afrinovel_reader_width', this.settings.contentWidth);
    localStorage.setItem('afrinovel_reader_fontfamily', this.settings.fontFamily);
  }

  reset() {
    this.settings = {
      theme: 'dark',
      fontSize: '18',
      lineHeight: '1.9',
      contentWidth: '46',
      fontFamily: 'Georgia, serif'
    };
    this.applySettings();
    this.saveSettings();
  }
}

// Auto-initialize on reader pages
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('settingsPanel')) {
    new ReaderSettings();
  }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ReaderSettings;
}