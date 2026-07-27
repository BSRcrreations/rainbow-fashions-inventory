export const themeTokens = {
  colors: {
    primary: "rgb(var(--color-primary-700))",
    secondary: "rgb(var(--color-secondary))",
    success: "rgb(var(--color-success))",
    warning: "rgb(var(--color-warning))",
    error: "rgb(var(--color-error))",
    background: "rgb(var(--color-background))",
    surface: "rgb(var(--color-surface))",
    foreground: "rgb(var(--color-foreground))",
    muted: "rgb(var(--color-muted))",
    border: "rgb(var(--color-border))",
  },
  radius: { sm: 6, md: 8, lg: 12, xl: 16 },
  spacing: { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32 },
  iconSize: { sm: 16, md: 20, lg: 24 },
  controlHeight: { sm: 40, md: 44, lg: 48 },
  motion: { fast: 160, base: 220 },
} as const;

export type ThemeTokens = typeof themeTokens;
