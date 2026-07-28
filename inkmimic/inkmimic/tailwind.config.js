/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#080B22',
          900: '#0C1030',
          850: '#10143B',
          800: '#151A4A',
          700: '#1D2359',
        },
        royal: {
          800: '#152B7A',
          700: '#1E3A8A',
          600: '#2541B2',
          500: '#3457D5',
          400: '#5B79E8',
        },
        gold: {
          500: '#F2B705',
          400: '#FFC93C',
          300: '#FFD966',
          200: '#FFE9A3',
        },
        parchment: {
          DEFAULT: '#F6F1E6',
          dim: '#EBE3D2',
        },
      },
      fontFamily: {
        display: ['"Fraunces"', 'serif'],
        body: ['"Manrope"', 'sans-serif'],
        script: ['"Caveat"', 'cursive'],
      },
      boxShadow: {
        panel: '0 30px 60px -25px rgba(8, 11, 34, 0.55)',
        gold: '0 0 0 1px rgba(242, 183, 5, 0.35), 0 20px 40px -20px rgba(242, 183, 5, 0.35)',
      },
      backgroundImage: {
        'ink-grain':
          'radial-gradient(circle at 20% 20%, rgba(91,121,232,0.14), transparent 40%), radial-gradient(circle at 80% 0%, rgba(242,183,5,0.10), transparent 35%), radial-gradient(circle at 50% 100%, rgba(37,65,178,0.18), transparent 45%)',
      },
      keyframes: {
        'ink-draw': {
          to: { strokeDashoffset: 0 },
        },
        'float-slow': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'fade-up': {
          from: { opacity: 0, transform: 'translateY(14px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
        'reveal-ink': {
          from: { clipPath: 'inset(0 100% 0 0)' },
          to: { clipPath: 'inset(0 0% 0 0)' },
        },
        'pen-glide': {
          '0%': { left: '0%', opacity: 0 },
          '6%': { opacity: 1 },
          '92%': { opacity: 1 },
          '100%': { left: '100%', opacity: 0 },
        },
      },
      animation: {
        'ink-draw': 'ink-draw 2.4s ease forwards',
        'float-slow': 'float-slow 6s ease-in-out infinite',
        'fade-up': 'fade-up 0.7s cubic-bezier(0.16,1,0.3,1) forwards',
        'reveal-ink': 'reveal-ink 1.8s cubic-bezier(0.65,0.05,0.36,1) forwards',
        'pen-glide': 'pen-glide 1.8s cubic-bezier(0.65,0.05,0.36,1) forwards',
      },
    },
  },
  plugins: [],
};
