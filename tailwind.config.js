/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101722",
        panel: "#182231",
        line: "#29374a",
        mint: "#7be0c3",
        sky: "#83b5ff"
      },
      boxShadow: {
        glow: "0 22px 70px rgba(5, 10, 20, 0.28)"
      }
    }
  },
  plugins: []
};