import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // GestureMed Design System
        gm: {
          bg: "#060608",
          surface: "#0d0d12",
          panel: "#11111a",
          border: "#1a1a28",
          "border-light": "#252535",
          accent: "#3B82F6",
          "accent-dim": "#1d4ed8",
          teal: "#14B8A6",
          purple: "#8B5CF6",
          amber: "#F59E0B",
          red: "#EF4444",
          green: "#10B981",
          text: "#F1F5F9",
          "text-muted": "#64748B",
          "text-dim": "#334155",
        },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "DM Mono", "ui-monospace", "monospace"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
        glow: "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        glow: {
          "0%": { boxShadow: "0 0 5px rgba(59, 130, 246, 0.3)" },
          "100%": { boxShadow: "0 0 20px rgba(59, 130, 246, 0.7)" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};

export default config;
