# AfriNovel Admin UI Handoff

## Status

The Django admin shell now uses one shared visual system across the custom dashboard, Django changelists, forms, login, reports, users, and permission views.

Primary implementation files:

- [templates/admin/base.html](templates/admin/base.html): semantic shell, navigation, search, theme control, and content blocks.
- [templates/admin/base_site.html](templates/admin/base_site.html): Django title integration.
- [static/admin/admin.css](static/admin/admin.css): tokens, components, responsive layout, dark theme, RTL hooks, and Django selector overrides.
- [static/admin/admin.js](static/admin/admin.js): persisted theme and accessible mobile navigation.
- [design-system/tokens.css](design-system/tokens.css): prototype/design-source tokens aligned with production CSS.
- `design-system/`: equivalent high-fidelity screen and component-library deliverable; serve it with `python -m http.server 8001` from that directory.

## Visual system

- Palette: warm paper background, deep evergreen navigation, coral focus/accent, semantic success/warning/danger states.
- Typography: DM Sans when installed, with Aptos and Segoe UI fallbacks.
- Spacing: 4, 8, 12, 16, 20, 24, 32, 40, 48px.
- Shape: 8px controls and 10px panels; shadows are reserved for elevated tools.
- Components: sidebar, topbar/search, metric card, panel, data table, filter panel, form controls, status badge, button, auth panel.
- Icons: compact controls use accessible text alternatives and `aria-hidden` glyphs; navigation labels remain visible for recognition and localization.

## Accessibility and responsive behavior

- Skip link, semantic `nav`, `main`, search landmark, button labels, and focus-visible rings are included in the shared shell.
- Text and controls use theme variables with AA-oriented contrast values; verify final contrast after branding changes.
- Mobile navigation is keyboard-toggleable with `aria-expanded` and `aria-controls`.
- `prefers-reduced-motion` disables transitions and animations.
- `dir="rtl"` is emitted from `LANGUAGE_CODE` for Arabic, Hebrew, Farsi, and Urdu and mirrors the mobile sidebar direction.

## Static pipeline

Development serves `static/` through Django's staticfiles configuration. For deployment:

```bash
python manage.py collectstatic --noinput
```

Configure `STATIC_ROOT` and serve the collected directory from the web server/CDN. Keep the query-string version on `admin.css` in the base template, or replace it with a build hash when a bundler is introduced. A bundler is optional for this implementation; if webpack/Vite is adopted, keep `admin.css` and `admin.js` as the generated entry points and preserve Django's `{% static %}` references.

## Rollout and rollback

1. Review the design-system screens and run the existing admin smoke test.
2. Deploy static assets and templates to staging.
3. Check dashboard, index, changelist, add/change form, login, reports, users, permissions, logout, and password change with staff and superuser accounts.
4. Run keyboard, axe/WCAG, RTL, and responsive checks at 375px, 768px, 1280px, and 1440px.
5. Promote after confirming `collectstatic` output and cache invalidation.

Rollback is a template/static asset rollback only: restore the previous `base.html`, `admin.css`, `admin.js`, and token file, then run `collectstatic` again. No database migration or permission change is required.

## Acceptance checklist

- [ ] No default Django blue header, gradients, or unstyled form controls remain in scoped admin views.
- [ ] Existing admin URLs, permissions, POST actions, CSRF tokens, and template blocks continue to work.
- [ ] Light/dark themes persist per browser and remain readable.
- [ ] Keyboard traversal has a visible focus indicator and no focus trap.
- [ ] Tables scroll horizontally on narrow screens without changing column meaning.
- [ ] Chrome, Edge, Firefox, and Safari smoke-tested.
- [ ] Axe scan has no critical or serious findings.
- [ ] CSS and JS remain below the agreed page budget; current files are dependency-free and cacheable.

## Estimates

- Staging visual and responsive QA: 0.5-1 day.
- Accessibility and cross-browser verification: 0.5-1 day.
- Optional icon/font asset packaging: 0.5 day.
- Optional bundler integration: 1 day, only if the deployment pipeline requires it.
