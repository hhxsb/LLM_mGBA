/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pokemon: {
          blue: '#3B82F6',
          yellow: '#FCD34D',
          red: '#EF4444',
          green: '#10B981',
          sky: '#0EA5E9',
        },
        chat: {
          user: '#E5E7EB',
          ai: '#DBEAFE',
          gif: '#FEF3C7',
          action: '#DCFCE7',
          system: '#F3E8FF',
        }
      },
      animation: {
        'bounce-slow': 'bounce 2s infinite',
        'pulse-slow': 'pulse 3s infinite',
      }
    },
  },
  plugins: [],
}