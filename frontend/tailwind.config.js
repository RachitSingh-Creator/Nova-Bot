/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          50: "#f6f8fc",
          100: "#edf2f7",
          900: "#0f172a"
        }
      }
    }
  },
  plugins: []
};
