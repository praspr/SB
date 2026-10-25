module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        neutral: {
          50: '#F7F9FC',
          100: '#EEF2F8',
          200: '#D9E0EB',
          300: '#B9C4D6',
          400: '#98A4BB',
          500: '#7C879A',
          600: '#5E6B80',
          700: '#33415C',
          800: '#253047',
          900: '#121826',
          950: '#0C111B',
        },
        accent: {
          50: '#EEF0FD',
          100: '#DCE0FB',
          200: '#B9C1F7',
          300: '#96A2F3',
          400: '#7883E7',
          500: '#5E6AD2',
          600: '#4A55B0',
          700: '#3A4389',
          800: '#2A326C',
          900: '#1D234C',
        },
        // Violet partner for gradients / glow on focal actions.
        accent2: {
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
        },
        // Dark-first chart palette — desaturated, luminance-stepped for dark surfaces.
        chart: {
          1: '#7C8CF8',
          2: '#38BDF8',
          3: '#34D399',
          4: '#FBBF24',
          5: '#FB7185',
          6: '#C084FC',
        },
        // Semantic ramps: {fg,bg,border,solid} so /5 /10 /15 alpha math disappears.
        success: {
          DEFAULT: '#3FB68B',
          fg: '#4ADE9A',
          bg: '#0F2A22',
          border: '#1C5C45',
          solid: '#2FA87A',
        },
        warning: {
          DEFAULT: '#D9A441',
          fg: '#F5C062',
          bg: '#2B2113',
          border: '#6B5120',
          solid: '#D9A441',
        },
        danger: {
          DEFAULT: '#E06D6D',
          fg: '#F58A8A',
          bg: '#2C1618',
          border: '#6E2B2E',
          solid: '#D95C5C',
        },
        info: {
          DEFAULT: '#5DA8FF',
          fg: '#7CC0FF',
          bg: '#12243A',
          border: '#245080',
          solid: '#4A95E8',
        },
        // 4-step opaque elevation ladder (+ sunken). Depth via lightness, not borders.
        surface: {
          0: '#080C14', // app canvas — darkest
          1: '#121826', // panels, cards, sidebar
          2: '#1A2236', // hover, raised rows, active nav
          3: '#232C44', // popovers, dialogs, command palette
          sunken: '#0D1220', // inset wells, inputs, table headers
        },
        // Back-compat aliases (map onto the new ladder so legacy classes keep working).
        bg: {
          app: '#080C14',
          panel: '#121826',
          elevated: '#1A2236',
          overlay: '#232C44',
        },
        border: {
          subtle: 'rgba(255,255,255,0.06)',
          strong: 'rgba(255,255,255,0.12)',
          accent: 'rgba(94,106,210,0.55)',
        },
        text: {
          primary: '#F5F7FB',
          secondary: '#A7B0C0',
          muted: '#78839A',
          faint: '#4D5A74',
        },
      },
      fontFamily: {
        // text-40/32 font-mono — hero numbers
        // text-24 font-semibold tracking-tight — page h1
        // text-20 font-semibold — section h1 (dense)
        // text-16 font-semibold — section h2
        // text-14 font-semibold — subsection h3
        // text-13 — body
        // text-12 — secondary body
        // text-11 uppercase tracking — small caps labels / sidebar group heading
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'Geist Mono',
          'SF Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'monospace',
        ],
      },
      fontSize: {
        11: ['11px', { lineHeight: '14px', fontWeight: '600', letterSpacing: '0.08em' }],
        12: ['12px', { lineHeight: '16px', fontWeight: '500' }],
        13: ['13px', { lineHeight: '18px', fontWeight: '500' }],
        14: ['14px', { lineHeight: '20px', fontWeight: '500' }],
        16: ['16px', { lineHeight: '24px', fontWeight: '600', letterSpacing: '-0.006em' }],
        20: ['20px', { lineHeight: '26px', fontWeight: '600', letterSpacing: '-0.012em' }],
        24: ['24px', { lineHeight: '30px', fontWeight: '650', letterSpacing: '-0.018em' }],
        32: ['32px', { lineHeight: '34px', fontWeight: '680', letterSpacing: '-0.025em' }],
        40: ['40px', { lineHeight: '42px', fontWeight: '700', letterSpacing: '-0.03em' }],
      },
      borderRadius: {
        sm: '8px',
        md: '10px',
        lg: '14px',
        xl: '18px',
        '2xl': '22px',
      },
      boxShadow: {
        sm: '0 8px 24px rgba(0,0,0,0.18)',
        md: '0 16px 40px rgba(0,0,0,0.24)',
        raised: '0 1px 2px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.04)',
        card: '0 2px 8px rgba(0,0,0,0.32), 0 0 0 1px rgba(255,255,255,0.05)',
        pop: '0 12px 32px -8px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.07)',
        glow: '0 0 0 1px rgba(94,106,210,0.5), 0 4px 16px -2px rgba(94,106,210,0.35)',
        rail: 'inset 2px 0 0 0 #7883E7',
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        countup: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      transitionDuration: {
        fast: '100ms',
        base: '150ms',
        view: '200ms',
      },
      animation: {
        shimmer: 'shimmer 1.6s infinite',
        countup: 'countup 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
}
