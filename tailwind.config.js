/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./**/*.html'],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui'), require('@tailwindcss/forms')],
  darkMode: 'selector', // or 'media' or 'class'
};