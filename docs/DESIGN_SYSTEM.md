# Design System

Rainbow Fashions uses one centralized design system. New modules must reuse these tokens and shared components instead of introducing module-specific palettes or visual primitives.

## Sources of truth

- `frontend/src/styles.css`: CSS variables, base styles, shared component classes, table behavior, and motion.
- `frontend/tailwind.config.js`: semantic Tailwind aliases backed by CSS variables.
- `frontend/src/theme/tokens.ts`: strongly typed values for charts or logic that cannot use CSS classes.
- `frontend/src/components/ui`: reusable buttons and cards.
- `frontend/src/components`: dialogs, feedback, loading, empty states, page headings, status badges, and toasts.

## Semantic tokens

- Brand: `primary-*`
- Supporting action/data: `secondary`
- Feedback: `success`, `warning`, `error`
- Content: `foreground`, `muted`
- Layout: `background`, `surface`, `surface-subtle`, `border`

The legacy `slate-*` and `teal-*` utility families are mapped to the centralized neutral and primary tokens. This keeps existing modules consistent while they migrate to semantic names.

## Shared styles

- Surfaces and cards: `ds-surface`, `ds-card`
- Forms: `field-label`, `field-input`, `focus-ring`
- Tables: `ds-table-wrap`, `ds-table`
- Dialogs: `ds-dialog-backdrop`, `ds-dialog`
- Feedback and empty states: shared React components
- Status labels: `StatusBadge`

Use the 8px spacing rhythm for component layout, 44px default controls, 12px card/control radius, and the predefined shadows. Lucide icons are the only application icon set; use 16px, 20px, or 24px token sizes.

## Rules

1. Search for an existing component before creating one.
2. Do not add raw hex colors or page-specific palettes.
3. Use semantic colors for new code. Do not bind behavior to a color name.
4. Extend tokens only when an application-wide need cannot be represented by an existing token.
5. Keep interaction states, loading, errors, dialogs, and responsive behavior in shared primitives.
