/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        /* Brand color ramps */
        green: {
          950: "hsl(var(--green-950))",
          900: "hsl(var(--green-900))",
          800: "hsl(var(--green-800))",
          700: "hsl(var(--green-700))",
          600: "hsl(var(--green-600))",
          500: "hsl(var(--green-500))",
          400: "hsl(var(--green-400))",
          300: "hsl(var(--green-300))",
        },
        teal: {
          900: "hsl(var(--teal-900))",
          800: "hsl(var(--teal-800))",
          700: "hsl(var(--teal-700))",
          600: "hsl(var(--teal-600))",
          500: "hsl(var(--teal-500))",
          400: "hsl(var(--teal-400))",
          300: "hsl(var(--teal-300))",
          100: "hsl(var(--teal-100))",
          50: "hsl(var(--teal-50))",
        },
        /* Neutral ramp */
        n: {
          0: "hsl(var(--n-0))",
          50: "hsl(var(--n-50))",
          100: "hsl(var(--n-100))",
          200: "hsl(var(--n-200))",
          300: "hsl(var(--n-300))",
          400: "hsl(var(--n-400))",
          500: "hsl(var(--n-500))",
          600: "hsl(var(--n-600))",
          700: "hsl(var(--n-700))",
          800: "hsl(var(--n-800))",
          900: "hsl(var(--n-900))",
        },
        /* Chrome (dark surfaces) */
        chrome: {
          DEFAULT: "hsl(var(--chrome))",
          elevated: "hsl(var(--chrome-elevated))",
          foreground: "hsl(var(--chrome-foreground))",
          muted: "hsl(var(--chrome-muted-foreground))",
          border: "hsl(var(--chrome-border))",
          hover: "hsl(var(--chrome-hover))",
        },
        /* Semantic colors */
        success: {
          DEFAULT: "hsl(var(--success))",
          bg: "hsl(var(--success-bg))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          bg: "hsl(var(--warning-bg))",
        },
        danger: {
          DEFAULT: "hsl(var(--destructive))",
          bg: "hsl(var(--destructive-bg))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          bg: "hsl(var(--info-bg))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        xs: "var(--shadow-xs)",
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
      },
      fontFamily: {
        sans: ['"Inter var"', 'Inter', '"Segoe UI"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Cascadia Mono"', 'Consolas', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.02em" }],
        xs: ["0.75rem", { lineHeight: "1.125rem" }],
        sm: ["0.8125rem", { lineHeight: "1.25rem" }],
        base: ["0.875rem", { lineHeight: "1.375rem" }],
        lg: ["1rem", { lineHeight: "1.5rem" }],
        xl: ["1.125rem", { lineHeight: "1.625rem", letterSpacing: "-0.01em" }],
        "2xl": ["1.375rem", { lineHeight: "1.875rem", letterSpacing: "-0.015em" }],
        "3xl": ["1.75rem", { lineHeight: "2.125rem", letterSpacing: "-0.02em" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem", letterSpacing: "-0.025em" }],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-18px)" },
        },
        "float-reverse": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(14px)" },
        },
        "glow-pulse": {
          "0%, 100%": {
            boxShadow: "0 0 20px 4px rgba(99, 102, 241, 0.35)",
          },
          "50%": {
            boxShadow: "0 0 35px 10px rgba(99, 102, 241, 0.55)",
          },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in-scale": {
          from: { opacity: "0", transform: "scale(0.95)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(8px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "shimmer": {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "float": "float 7s ease-in-out infinite",
        "float-slow": "float 10s ease-in-out infinite 2s",
        "float-reverse": "float-reverse 8s ease-in-out infinite 1s",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
        "fade-up": "fade-up 0.5s ease-out both",
        "fade-up-delay-1": "fade-up 0.5s ease-out 0.1s both",
        "fade-up-delay-2": "fade-up 0.5s ease-out 0.2s both",
        "fade-up-delay-3": "fade-up 0.5s ease-out 0.3s both",
        "fade-up-delay-4": "fade-up 0.5s ease-out 0.4s both",
        "fade-in-scale": "fade-in-scale 0.4s ease-out both",
        "slide-in-right": "slide-in-right 180ms cubic-bezier(0.16,1,0.3,1) both",
        "shimmer": "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};