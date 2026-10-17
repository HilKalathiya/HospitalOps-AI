/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: 'var(--bg)',
          2: 'var(--bg-2)',
        },
        panel: {
          DEFAULT: 'var(--panel)',
          raised: 'var(--panel-raised)',
          hover: 'var(--panel-hover)',
        },
        ink: {
          DEFAULT: 'var(--ink)',
          2: 'var(--ink-2)',
        },
        muted: 'var(--muted)',
        subtle: 'var(--subtle)',
        line: {
          DEFAULT: 'var(--line)',
          strong: 'var(--line-strong)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          soft: 'var(--accent-soft)',
          2: 'var(--accent-2)',
        },
        good: 'var(--good)',
        warn: 'var(--warn)',
        bad: 'var(--bad)',

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
        '2xs': ['0.6875rem', { lineHeight: '0.9rem' }],    // 11px
        xs: ['0.75rem', { lineHeight: '1.05rem' }],        // 12px
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],      // 13px
        base: ['0.875rem', { lineHeight: '1.4rem' }],      // 14px
        lg: ['1rem', { lineHeight: '1.5rem' }],            // 16px
        xl: ['1.1875rem', { lineHeight: '1.75rem' }],      // 19px
        '2xl': ['1.4375rem', { lineHeight: '1.9rem' }],    // 23px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],    // 30px
      }
    },
  },
  plugins: [],
}
