/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0D1117',
          sidebar: '#111827',
          card: '#18212F',
          elevated: '#202B3A',
          border: '#2B3645',
        },
        brand: {
          purple: '#8B5CF6',
          'purple-light': '#A78BFA',
          'purple-dark': '#7C3AED',
        },
        text: {
          main: '#F8FAFC',
          muted: '#94A3B8',
        },
        status: {
          genuine: '#22C55E',
          warning: '#F59E0B',
          invalid: '#EF4444',
          neutral: '#94A3B8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

