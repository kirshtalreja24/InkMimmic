/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./App.js', './src/**/*.{js,jsx}'],
  presets: [require('nativewind/preset')],
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
        display: ['Fraunces_600SemiBold'],
        displayItalic: ['Fraunces_500Medium_Italic'],
        body: ['Manrope_400Regular'],
        bodyBold: ['Manrope_700Bold'],
        bodySemibold: ['Manrope_600SemiBold'],
        script: ['Caveat_600SemiBold'],
      },
    },
  },
  plugins: [],
};
