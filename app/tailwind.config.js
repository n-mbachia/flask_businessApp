const path = require('path');
const defaultTheme = require('tailwindcss/defaultTheme');
const colors = require('tailwindcss/colors');

const tokenVar = (name) => `var(${name})`;

const colorTokens = {
  primary: {
    DEFAULT: tokenVar('--color-primary'),
    dark: tokenVar('--color-primary-dark'),
    light: tokenVar('--color-primary-light'),
    lighter: tokenVar('--color-primary-lighter'),
  },
  secondary: {
    DEFAULT: tokenVar('--color-secondary'),
    dark: tokenVar('--color-secondary-dark'),
    light: tokenVar('--color-secondary-light'),
  },
  accent: {
    DEFAULT: tokenVar('--color-accent'),
    dark: tokenVar('--color-accent-dark'),
    light: tokenVar('--color-accent-light'),
  },
  background: tokenVar('--color-background'),
  surface: tokenVar('--color-surface'),
  'surface-alt': tokenVar('--color-surface-alt'),
  text: tokenVar('--color-text'),
  'text-muted': tokenVar('--color-text-muted'),
  'text-light': tokenVar('--color-text-light'),
  success: {
    DEFAULT: tokenVar('--color-success'),
    light: tokenVar('--color-success-light'),
  },
  warning: {
    DEFAULT: tokenVar('--color-warning'),
    light: tokenVar('--color-warning-light'),
  },
  danger: {
    DEFAULT: tokenVar('--color-danger'),
    light: tokenVar('--color-danger-light'),
  },
  info: {
    DEFAULT: tokenVar('--color-info'),
    light: tokenVar('--color-info-light'),
  },
  gray: {
    50: tokenVar('--color-background'),
    100: tokenVar('--color-gray-100'),
    200: tokenVar('--color-gray-200'),
    300: tokenVar('--color-gray-300'),
    400: tokenVar('--color-gray-400'),
    500: tokenVar('--color-gray-500'),
    600: tokenVar('--color-gray-600'),
    700: tokenVar('--color-gray-700'),
    800: tokenVar('--color-gray-800'),
    900: tokenVar('--color-gray-900'),
  },
};

const defaultColorPalette = {
  inherit: 'inherit',
  current: 'currentColor',
  transparent: 'transparent',
  black: colors.black,
  white: colors.white,
  slate: colors.slate,
  gray: colors.gray,
  zinc: colors.zinc,
  neutral: colors.neutral,
  stone: colors.stone,
  red: colors.red,
  orange: colors.orange,
  amber: colors.amber,
  yellow: colors.yellow,
  lime: colors.lime,
  green: colors.green,
  emerald: colors.emerald,
  teal: colors.teal,
  cyan: colors.cyan,
  sky: colors.sky,
  blue: colors.blue,
  indigo: colors.indigo,
  violet: colors.violet,
  purple: colors.purple,
  fuchsia: colors.fuchsia,
  pink: colors.pink,
  rose: colors.rose,
};

const spacingScale = {
  xxs: '0.25rem',
  xs: '0.5rem',
  sm: '0.75rem',
  md: '1rem',
  lg: '1.5rem',
  xl: '2rem',
  '2xl': '3rem',
  '3xl': '4rem',
};

const fontSizeScale = {
  xs: tokenVar('--font-size-xs'),
  sm: tokenVar('--font-size-sm'),
  base: tokenVar('--font-size-base'),
  lg: tokenVar('--font-size-lg'),
  xl: tokenVar('--font-size-xl'),
  '2xl': tokenVar('--font-size-2xl'),
  '3xl': tokenVar('--font-size-3xl'),
  '4xl': tokenVar('--font-size-4xl'),
};

const lineHeightScale = {
  none: tokenVar('--line-height-none'),
  tight: tokenVar('--line-height-tight'),
  snug: tokenVar('--line-height-snug'),
  normal: tokenVar('--line-height-normal'),
  relaxed: tokenVar('--line-height-relaxed'),
  loose: tokenVar('--line-height-loose'),
};

