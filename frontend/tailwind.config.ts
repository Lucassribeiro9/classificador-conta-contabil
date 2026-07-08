import type { Config } from "tailwindcss";

import { visualTokens } from "./src/styles/tokens";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: visualTokens.colors.brand,
          dark: visualTokens.colors.brandDark,
        },
        surface: visualTokens.colors.surface,
        neutral: visualTokens.colors.neutral,
      },
      borderRadius: {
        compact: visualTokens.radius.compact,
        control: visualTokens.radius.control,
      },
      boxShadow: {
        compact: visualTokens.shadow.compact,
      },
    },
  },
  plugins: [],
} satisfies Config;
