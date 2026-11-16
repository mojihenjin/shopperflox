/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sf: {
          dark: '#3F2021',      // Шоколадно-бордовый (Espresso/Burgundy)
          cream: '#F2E9DB',     // Сливочный лен (Warm Cream)
          denim: '#7594B3',     // Серо-голубой деним (Slate Denim)
          black: '#000000',     // Чистый черный
          muted: '#5F5F5F',     // Приглушенный серый
          coral: '#FF8562',     // Кораллово-терракотовый микроакцент
          border: '#C7D2E9',    // Светло-голубой бордер
        }
      },
      fontFamily: {
        serif: ['"Times New Roman"', 'Georgia', 'serif'],
        sans: ['"Golos Text"', '-apple-system', 'BlinkMacSystemFont', 'Arial', 'sans-serif'],
      },
      borderRadius: {
        none: '0px',
        DEFAULT: '0px',
      },
      maxWidth: {
        container: '1200px',
      },
      aspectRatio: {
        portrait: '2 / 3',
        banner: '1160 / 348',
      }
    }
  },
  plugins: [],
};
