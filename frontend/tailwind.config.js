/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#ff906d",
        primary_container: "#f9873e",
        tertiary_container: "#f9873e",
        on_primary_container: "#460f00",
        surface: "#0e0e0e",
        "surface-container-low": "#131313",
        "surface-container-high": "#1a1a1a",
        "surface-container-highest": "#262626",
        "surface-variant": "#333333",
        on_surface: "#ffffff",
        on_surface_variant: "#adaaaa",
        outline_variant: "#484847",
        error: "#ffb4ab",
        error_dim: "#d7383b",
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
