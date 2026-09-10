# BookClub Admin Design System

This package is a Figma-style export set and multi-page Storybook-style system for the BookClub admin experience.

## Included deliverables

- Design tokens and semantic variables
- Light and dark themes
- Component library patterns
- Multi-page admin dashboard prototypes
- SVG export assets
- Handoff notes for engineering and design

## Pages

- Overview dashboard
- Users management
- Settings
- Activity logs
- CRUD editor
- Storybook gallery index

## Quick start

Open the HTML files directly in a browser, or serve the folder locally:

```bash
cd design-system
python -m http.server 8001
```

Then visit:

- http://localhost:8001/
- http://localhost:8001/pages/overview.html

## Design principles

- Clear information hierarchy
- Strong contrast and accessibility
- Consistent spacing and component states
- Enterprise data-visualisation feel
- No Django admin styling artifacts

## Token map

The core theme variables are defined in `tokens.css` and consumed by the page styles.
