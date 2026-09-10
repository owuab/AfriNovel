#!/usr/bin/env python3
"""
BookClub Template Migration Script
Automates migration of templates from inline styles to design system

Run: python migrate_templates.py
"""

import os
import re
from pathlib import Path

# Template directory
TEMPLATE_DIR = Path("templates/books")
EXCLUDED = {"base.html", "login.html", "signup.html", "_community_nav.html"}

# Pattern to detect standalone HTML templates
STANDALONE_PATTERN = r'<!DOCTYPE html>'

# Migration template - Use this structure for all templates
MIGRATION_TEMPLATE = '''{% extends "base.html" %}

{% block title %}{TITLE} | BookClub{% endblock %}

{% block extra_css %}
<style>
  /* Page-specific styles only - use CSS custom properties from design system */
  .{PAGE_CLASS} {{
    /* Override specific colors and layouts */
  }}
</style>
{% endblock %}

{% block content %}
<div class="container">
  {CONTENT}
</div>
{% endblock %}
'''

def analyze_template(template_path: Path) -> dict:
    """Analyze a template to extract key information"""
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title
    title_match = re.search(r'<title>([^<]+)<', content)
    title = title_match.group(1) if title_match else template_path.stem.replace('_', ' ').title()
    
    # Check if standalone
    is_standalone = bool(re.search(STANDALONE_PATTERN, content))
    
    # Count inline styles
    inline_styles = len(re.findall(r'<style', content))
    
    # Count lines
    lines = len(content.split('\n'))
    
    return {
        'path': str(template_path),
        'title': title,
        'is_standalone': is_standalone,
        'inline_styles': inline_styles,
        'lines': lines,
        'size_kb': os.path.getsize(template_path) / 1024
    }

def generate_migration_report():
    """Generate a report of templates needing migration"""
    templates = sorted([
        f for f in TEMPLATE_DIR.glob('*.html') 
        if f.name not in EXCLUDED
    ])
    
    print("=" * 80)
    print("BOOKCLUB TEMPLATE MIGRATION REPORT")
    print("=" * 80)
    print(f"\nFound {len(templates)} templates to migrate:\n")
    
    priority_high = []
    priority_medium = []
    priority_low = []
    
    for template in templates:
        info = analyze_template(template)
        
        # Categorize by complexity
        if info['lines'] > 400 or info['inline_styles'] > 3:
            priority_high.append(info)
        elif info['lines'] > 200:
            priority_medium.append(info)
        else:
            priority_low.append(info)
    
    print("HIGH PRIORITY (Complex templates):")
    print("-" * 80)
    for info in sorted(priority_high, key=lambda x: x['lines'], reverse=True):
        print(f"  {info['path']:50} {info['lines']:4d} lines  {info['size_kb']:6.1f} KB")
    
    print(f"\nMEDIUM PRIORITY (Medium templates):")
    print("-" * 80)
    for info in sorted(priority_medium, key=lambda x: x['lines'], reverse=True):
        print(f"  {info['path']:50} {info['lines']:4d} lines  {info['size_kb']:6.1f} KB")
    
    print(f"\nLOW PRIORITY (Simple templates):")
    print("-" * 80)
    for info in sorted(priority_low, key=lambda x: x['lines'], reverse=True):
        print(f"  {info['path']:50} {info['lines']:4d} lines  {info['size_kb']:6.1f} KB")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {len(priority_high)} high, {len(priority_medium)} medium, {len(priority_low)} low priority")
    print("=" * 80)
    
    return {
        'high': priority_high,
        'medium': priority_medium,
        'low': priority_low
    }

