import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        swft: {
          primary: "#2563eb",
          accent: "#1e293b"
        }
      }
    }
  },
  plugins: []
};

export default config;
