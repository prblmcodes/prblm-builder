/* prblm-builder — built-in blocks. Tiny, dependency-free enhancements.
   Everything works without it; it only adds behaviour (e.g. the header's mobile menu). */
(function () {
  "use strict";
  function ready(fn) { if (document.readyState !== "loading") fn(); else document.addEventListener("DOMContentLoaded", fn); }
  ready(function () {
    // Header mobile menu: a button toggles the nav (aria-expanded drives the CSS).
    document.querySelectorAll("[data-pbk-menu-toggle]").forEach(function (btn) {
      if (btn.dataset.pbkBound) return; btn.dataset.pbkBound = "1";
      var nav = document.getElementById(btn.getAttribute("aria-controls"));
      if (!nav) return;
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", open ? "false" : "true");
        nav.classList.toggle("is-open", !open);
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") {
          btn.setAttribute("aria-expanded", "false"); nav.classList.remove("is-open"); btn.focus();
        }
      });
    });
  });
})();