def print_migration_steps():
    """Print step-by-step migration instructions"""
    print("\n" + "=" * 80)
    print("TEMPLATE MIGRATION STEPS")
    print("=" * 80)
    
    steps = """
1. FOR EACH TEMPLATE FILE:
   
   a) Open the template in your editor
   
   b) Replace the header with:
      {% extends "base.html" %}
      {% load static %}
      
      {% block title %}PAGE_TITLE | BookClub{% endblock %}
      
      {% block extra_css %}
      <style>
        /* Page-specific CSS only */
      </style>
      {% endblock %}
      
      {% block content %}
      ...your content here...
      {% endblock %}
   
   c) Remove all <html>, <head>, <body> tags
   
   d) Remove the <style> tag with CSS variables (:root section)
   
   e) Replace color references:
      - #7a4c3d   → var(--color-accent)
      - #f5f1e8   → var(--color-bg-primary)
      - #fbf9f5   → var(--color-bg-secondary)
      - #ffffff   → var(--color-bg-tertiary)
      - #1f2a2e   → var(--color-text-primary)
      - #5d6a6f   → var(--color-text-secondary)
   
   f) Replace spacing with design tokens:
      - 24px      → var(--spacing-6)
      - 16px      → var(--spacing-4)
      - 12px      → var(--spacing-3)
      - 8px       → var(--spacing-2)
   
   g) Update buttons to use .button class:
      <button class="button">Click</button>
      <button class="button button-secondary">Secondary</button>
      <a href="#" class="button button-outline">Outline</a>
   
   h) Update forms to use .form-group wrapper:
      <div class="form-group">
        <label for="field">Label</label>
        <input type="text" id="field">
      </div>
   
   i) Wrap content in container:
      <div class="container">
        Your content
      </div>
   
   j) Test in browser - verify styling is correct

2. CSS USAGE GUIDELINES:

   Use CSS custom properties instead of hardcoded colors:
   ✅ color: var(--color-text-primary)
   ❌ color: #1f2a2e
   
   Use spacing tokens instead of pixels:
   ✅ padding: var(--spacing-4)
   ❌ padding: 16px
   
   Use utility classes for common patterns:
   ✅ <div class="text-center d-flex gap-4">
   ❌ <div style="text-align: center; display: flex; gap: 16px;">
   
   Common utility classes:
   - d-flex, d-grid, d-none, d-block
   - text-center, text-muted, text-success
   - font-bold, font-semibold, font-medium
   - ml-auto, mr-auto, mt-auto, mb-auto
   - gap-2, gap-4, gap-6
   - sr-only (screen reader only)

3. TESTING CHECKLIST:

   After migration, test:
   ☐ Page loads without console errors
   ☐ CSS styles are applied correctly
   ☐ Colors match design system tokens
   ☐ Responsive design works (test on mobile)
   ☐ Forms and buttons work
   ☐ Links have proper hover states
   ☐ Focus states are visible (tab through page)
   ☐ Print styles work (Ctrl+P)
   ☐ No layout shifts when CSS loads

4. BATCH MIGRATION (for similar templates):
   
   Use find-and-replace for common patterns:
   - Find: style="color: #7a4c3d"
   - Replace: style="color: var(--color-accent)"
   
   - Find: border: 1px solid #e7dfd2
   - Replace: border: 1px solid var(--color-border)"
   
   - Find: padding: 24px
   - Replace: padding: var(--spacing-6)

5. PRIORITY ORDER:

   Start with HIGH PRIORITY (complex templates):
   - Will impact user experience the most
   - May have complex styling that needs careful migration
   - Take most time
   
   Then MEDIUM PRIORITY:
   - Standard page templates
   - Should migrate quickly once pattern is understood
   
   Finally LOW PRIORITY:
   - Simple templates
   - Quick wins, good for building momentum
"""
    print(steps)

if __name__ == '__main__':
    import sys
    
    print("\n🎨 BookClub Design System Template Migration Tool\n")
    
    # Generate report
    results = generate_migration_report()
    
    # Print instructions
    print_migration_steps()
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("""
1. Follow the migration steps for each template
2. Start with HIGH PRIORITY templates
3. Test each migrated template in the browser
4. Use the design system guide: DESIGN_SYSTEM_GUIDE.md
5. Reference working templates: login.html, base.html
6. Submit screenshots/tests to verify styling

For help:
- DESIGN_SYSTEM_GUIDE.md - Complete design system documentation
- templates/base.html - Base template structure
- static/css/design-system.css - Available colors, sizes, spacing
- static/css/layout.css - Layout components and utilities
""")
    print("=" * 80 + "\n")
