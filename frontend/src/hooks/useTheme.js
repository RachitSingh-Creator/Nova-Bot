import { useEffect, useState } from "react";

export default function useTheme() {
  const [theme, setTheme] = useState(localStorage.getItem("nova_theme") || "dark");

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("nova_theme", theme);
  }, [theme]);

  return { theme, setTheme };
}
