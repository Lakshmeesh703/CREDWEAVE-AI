/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#172033',
        teal: '#0f766e',
        mist: '#f4f7f6',
        navy: {
          800: '#1d2b45',
          900: '#111827',
          950: '#0b1220',
        },
      },
    },
  },
  plugins: [],
}
