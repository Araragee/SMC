/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      screens: {
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },
      colors: {
        // Tokens that need opacity modifier support use rgb(var(--X-rgb) / <alpha-value>).
        // All CSS vars are defined in style.css and switch via :root / :root:not(.dark).

        // Primary — used with /10 /20 /30 /40 /50 opacity modifiers
        "primary":                    "rgb(var(--primary-rgb) / <alpha-value>)",
        "on-primary":                 "var(--on-primary)",
        "primary-container":          "var(--primary-container)",
        "on-primary-container":       "var(--on-primary-container)",
        "primary-dim":                "var(--primary-dim)",
        "primary-fixed":              "var(--primary-fixed)",
        "primary-fixed-dim":          "var(--primary-fixed-dim)",
        "on-primary-fixed":           "var(--on-primary-fixed)",
        "on-primary-fixed-variant":   "var(--on-primary-fixed-variant)",
        "inverse-primary":            "var(--inverse-primary)",

        "secondary":                  "var(--secondary)",
        "on-secondary":               "var(--on-secondary)",
        "secondary-container":        "var(--secondary-container)",
        "on-secondary-container":     "var(--on-secondary-container)",
        "secondary-dim":              "var(--secondary-dim)",
        "secondary-fixed":            "var(--secondary-fixed)",
        "secondary-fixed-dim":        "var(--secondary-fixed-dim)",
        "on-secondary-fixed":         "var(--on-secondary-fixed)",
        "on-secondary-fixed-variant": "var(--on-secondary-fixed-variant)",

        "tertiary":                   "var(--tertiary)",
        "on-tertiary":                "var(--on-tertiary)",
        "tertiary-container":         "var(--tertiary-container)",
        "on-tertiary-container":      "var(--on-tertiary-container)",
        "tertiary-dim":               "var(--tertiary-dim)",
        "tertiary-fixed":             "var(--tertiary-fixed)",
        "tertiary-fixed-dim":         "var(--tertiary-fixed-dim)",
        "on-tertiary-fixed":          "var(--on-tertiary-fixed)",
        "on-tertiary-fixed-variant":  "var(--on-tertiary-fixed-variant)",

        "error":                      "var(--error)",
        "on-error":                   "var(--on-error)",
        "error-container":            "var(--error-container)",
        "on-error-container":         "var(--on-error-container)",
        "error-dim":                  "var(--error-dim)",

        "surface":                    "var(--surface)",
        // on-surface used with ring-on-surface/20
        "on-surface":                 "rgb(var(--on-surface-rgb) / <alpha-value>)",
        "surface-dim":                "var(--surface-dim)",
        "surface-bright":             "var(--surface-bright)",
        "surface-container-lowest":   "var(--surface-container-lowest)",
        // surface-container-low used with /40 /80
        "surface-container-low":      "rgb(var(--surface-container-low-rgb) / <alpha-value>)",
        "surface-container":          "var(--surface-container)",
        "surface-container-high":     "var(--surface-container-high)",
        // surface-container-highest used with /30 /50 /80
        "surface-container-highest":  "rgb(var(--surface-container-highest-rgb) / <alpha-value>)",
        "surface-variant":            "var(--surface-variant)",
        // on-surface-variant used with /40 /50 /60
        "on-surface-variant":         "rgb(var(--on-surface-variant-rgb) / <alpha-value>)",
        "inverse-surface":            "var(--inverse-surface)",
        "inverse-on-surface":         "var(--inverse-on-surface)",
        "surface-tint":               "var(--surface-tint)",

        "outline":                    "var(--outline)",
        // outline-variant used with /20 /30 /40
        "outline-variant":            "rgb(var(--outline-variant-rgb) / <alpha-value>)",

        "background":                 "var(--background)",
        "on-background":              "var(--on-background)",

        // Legacy underscore aliases
        "primary_container":          "var(--primary-container)",
        "tertiary_container":         "var(--tertiary-container)",
        "on_primary_container":       "var(--on-primary-container)",
        "on_surface":                 "rgb(var(--on-surface-rgb) / <alpha-value>)",
        "on_surface_variant":         "rgb(var(--on-surface-variant-rgb) / <alpha-value>)",
        "outline_variant":            "rgb(var(--outline-variant-rgb) / <alpha-value>)",
        "error_dim":                  "var(--error-dim)",
      },
      fontFamily: {
        "headline": ["Plus Jakarta Sans", "sans-serif"],
        "body": ["Plus Jakarta Sans", "sans-serif"],
        "label": ["Plus Jakarta Sans", "sans-serif"],
        "sans": ["Plus Jakarta Sans", "sans-serif"],
        "plus-jakarta-sans": ["Plus Jakarta Sans", "sans-serif"],
      },
      borderRadius: {"DEFAULT": "1rem", "lg": "2rem", "xl": "3rem"},
    },
  },
  plugins: [],
}
