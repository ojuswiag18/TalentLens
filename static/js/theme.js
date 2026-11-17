/* TalentLens theme switching with localStorage persistence */
(function () {
  var STORAGE_KEY = "theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  }

  function applyTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);
    if (persist !== false) {
      try {
        localStorage.setItem(STORAGE_KEY, theme);
      } catch (e) { /* ignore */ }
    }
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      var label = btn.querySelector(".label");
      if (label) label.textContent = theme === "dark" ? "Dark Mode" : "Light Mode";
    });
  }

  var saved = null;
  try {
    saved = localStorage.getItem(STORAGE_KEY);
  } catch (e) { /* ignore */ }

  var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(saved || (prefersDark ? "dark" : "light"));

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-theme-toggle]");
    if (!btn) return;
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
  });

  window.TalentLensTheme = { current: currentTheme, apply: applyTheme };
})();