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
        "primary-container":          "rgb(var(--primary-container-rgb) / <alpha-value>)",
        "on-primary-container":       "rgb(var(--on-primary-container-rgb) / <alpha-value>)",
        "primary-dim":                "var(--primary-dim)",
        "primary-fixed":              "var(--primary-fixed)",
        "primary-fixed-dim":          "var(--primary-fixed-dim)",
        "on-primary-fixed":           "var(--on-primary-fixed)",
        "on-primary-fixed-variant":   "var(--on-primary-fixed-variant)",
        "inverse-primary":            "var(--inverse-primary)",

        "secondary":                  "rgb(var(--secondary-rgb) / <alpha-value>)",
        "on-secondary":               "var(--on-secondary)",
        "secondary-container":        "rgb(var(--secondary-container-rgb) / <alpha-value>)",
        "on-secondary-container":     "rgb(var(--on-secondary-container-rgb) / <alpha-value>)",
        "secondary-dim":              "var(--secondary-dim)",
        "secondary-fixed":            "var(--secondary-fixed)",
        "secondary-fixed-dim":        "var(--secondary-fixed-dim)",
        "on-secondary-fixed":         "var(--on-secondary-fixed)",
        "on-secondary-fixed-variant": "var(--on-secondary-fixed-variant)",

        "tertiary":                   "rgb(var(--tertiary-rgb) / <alpha-value>)",
        "on-tertiary":                "var(--on-tertiary)",
        "tertiary-container":         "rgb(var(--tertiary-container-rgb) / <alpha-value>)",
        "on-tertiary-container":      "rgb(var(--on-tertiary-container-rgb) / <alpha-value>)",
        "tertiary-dim":               "var(--tertiary-dim)",
        "tertiary-fixed":             "var(--tertiary-fixed)",
        "tertiary-fixed-dim":         "var(--tertiary-fixed-dim)",
        "on-tertiary-fixed":          "var(--on-tertiary-fixed)",
        "on-tertiary-fixed-variant":  "var(--on-tertiary-fixed-variant)",

        // Status colors — pastel containers with a deeper on-* foreground.
        "success":                    "rgb(var(--success-rgb) / <alpha-value>)",
        "on-success":                 "var(--on-success)",
        "success-container":          "rgb(var(--success-container-rgb) / <alpha-value>)",
        "on-success-container":       "rgb(var(--on-success-container-rgb) / <alpha-value>)",

        "warning":                    "rgb(var(--warning-rgb) / <alpha-value>)",
        "on-warning":                 "var(--on-warning)",
        "warning-container":          "rgb(var(--warning-container-rgb) / <alpha-value>)",
        "on-warning-container":       "rgb(var(--on-warning-container-rgb) / <alpha-value>)",

        "info":                       "rgb(var(--info-rgb) / <alpha-value>)",
        "on-info":                    "var(--on-info)",
        "info-container":             "rgb(var(--info-container-rgb) / <alpha-value>)",
        "on-info-container":          "rgb(var(--on-info-container-rgb) / <alpha-value>)",

        "error":                      "rgb(var(--error-rgb) / <alpha-value>)",
        "on-error":                   "var(--on-error)",
        "error-container":            "rgb(var(--error-container-rgb) / <alpha-value>)",
        "on-error-container":         "rgb(var(--on-error-container-rgb) / <alpha-value>)",
        "error-dim":                  "var(--error-dim)",

        "surface":                    "var(--surface)",
        // on-surface used with ring-on-surface/20
        "on-surface":                 "rgb(var(--on-surface-rgb) / <alpha-value>)",
        "surface-dim":                "var(--surface-dim)",
        "surface-bright":             "var(--surface-bright)",
        "surface-container-lowest":   "rgb(var(--surface-container-lowest-rgb) / <alpha-value>)",
        // surface-container-low used with /40 /80
        "surface-container-low":      "rgb(var(--surface-container-low-rgb) / <alpha-value>)",
        "surface-container":          "rgb(var(--surface-container-rgb) / <alpha-value>)",
        "surface-container-high":     "rgb(var(--surface-container-high-rgb) / <alpha-value>)",
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
        "primary_container":          "rgb(var(--primary-container-rgb) / <alpha-value>)",
        "tertiary_container":         "rgb(var(--tertiary-container-rgb) / <alpha-value>)",
        "on_primary_container":       "rgb(var(--on-primary-container-rgb) / <alpha-value>)",
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
      // Radii were 1rem/2rem/3rem — heavy enough that small controls read as
      // pills and cards as lozenges. Scaled to a conventional ramp where the
      // radius stays proportional to the element.
      borderRadius: {"DEFAULT": "0.75rem", "lg": "1rem", "xl": "1.5rem"},
      boxShadow: {
        "e1": "var(--shadow-1)",
        "e2": "var(--shadow-2)",
        "e3": "var(--shadow-3)",
      },
    },
  },
  plugins: [],
}
