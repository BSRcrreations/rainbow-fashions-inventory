/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      colors: {
        ink: "#1f2933",
        line: "#d9e2ec",
        surface: "#ffffff",
        canvas: "#f4f7fb",
        primary: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          200: "#99f6e4",
          300: "#5eead4",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0f766e",
          800: "#115e59",
          900: "#134e4a"
        }
      },
      boxShadow: {
        soft: "0 4px 20px -4px rgba(15, 41, 51, 0.08)",
        card: "0 1px 3px rgba(15, 41, 51, 0.04), 0 8px 24px rgba(15, 41, 51, 0.06)",
        elevated: "0 12px 40px -8px rgba(15, 41, 51, 0.12)"
      }
    }
  },
  plugins: []
};
