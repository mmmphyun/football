/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pitch: {
          dark: "#1e3a1e",
          grass: "#2d5a27",
          line: "#ffffff",
          grid: "rgba(255, 255, 255, 0.15)",
        },
      },
    },
  },
  plugins: [],
}
