# BookClub Admin UI Handoff

## Overview
This design system is built as a modern enterprise admin dashboard pattern set for BookClub. It removes default Django admin styling and establishes a new multi-page component language for product operations, content management, and user administration.

## Design goals
- Clear hierarchy for operational tasks
- High contrast and accessibility compliance
- Enterprise-grade data density and dashboard behavior
- Responsive behavior across desktop/tablet/mobile
- Semantic, developer-friendly component structure

## Tokens

### Color palette
- Primary: #4F46E5
- Accent: #8B5CF6
- Success: #16A34A
- Warning: #F59E0B
- Danger: #EF4444
- Info: #0EA5E9

### Typography
- Font family: Inter
- Heading scale: 32px, 24px, 20px, 16px
- Body text: 14px / 1.6

### Spacing
- 4px, 8px, 12px, 16px, 20px, 24px, 32px, 40px, 48px

### Radius
- Small: 8px
- Medium: 12px
- Large: 18px
- XL: 24px

## Components
- Header + search
- Sidebar + nav groups
- Metric cards
- Data tables
- Forms and filters
- Status badges
- Activity timeline
- Buttons (primary, secondary, ghost)
- Dark mode toggle

## Recommended implementation stack
- Frontend: HTML + CSS + JS prototype
- Future production conversion: React + Vite + Tailwind or SCSS
- Charts: Recharts or Chart.js
- Tables: TanStack Table for virtualized data

## Accessibility notes
- Target contrast ratios: WCAG AA minimum
- Keyboard focus rings
- Strict semantic headings and labels
- ARIA for navigation and data table operations

## Files
- `tokens.css` contains the semantic variables
- `storybook.css` contains the component system styling
- `pages/*.html` contains the multi-page designer prototypes

## Next engineering step
Convert tokens and component patterns into a React component library or Tailwind config for production use.
