import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#06070f", 900: "#0a0c18", 800: "#10132a", 700: "#181c3a", 600: "#242a52" },
        brand: { violet: "#8b5cf6", blue: "#3b82f6", cyan: "#22d3ee" },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(120deg, #8b5cf6 0%, #3b82f6 55%, #22d3ee 100%)",
      },
      boxShadow: { glow: "0 0 40px -10px rgba(139,92,246,0.55)" },
    },
  },
  plugins: [],
};
export default config;
