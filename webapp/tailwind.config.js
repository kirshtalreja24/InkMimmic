/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // We can map our custom colors to tailwind config if we want,
        // but since we already use vanilla classes and css variables,
        // we keep the defaults.
      }
    },
  },
  plugins: [],
}
