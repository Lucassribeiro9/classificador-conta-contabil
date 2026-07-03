import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#007693",
          dark: "#004E61",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
