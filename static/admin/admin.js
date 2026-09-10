document.addEventListener('DOMContentLoaded', () => {
  const root = document.body;
  const toggle = document.querySelector('[data-theme-toggle]');
  const sidebarToggle = document.querySelector('[aria-controls="admin-sidebar"]');
  const sidebar = document.querySelector('.sidebar');

  const applyTheme = (theme) => {
    root.setAttribute('data-theme', theme);
    if (toggle) {
      toggle.innerHTML = '<span class="ui-icon ui-icon-theme" aria-hidden="true"></span>';
    }
  };

  const savedTheme = localStorage.getItem('bookclub-admin-theme');
  if (savedTheme) {
    applyTheme(savedTheme);
  }

  if (toggle) {
    toggle.addEventListener('click', () => {
      const nextTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      localStorage.setItem('bookclub-admin-theme', nextTheme);
      applyTheme(nextTheme);
    });
  }

  if (sidebarToggle && sidebar) {
    sidebar.id = 'admin-sidebar';
    sidebarToggle.addEventListener('click', () => {
      const isOpen = root.classList.toggle('sidebar-open');
      sidebarToggle.setAttribute('aria-expanded', String(isOpen));
    });
  }

  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach((item) => {
    item.addEventListener('click', () => {
      navItems.forEach((entry) => entry.classList.remove('active'));
      item.classList.add('active');
    });
  });
});
