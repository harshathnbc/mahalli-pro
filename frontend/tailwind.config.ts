import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#0F766E", dark: "#115E59" }, // KSA-teal
      },
    },
  },
  plugins: [],
} satisfies Config;
