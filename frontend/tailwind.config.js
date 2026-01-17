/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        medical: {
          primary: '#0072C6',
          secondary: '#E6F3FF',
          success: '#28a745',
          warning: '#ffc107',
          danger: '#FF0000',
        }
      }
    },
  },
  plugins: [],
  darkMode: 'class',
}
