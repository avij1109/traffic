/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        hud: {
          bg: '#0a0d14',
          panel: '#101522',
          'panel-light': '#182032',
          border: '#1e293b',
          'border-bright': '#334155',
          cyan: '#06b6d4',
          emerald: '#10b981',
          amber: '#f59e0b',
          crimson: '#ef4444',
          blue: '#3b82f6',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        tactical: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'hud-glow': '0 0 15px -3px rgba(6, 182, 212, 0.25)',
        'hud-alert': '0 0 15px -3px rgba(239, 68, 68, 0.35)',
        'hud-emerald': '0 0 15px -3px rgba(16, 185, 129, 0.25)',
      },
      animation: {
        'pulse-fast': 'pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2.5s cubic-bezier(0, 0, 0.2, 1) infinite',
      }
    },
  },
  plugins: [],
}
