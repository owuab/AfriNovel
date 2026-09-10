# BookClub Design System - Quick Reference

## 🎨 Every New Template Must Do This:

```django
{% extends "base.html" %}
{% load static %}

{% block title %}Page Title | BookClub{% endblock %}

{% block extra_css %}
<style>
  /* Page-specific styles ONLY - use CSS custom properties */
  .page-feature { color: var(--color-accent); }
</style>
{% endblock %}

{% block content %}
<div class="container">
  Your content here
</div>
{% endblock %}
```

---

## 🎯 Essential Color Replacements

When migrating or creating templates, find & replace these colors:

```
#7a4c3d         →  var(--color-accent)
#f5f1e8         →  var(--color-bg-primary)
#fbf9f5         →  var(--color-bg-secondary)
#ffffff         →  var(--color-bg-tertiary)
#1f2a2e         →  var(--color-text-primary)
#5d6a6f         →  var(--color-text-secondary)
#999999         →  var(--color-text-muted)
#2f5d50         →  var(--color-success)
#9d2929         →  var(--color-danger)
#cc8800         →  var(--color-warning)
#1e6b9a         →  var(--color-info)
#e7dfd2         →  var(--color-border)
#f1f1f1         →  var(--color-bg-disabled)
```

---

## 📏 Spacing Replacements

```
2px             →  var(--spacing-0-5)
4px             →  var(--spacing-1)
8px             →  var(--spacing-2)
12px            →  var(--spacing-3)
16px            →  var(--spacing-4)
20px            →  var(--spacing-5)
24px            →  var(--spacing-6)
32px            →  var(--spacing-8)
48px            →  var(--spacing-12)
```

---

## 🔘 Button Classes

```html
<!-- Primary button (default) -->
<button class="button">Click me</button>

<!-- Sizes: small, large (default = base) -->
<button class="button button-sm">Small</button>
<button class="button button-lg">Large</button>

<!-- Variants: secondary, success, danger, outline, link -->
<button class="button button-secondary">Secondary</button>
<button class="button button-success">Success</button>
<button class="button button-danger">Delete</button>
<button class="button button-outline">Outline</button>
<a href="#" class="button button-link">Link Button</a>

<!-- Disabled state -->
<button class="button" disabled>Disabled</button>
```

---

## 📝 Form Components

```html
<!-- Form group - wrap all form fields -->
<div class="form-group">
  <label for="email">Email Address</label>
  <input type="email" id="email" name="email" required>
  <small class="form-help">Help text goes here</small>
</div>

<!-- Error display -->
<div class="form-group">
  <label for="username">Username</label>
  <input type="text" id="username" class="form-error">
  <small class="form-error">Username already taken</small>
</div>

<!-- Checkbox group -->
<div class="form-check">
  <input type="checkbox" id="agree" name="agree">
  <label for="agree">I agree to terms</label>
</div>

<!-- Textarea -->
<div class="form-group">
  <label for="message">Message</label>
  <textarea id="message" rows="4"></textarea>
</div>

<!-- Select -->
<div class="form-group">
  <label for="category">Category</label>
  <select id="category" name="category">
    <option>Choose one...</option>
    <option value="fiction">Fiction</option>
    <option value="nonfiction">Non-Fiction</option>
  </select>
</div>
```

---

## 💬 Messages & Alerts

```html
<!-- Success message (auto-dismiss after 5s) -->
<div class="messages">
  <div class="message message-success">
    ✓ Changes saved successfully
    <button class="message-close" aria-label="Close">×</button>
  </div>
</div>

<!-- Error message -->
<div class="message message-error">
  ✕ Something went wrong
</div>

<!-- Warning message -->
<div class="message message-warning">
  ⚠ Please review before submitting
</div>

<!-- Info message -->
<div class="message message-info">
  ℹ This is helpful information
</div>
```

---

## 🎴 Card Components

```html
<!-- Basic card -->
<div class="card">
  <div class="card-body">
    Card content here
  </div>
</div>

<!-- Card with header and footer -->
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Card Title</h3>
  </div>
  <div class="card-body">
    Main content
  </div>
  <div class="card-footer">
    <button class="button">Action</button>
  </div>
</div>
```

---

## 🔤 Typography Classes

```html
<!-- Headings (h1-h6) -->
<h1>Main Title</h1>
<h2>Section Heading</h2>
<h3>Subsection</h3>

<!-- Text styling -->
<p>Regular paragraph text</p>
<p class="text-muted">Muted secondary text</p>
<p class="text-center">Centered text</p>
<p class="text-success">Success text (green)</p>
<p class="text-danger">Error text (red)</p>

<!-- Font weights -->
<span class="font-semibold">Semibold</span>
<span class="font-bold">Bold text</span>
<span class="font-medium">Medium weight</span>

<!-- Links -->
<a href="#">Normal link</a>
<a href="#" class="button button-link">Link button</a>
```

