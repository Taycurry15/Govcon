/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      colors: {
        // Apple Blue
        primary: {
          50: '#e8f2ff',
          100: '#d1e5ff',
          200: '#a3cbff',
          300: '#75b1ff',
          400: '#4797ff',
          500: '#007AFF', // Apple Blue
          600: '#0062cc',
          700: '#004999',
          800: '#003166',
          900: '#001833',
        },
        // Apple Gray Scale (matching macOS/iOS)
        gray: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
        bronze: {
          50: '#fdf8f6',
          100: '#f8ebe1',
          200: '#f0d5c3',
          300: '#e5b79e',
          400: '#d89270',
          500: '#cd6f4a',
          600: '#b85a37',
          700: '#9a4a30',
          800: '#7e3f2e',
          900: '#673628',
        },
        // Apple System Colors
        systemGreen: '#34C759',
        systemYellow: '#FFCC00',
        systemOrange: '#FF9500',
        systemRed: '#FF3B30',
        systemPurple: '#AF52DE',
        systemIndigo: '#5856D6',
      },
      backgroundImage: {
        'gradient-apple': 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(249,249,249,0.9) 100%)',
      },
      boxShadow: {
        'apple-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'apple': '0 2px 8px 0 rgba(0, 0, 0, 0.08)',
        'apple-md': '0 4px 16px 0 rgba(0, 0, 0, 0.10)',
        'apple-lg': '0 8px 32px 0 rgba(0, 0, 0, 0.12)',
        'apple-xl': '0 16px 48px 0 rgba(0, 0, 0, 0.14)',
        'apple-inner': 'inset 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        'apple': '10px',
        'apple-lg': '14px',
        'apple-xl': '18px',
        'apple-2xl': '22px',
      },
      backdropBlur: {
        'apple': '20px',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
