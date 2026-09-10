# BookClub Design System - Implementation Guide

## Overview

The BookClub Design System provides a comprehensive, accessible, and maintainable UI framework for all templates across the application. This guide explains the system's components, how to use them, and best practices.

## Quick Start

### 1. Import the Design System

All templates should extend `base.html`:

```django
{% extends "base.html" %}
{% load static %}

{% block title %}Page Title | BookClub{% endblock %}

{% block content %}
  <!-- Your page content here -->
{% endblock %}
```

### 2. CSS Architecture

- **`design-system.css`** - Core design tokens, typography, forms, and components
- **`layout.css`** - Page layouts, header, footer, navigation, and utilities
- **Page-specific CSS** - Optional custom styles for specific templates

### 3. Avoid Inline Styles

Instead of:
```html
<style>
  .my-class { color: #7a4c3d; }
</style>
```

Use CSS custom properties from the design system:
```css
.my-class {
  color: var(--color-accent);
}
```

Or use utility classes:
```html
<div class="text-accent d-flex gap-4">...</div>
```

## Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg-primary` | #f5f1e8 | Page background |
| `--color-bg-secondary` | #fbf9f5 | Secondary backgrounds |
| `--color-bg-tertiary` | #ffffff | Cards, containers |
| `--color-text-primary` | #1f2a2e | Main text |
| `--color-text-secondary` | #5d6a6f | Secondary text |
| `--color-accent` | #7a4c3d | Primary action/branding |
| `--color-success` | #2f5d50 | Success messages |
| `--color-danger` | #9d2929 | Error messages |
| `--color-warning` | #cc8800 | Warnings |
| `--color-info` | #1e6b9a | Information |

### Typography

| Token | Value |
|-------|-------|
| `--font-family-base` | System font stack |
| `--font-family-serif` | Georgia, Garamond |
| `--font-size-sm` | 0.875rem (14px) |
| `--font-size-base` | 1rem (16px) |
| `--font-size-lg` | 1.125rem (18px) |
| `--font-size-xl` | 1.5rem (24px) |
| `--font-weight-normal` | 400 |
| `--font-weight-bold` | 700 |

### Spacing

Use multiples of 0.25rem:
- `--spacing-2` = 0.5rem
- `--spacing-4` = 1rem
- `--spacing-6` = 1.5rem
- `--spacing-8` = 2rem

### Borders & Radius

- `--border-radius-sm` = 0.25rem
- `--border-radius-md` = 0.5rem
- `--border-radius-lg` = 0.75rem
- `--border-radius-xl` = 1rem

## Components

### Buttons

```html
<!-- Primary Button -->
<button class="button">Click Me</button>

<!-- Secondary Button -->
<button class="button button-secondary">Secondary</button>

<!-- Outline Button -->
<button class="button button-outline">Outline</button>

<!-- Size Variants -->
<button class="button button-sm">Small</button>
<button class="button button-lg">Large</button>

<!-- States -->
<button class="button" disabled>Disabled</button>
```

### Forms

```html
<form>
  <div class="form-group">
    <label for="name">Name <span class="required">*</span></label>
    <input type="text" id="name" name="name" required>
    <div class="form-help">Enter your full name</div>
  </div>

  <div class="form-group">
    <label for="email">Email</label>
    <input type="email" id="email" name="email">
  </div>

  <button type="submit" class="button">Submit</button>
</form>
```

### Cards

```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Card Title</h3>
  </div>
  
  <div class="card-body">
    <p>Card content goes here</p>
  </div>
  
  <div class="card-footer">
    <button class="button button-outline">Cancel</button>
    <button class="button">Save</button>
  </div>
</div>
```

### Messages & Alerts

```html
<!-- Success Message -->
<div class="message message-success">
  <div class="message-icon">✓</div>
  <div class="message-content">Operation completed successfully!</div>
  <button class="message-close" type="button">×</button>
</div>

<!-- Error Message -->
<div class="message message-error">
  <div class="message-icon">✕</div>
  <div class="message-content">Something went wrong. Please try again.</div>
</div>
```

### Badges

```html
<span class="badge">Default</span>
<span class="badge success">Success</span>
<span class="badge danger">Danger</span>
<span class="badge warning">Warning</span>
```

### Grids

```html
<!-- 2-column responsive grid -->
<div class="grid grid-2">
  <div class="card">Item 1</div>
  <div class="card">Item 2</div>
</div>

<!-- 3-column responsive grid -->
<div class="grid grid-3">
  <div class="card">Item 1</div>
  <div class="card">Item 2</div>
  <div class="card">Item 3</div>
</div>
```

