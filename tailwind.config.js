/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/**/*.js"],
  theme: {
    extend: {
      colors: {
        // Configure your color palette here
        bgPurple: "#221E28",
        txtPurple: "#8C7CA0",
        purpleHover:"#50465e"
      },
    },
  },
  plugins: [],
};