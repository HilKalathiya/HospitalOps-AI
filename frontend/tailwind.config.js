/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        app: 'var(--app-bg)',
        surface: {
          DEFAULT: 'var(--surface)',
          muted: 'var(--surface-muted)',
          hover: 'var(--surface-hover)',
          selected: 'var(--surface-selected)',
          inset: 'var(--surface-inset)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          disabled: 'var(--text-disabled)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          DEFAULT: 'var(--border-default)',
          strong: 'var(--border-strong)',
        },
        brand: {
          DEFAULT: 'var(--brand-primary)',
          hover: 'var(--brand-hover)',
          pressed: 'var(--brand-pressed)',
          soft: 'var(--brand-soft)',
          text: 'var(--brand-text)',
        },
        status: {
          success: 'var(--status-success)',
          'success-bg': 'var(--status-success-bg)',
          warning: 'var(--status-warning)',
          'warning-bg': 'var(--status-warning-bg)',
          danger: 'var(--status-danger)',
          'danger-bg': 'var(--status-danger-bg)',
          info: 'var(--status-info)',
          'info-bg': 'var(--status-info-bg)',
        },
        chart: {
          actual: 'var(--chart-actual)',
          forecast: 'var(--chart-forecast)',
          baseline: 'var(--chart-baseline)',
          comparison: 'var(--chart-comparison)',
          grid: 'var(--chart-grid)',
          axis: 'var(--chart-axis)',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'monospace'],
      },
      boxShadow: {
        popover: 'var(--shadow-popover)',
        dialog: 'var(--shadow-dialog)',
      },
      fontSize: {
        '2xs': ['0.75rem', { lineHeight: '1rem' }],        // 12px
        xs: ['0.8125rem', { lineHeight: '1.2rem' }],       // 13px (elevated from 12px)
        sm: ['0.9375rem', { lineHeight: '1.4rem' }],       // 15px (elevated from 14px)
        base: ['1.0625rem', { lineHeight: '1.6rem' }],     // 17px (elevated from 16px)
        lg: ['1.1875rem', { lineHeight: '1.75rem' }],      // 19px (elevated from 18px)
        xl: ['1.3125rem', { lineHeight: '1.875rem' }],     // 21px (elevated from 20px)
        '2xl': ['1.625rem', { lineHeight: '2.125rem' }],   // 26px (elevated from 24px)
        '3xl': ['2rem', { lineHeight: '2.5rem' }],         // 32px (elevated from 30px)
      }
    },
  },
  plugins: [],
}
