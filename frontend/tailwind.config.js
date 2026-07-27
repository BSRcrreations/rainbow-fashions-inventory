/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      colors: {
        primary: {
          50: token("color-primary-50"), 100: token("color-primary-100"),
          200: token("color-primary-200"), 300: token("color-primary-300"),
          400: token("color-primary-400"), 500: token("color-primary-500"),
          600: token("color-primary-600"), 700: token("color-primary-700"),
          800: token("color-primary-800"), 900: token("color-primary-900")
        },
        secondary: token("color-secondary"),
        success: token("color-success"),
        warning: token("color-warning"),
        error: token("color-error"),
        foreground: token("color-foreground"),
        muted: token("color-muted"),
        background: token("color-background"),
        surface: token("color-surface"),
        "surface-subtle": token("color-surface-subtle"),
        border: token("color-border"),
        line: token("color-border"),
        ink: token("color-foreground"),
        slate: {
          50: token("color-neutral-50"), 100: token("color-neutral-100"),
          200: token("color-neutral-200"), 300: token("color-neutral-300"),
          400: token("color-neutral-400"), 500: token("color-neutral-500"),
          600: token("color-neutral-600"), 700: token("color-neutral-700"),
          800: token("color-neutral-800"), 900: token("color-neutral-900"),
          950: token("color-neutral-950")
        },
        teal: {
          50: token("color-primary-50"), 100: token("color-primary-100"),
          200: token("color-primary-200"), 300: token("color-primary-300"),
          400: token("color-primary-400"), 500: token("color-primary-500"),
          600: token("color-primary-600"), 700: token("color-primary-700"),
          800: token("color-primary-800"), 900: token("color-primary-900")
        }
      },
      borderRadius: {
        sm: "var(--radius-sm)", md: "var(--radius-md)",
        lg: "var(--radius-lg)", xl: "var(--radius-xl)"
      },
      boxShadow: {
        sm: "var(--shadow-sm)", md: "var(--shadow-md)",
        lg: "var(--shadow-lg)", xl: "var(--shadow-xl)"
      },
      spacing: {
        "control-sm": "var(--control-height-sm)",
        control: "var(--control-height)",
        "control-lg": "var(--control-height-lg)"
      }
    }
  },
  plugins: []
};
