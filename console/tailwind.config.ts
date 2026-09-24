import type { Config } from "tailwindcss";
export default {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { background: "hsl(var(--background))", foreground: "hsl(var(--foreground))", surface: "hsl(var(--surface))", border: "hsl(var(--border))",
      muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" }, primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
      accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" }, tile: "hsl(var(--tile))" },
    borderRadius: { lg: "12px", md: "8px", sm: "6px" },
    fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"], mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"] },
  } },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
