document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.querySelector('[data-theme-toggle]');
  const root = document.documentElement;

  const applyTheme = (theme) => {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    root.setAttribute('data-theme', resolved);
    if (themeToggle) {
      themeToggle.textContent = resolved === 'dark' ? '☀' : '☾';
    }
  };

  const saved = localStorage.getItem('bookclub-design-theme');
  applyTheme(saved || 'light');

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      localStorage.setItem('bookclub-design-theme', next);
      applyTheme(next);
    });
  }

  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', () => {
      document.querySelectorAll('.nav-link').forEach((el) => el.classList.remove('is-active'));
      link.classList.add('is-active');
    });
  });
});
