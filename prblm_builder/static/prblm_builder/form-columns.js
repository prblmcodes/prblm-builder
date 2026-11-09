/* prblm-builder — two-column block forms: the one rule CSS can't express.

   form-columns.css lays the fields out instantly (short ones two per row, long / grouped
   ones full width). This script only finds a short field left *without a partner* — the
   last of an odd run before a full-width field, or at the end — and gives it
   `pb-col-full`, so it doesn't sit at half width next to an empty space. It runs straight
   from a MutationObserver (before the browser paints), so new blocks don't flicker. */
(function () {
  "use strict";
  var script = document.currentScript;
  var SITE = script && script.getAttribute("data-site-blocks") === "1";
  var CONTAINERS = ".pbk-form, .pbk-form .struct-block, .pbk-form [data-block-settings], " +
    ".w-panel.pbk-form > .w-panel__content" + (SITE ? ", .struct-block, [data-block-settings]" : "");

  function isField(el) {
    return el.hasAttribute("data-contentpath") || el.classList.contains("w-panel__wrapper");
  }

  function layout(container) {
    var style = getComputedStyle(container);
    if (style.display !== "grid") return;
    var pending = null, lastTop = null;
    Array.prototype.forEach.call(container.children, function (c) {
      if (!isField(c)) return;
      c.classList.remove("pb-col-full");
    });
    var cols = style.gridTemplateColumns.split(" ").length;
    Array.prototype.forEach.call(container.children, function (c) {
      if (!isField(c) || c.hidden || c.offsetParent === null) return;
      var span = getComputedStyle(c).gridColumnStart === "auto" && cols > 1 &&
                 getComputedStyle(c).gridColumnEnd === "auto";
      if (!span) { if (pending) pending.classList.add("pb-col-full"); pending = null; return; }
      pending = pending ? null : c;
    });
    if (pending) pending.classList.add("pb-col-full");
  }

  // Re-check a form when its own width changes (window resize, sidebar opening / closing,
  // which animates — so the window's resize event alone fires too early).
  var watched = typeof WeakSet !== "undefined" ? new WeakSet() : null;
  var sizes = typeof ResizeObserver !== "undefined"
    ? new ResizeObserver(function (entries) { entries.forEach(function (e) { layout(e.target); }); })
    : null;

  function layoutAll() {
    document.querySelectorAll(CONTAINERS).forEach(function (c) {
      if (sizes && watched && !watched.has(c)) { watched.add(c); sizes.observe(c); }
      layout(c);
    });
  }

  function start() {
    layoutAll();
    var busy = false;
    new MutationObserver(function (records) {
      if (busy) return;
      // Typing in a rich-text editor changes its DOM on every key: not a layout change.
      var relevant = records.some(function (r) {
        var t = r.target.nodeType === 1 ? r.target : r.target.parentElement;
        return !(t && t.closest && t.closest(".Draftail-Editor, [contenteditable], .pb-tip, .w-autosave-indicator"));
      });
      if (!relevant) return;
      busy = true;
      try { layoutAll(); } finally { busy = false; }
    }).observe(document.body, { childList: true, subtree: true, attributes: true,
                                attributeFilter: ["hidden", "aria-expanded"] });
    if (!sizes) window.addEventListener("resize", layoutAll);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