## Utility Classes

### Display

```html
<div class="d-none">Hidden</div>
<div class="d-block">Block</div>
<div class="d-flex">Flex</div>
<div class="d-grid">Grid</div>
```

### Spacing

```html
<div class="gap-2">Flex gap 2</div>
<div class="gap-4">Flex gap 4</div>
<div class="gap-6">Flex gap 6</div>
```

### Text

```html
<div class="text-center">Centered text</div>
<div class="text-muted">Muted text</div>
<div class="text-success">Success text</div>
<div class="font-bold">Bold text</div>
```

### Margin

```html
<div class="ml-auto">Left auto margin</div>
<div class="mr-auto">Right auto margin</div>
<div class="mt-auto">Top auto margin</div>
```

## Form Widgets (Django)

Django form fields automatically use the design system styles:

```python
from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(
        label="Your Name",
        max_length=100,
        required=True,
        help_text="Please enter your full name"
    )
    email = forms.EmailField(required=True)
    message = forms.CharField(
        widget=forms.Textarea,
        required=True
    )
```

Template rendering:

```django
{% for field in form %}
  <div class="form-group">
    {{ field.label_tag }}
    {{ field }}
    {% if field.help_text %}
      <div class="form-help">{{ field.help_text|safe }}</div>
    {% endif %}
    {% if field.errors %}
      <div class="form-error">{{ field.errors }}</div>
    {% endif %}
  </div>
{% endfor %}
```

## Accessibility

The design system includes:

- Semantic HTML (`<button>`, `<form>`, `<nav>`)
- Proper ARIA labels and roles
- Focus visible indicators (3px outline)
- Color contrast ratios meeting WCAG AA
- Keyboard navigation support
- Screen reader compatibility

### Best Practices

1. Always use semantic HTML:
   ```html
   <button class="button">Submit</button>  <!-- Good -->
   <div class="button">Submit</div>       <!-- Bad -->
   ```

2. Use proper heading hierarchy:
   ```html
   <h1>Page Title</h1>
   <h2>Section Title</h2>
   <h3>Subsection</h3>
   ```

3. Provide alt text for images:
   ```html
   <img src="book.jpg" alt="Cover of 'The Great Gatsby'">
   ```

4. Label form inputs:
   ```html
   <label for="email">Email Address</label>
   <input type="email" id="email">
   ```

## Responsive Design

The design system is mobile-first. Use media queries for breakpoints:

- **Mobile**: < 576px
- **Tablet**: 576px - 768px
- **Desktop**: 768px - 1200px
- **Large**: 1200px+

Example:

```css
.my-component {
  /* Mobile styles */
}

@media (min-width: 768px) {
  .my-component {
    /* Tablet+ styles */
  }
}
```

## Migration Checklist

When updating an existing template:

- [ ] Change `<!DOCTYPE html>` to `{% extends "base.html" %}`
- [ ] Remove all `<html>`, `<head>`, `<body>` tags
- [ ] Remove inline `<style>` tags
- [ ] Replace inline colors with CSS custom properties
- [ ] Update form markup to use `.form-group`
- [ ] Update buttons to use `.button` class
- [ ] Replace custom navigation with base template nav
- [ ] Add `{% load static %}` for any remaining static references
- [ ] Test on mobile, tablet, and desktop
- [ ] Test keyboard navigation
- [ ] Verify color contrast
- [ ] Test with screen reader

## Example: Converting a Template

### Before

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { color: #1f2a2e; }
    .button { background: #7a4c3d; color: white; }
  </style>
</head>
<body>
  <h1 style="color: #7a4c3d;">My Page</h1>
  <form>
    <input type="text" style="border: 1px solid #e7dfd2;">
  </form>
</body>
</html>
```

### After

```django
{% extends "base.html" %}

{% block title %}My Page | BookClub{% endblock %}

{% block content %}
<div class="container">
  <h1>My Page</h1>
  
  <form>
    <div class="form-group">
      <label for="name">Name</label>
      <input type="text" id="name" name="name">
    </div>
    <button type="submit" class="button">Submit</button>
  </form>
</div>
{% endblock %}
```

## Support & Issues

For design system questions:
1. Check this guide
2. Review `design-system.css` and `layout.css`
3. Reference example templates
4. Ask in team documentation

## Additional Resources

- WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- CSS Custom Properties: https://developer.mozilla.org/en-US/docs/Web/CSS/--*
- Django Form Rendering: https://docs.djangoproject.com/en/stable/topics/forms/#rendering-fields-manually
- Accessible Colors: https://contrast-ratio.com/