const letterSpacingScale = {
  tighter: tokenVar('--letter-spacing-tighter'),
  tight: tokenVar('--letter-spacing-tight'),
  normal: tokenVar('--letter-spacing-normal'),
  wide: tokenVar('--letter-spacing-wide'),
  wider: tokenVar('--letter-spacing-wider'),
  widest: tokenVar('--letter-spacing-widest'),
};

const borderRadiusScale = {
  sm: tokenVar('--border-radius-sm'),
  md: tokenVar('--border-radius-md'),
  lg: tokenVar('--border-radius-lg'),
  xl: tokenVar('--border-radius-xl'),
  '2xl': tokenVar('--border-radius-2xl'),
  full: tokenVar('--border-radius-full'),
};

const borderWidthScale = {
  DEFAULT: tokenVar('--border-width'),
  2: tokenVar('--border-width-2'),
  4: tokenVar('--border-width-4'),
};

const boxShadowScale = {
  sm: tokenVar('--shadow-sm'),
  DEFAULT: tokenVar('--shadow'),
  md: tokenVar('--shadow-md'),
  lg: tokenVar('--shadow-lg'),
  xl: tokenVar('--shadow-xl'),
  '2xl': tokenVar('--shadow-2xl'),
  inner: tokenVar('--shadow-inner'),
  outline: tokenVar('--shadow-outline'),
  none: tokenVar('--shadow-none'),
};

const transitionDurationScale = {
  fast: tokenVar('--transition-fast'),
  normal: tokenVar('--transition-normal'),
  slow: tokenVar('--transition-slow'),
};

const containerMaxWidth = {
  'container-sm': tokenVar('--container-sm'),
  'container-md': tokenVar('--container-md'),
  'container-lg': tokenVar('--container-lg'),
  'container-xl': tokenVar('--container-xl'),
  'container-2xl': tokenVar('--container-2xl'),
};

const defaultMaxWidthScale = {
  '0': '0rem',
  none: 'none',
  xs: '20rem',
  sm: '24rem',
  md: '28rem',
  lg: '32rem',
  xl: '36rem',
  '2xl': '42rem',
  '3xl': '48rem',
  '4xl': '56rem',
  '5xl': '64rem',
  '6xl': '72rem',
  '7xl': '80rem',
  full: '100%',
  min: 'min-content',
  max: 'max-content',
  fit: 'fit-content',
  prose: '65ch',
};

module.exports = {
  content: [
    path.join(__dirname, 'templates/**/*.html'),
    path.join(__dirname, 'static/js/**/*.js'),
    path.join(__dirname, 'static/js/components/**/*.js'),
  ],
  theme: {
    extend: {
      colors: {
        ...defaultColorPalette,
        ...colorTokens,
      },
      fontFamily: {
        sans: ['var(--font-primary)', ...defaultTheme.fontFamily.sans],
        mono: ['var(--font-mono)', ...defaultTheme.fontFamily.mono],
      },
      fontSize: {
        ...defaultTheme.fontSize,
        ...fontSizeScale,
      },
      spacing: {
        ...defaultTheme.spacing,
        ...spacingScale,
      },
      lineHeight: {
        ...defaultTheme.lineHeight,
        ...lineHeightScale,
      },
      letterSpacing: {
        ...defaultTheme.letterSpacing,
        ...letterSpacingScale,
      },
      borderRadius: {
        ...defaultTheme.borderRadius,
        ...borderRadiusScale,
      },
      borderWidth: {
        ...defaultTheme.borderWidth,
        ...borderWidthScale,
      },
      boxShadow: {
        ...defaultTheme.boxShadow,
        ...boxShadowScale,
      },
      transitionDuration: {
        ...defaultTheme.transitionDuration,
        ...transitionDurationScale,
      },
      transitionTimingFunction: {
        DEFAULT: tokenVar('--transition-timing'),
      },
      screens: {
        ...defaultTheme.screens,
        xs: '0px',
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
      },
      maxWidth: {
        ...defaultMaxWidthScale,
        ...containerMaxWidth,
      },
    },
  },
  plugins: [],
};