---

## 🎨 Utility Classes

```html
<!-- Display -->
<div class="d-flex">Flexbox container</div>
<div class="d-grid">CSS Grid container</div>
<div class="d-none">Hidden</div>
<div class="d-block">Block display</div>

<!-- Spacing -->
<div class="gap-2">2 spacing between children</div>
<div class="gap-4">4 spacing between children</div>
<div class="gap-6">6 spacing between children</div>

<!-- Margins -->
<div class="ml-auto">Push to right</div>
<div class="mr-auto">Push to left</div>
<div class="mt-4">Top margin</div>
<div class="mb-6">Bottom margin</div>

<!-- Text alignment -->
<div class="text-center">Center aligned</div>
<div class="text-right">Right aligned</div>
<div class="text-left">Left aligned</div>

<!-- Screen reader only -->
<span class="sr-only">Hidden from view but read by screen readers</span>

<!-- Grid layouts -->
<div class="grid">Default responsive grid</div>
<div class="grid-2">2 columns</div>
<div class="grid-3">3 columns</div>
<div class="grid-4">4 columns</div>

<!-- Responsive visibility -->
<div class="hide-mobile">Hidden on mobile</div>
<div class="show-mobile">Only shown on mobile</div>
```

---

## 🎯 Badges & Status Indicators

```html
<span class="badge">Default</span>
<span class="badge badge-success">Active</span>
<span class="badge badge-danger">Blocked</span>
<span class="badge badge-warning">Pending</span>
```

---

## 📊 Grid & Layouts

```html
<!-- 2-column grid (auto-responsive) -->
<div class="grid-2">
  <div>Column 1</div>
  <div>Column 2</div>
</div>

<!-- 3-column grid -->
<div class="grid-3">
  <div>Col 1</div>
  <div>Col 2</div>
  <div>Col 3</div>
</div>

<!-- 4-column grid -->
<div class="grid-4">
  <div>1</div>
  <div>2</div>
  <div>3</div>
  <div>4</div>
</div>

<!-- Aspect ratio container (for images/videos) -->
<div class="aspect-ratio aspect-ratio-video">
  <img src="..." alt="...">
</div>
```

---

## 🌐 Font Sizes

```html
<p class="text-xs">Extra small</p>
<p class="text-sm">Small</p>
<p class="text-base">Base/Normal</p>
<p class="text-lg">Large</p>
<p class="text-xl">Extra large</p>
<p class="text-2xl">2XL</p>
<p class="text-3xl">3XL</p>
<p class="text-4xl">4XL</p>
```

---

## ✅ Accessibility Checklist

- [ ] All interactive elements have focus states (dotted outline)
- [ ] Color is not the only indicator of status (use icons or text too)
- [ ] Proper heading hierarchy (h1 → h2 → h3, no skipping)
- [ ] Form labels associated with inputs (`for="id"` attribute)
- [ ] Required fields marked with `required` attribute
- [ ] Error messages clearly associated with fields
- [ ] Tab order makes sense (logical page flow)
- [ ] Images have alt text
- [ ] Buttons have clear labels (not just icons)
- [ ] Sufficient color contrast (WCAG AA compliant)

---

## 🧪 Testing After Migration

1. **Visual**: Does layout look correct?
2. **Responsive**: Resize to mobile (576px) - works?
3. **Forms**: Can you fill and submit forms?
4. **Buttons**: Do all buttons work?
5. **Keyboard**: Can you tab through page? Escape key?
6. **Focus**: Can you see where focus is?
7. **Colors**: Do colors match design system?
8. **Console**: Any JavaScript errors?

---

## 📚 References

- **Full Documentation**: `DESIGN_SYSTEM_GUIDE.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **CSS Files**: `static/css/design-system.css` and `layout.css`
- **Base Template**: `templates/base.html`
- **Working Example**: `templates/books/login.html`
- **Migration Tool**: `python migrate_templates.py`

---

## 🚀 Quick Migration Process

```bash
# For each template:
1. Read the current template
2. Copy content between <body> tags
3. Create new file extending base.html
4. Paste content into {% block content %}
5. Replace all color hex codes with CSS variables
6. Replace all pixel spacing with spacing tokens
7. Test in browser (http://localhost:8000/page/)
8. Verify responsive design
9. Check accessibility
```

---

## ⚡ Pro Tips

- **Never** use hex colors directly - always use CSS variables
- **Never** use hardcoded pixels - use spacing tokens
- **Always** extend base.html for new templates
- **Always** wrap content in .container div
- **Always** test responsiveness on mobile
- **Always** verify keyboard navigation works
- Use find-and-replace in VS Code to speed up migrations
- Take screenshots of before/after for validation

---

**Last Updated**: 2026-08-23  
**Design System Version**: 1.0  
**For Updates**: Check DESIGN_SYSTEM_GUIDE.md
