/* prblm-builder — foldable groups (Block library + Layout sidebar).
   Any [data-fold="key"] button folds every [data-fold-body="key"] on the page, so a group
   folded in the sidebar is also hidden in the preview column. Remembered per browser. */
(function () {
  "use strict";
  var STORE = "prblm-builder:folded:" + (document.body.getAttribute("data-fold-store") || "default");
  var state = {};
  try { state = JSON.parse(window.localStorage.getItem(STORE) || "{}") || {}; } catch (e) { state = {}; }

  function apply(key, folded) {
    document.querySelectorAll('[data-fold-body="' + key + '"]').forEach(function (el) { el.hidden = folded; });
    document.querySelectorAll('[data-fold="' + key + '"]').forEach(function (b) {
      b.setAttribute("aria-expanded", folded ? "false" : "true");
    });
  }
  Object.keys(state).forEach(function (k) { if (state[k]) apply(k, true); });

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-fold]");
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    var key = btn.getAttribute("data-fold");
    var folded = btn.getAttribute("aria-expanded") !== "false";
    if (folded) state[key] = true; else delete state[key];
    apply(key, folded);
    try { window.localStorage.setItem(STORE, JSON.stringify(state)); } catch (err) {}
    document.dispatchEvent(new CustomEvent("prblm-builder:fold", { detail: { key: key, folded: folded } }));
  }, true);
})();
