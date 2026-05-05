/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#4285F4',
        secondary: '#34A853',
        danger: '#EA4335',
        warning: '#FBBC05',
        info: '#2196F3',
      },
    },
  },
  plugins: [],
}