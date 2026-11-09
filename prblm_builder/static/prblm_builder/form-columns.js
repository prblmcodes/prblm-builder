/* prblm-builder — two-column block forms in the Wagtail admin.

   Short fields (text, email, URL, number, dropdown, checkbox, date, choosers) share a row,
   two per row; long ones (textarea, rich text) and grouped ones (lists, nested blocks) take
   the full width, and so does a short field left without a partner. Built-in blocks
   (``.pbk-form``) always; with PRBLM_BUILDER_FORM_COLUMNS = "all" every block form.
   If Wagtail's form markup ever changes, nothing matches and forms keep their normal look. */
(function () {
  "use strict";
  var script = document.currentScript;
  var MODE = (script && script.getAttribute("data-mode")) || "builtin";
  var MIN_WIDTH = 560;   // narrower than this: one column
  // Block forms (StreamField) and the plugin's own panel groups (e.g. the Theme page:
  // a MultiFieldPanel with classname "pbk-form").
  var PANEL = ".w-panel.pbk-form > .w-panel__content";
  var CONTAINERS = MODE === "all"
    ? ".struct-block, .pbk-form, [data-block-settings], " + PANEL
    : ".pbk-form, .pbk-form .struct-block, .pbk-form [data-block-settings], " + PANEL;

  // A field: a block field (data-contentpath) or a model-form field panel.
  function isField(el) {
    return el.hasAttribute && (el.hasAttribute("data-contentpath") || el.classList.contains("w-panel__wrapper"));
  }
  function visible(el) { return !el.hidden && el.offsetParent !== null; }
  function isWide(el) {
    // Long text, rich text, or a group of fields (a list, a nested block, a stream).
    // (Lists and streams are recognised by their containers, so an empty list counts too.
    // A model-form field panel holds its own [data-contentpath] element, so for those only
    // the content counts.)
    var long = 'textarea, .Draftail-Editor, [data-draftail-input], [data-streamfield-list-container], ' +
               '[data-streamfield-list-count], [data-streamfield-stream-container]';
    if (el.classList.contains("w-panel__wrapper")) return !!el.querySelector(long);
    return !!el.querySelector(long + ", [data-contentpath]");
  }

  function layout(container) {
    var children = Array.prototype.filter.call(container.children, function (c) { return c.nodeType === 1; });
    var fields = children.filter(isField);
    if (!fields.length) return;
    var single = container.clientWidth > 0 && container.clientWidth < MIN_WIDTH;
    container.classList.toggle("pb-cols", !single);
    children.forEach(function (c) { c.classList.remove("pb-col-half", "pb-col-full"); });
    if (single) return;
    // Anything that isn't a field (e.g. the settings area) spans the full width (CSS default).
    var pending = null;
    fields.forEach(function (f) {
      if (!visible(f)) return;
      if (isWide(f)) {
        if (pending) { pending.classList.add("pb-col-full"); pending = null; }
        f.classList.add("pb-col-full");
      } else if (pending) {
        pending.classList.add("pb-col-half"); f.classList.add("pb-col-half"); pending = null;
      } else {
        pending = f;
      }
    });
    if (pending) pending.classList.add("pb-col-full");
  }

  var queued = false;
  function layoutAll() {
    queued = false;
    document.querySelectorAll(CONTAINERS).forEach(layout);
  }
  function schedule() { if (!queued) { queued = true; requestAnimationFrame(layoutAll); } }

  function start() {
    var root = document.querySelector("form[data-edit-form]") || document.querySelector("main form") || document.body;
    layoutAll();
    // Re-run when blocks / list items are added, fields hide or show, or panels open.
    new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var t = records[i].target;
        if (t.closest && t.closest(".pb-tip, .w-autosave-indicator")) continue;
        schedule(); return;
      }
    }).observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "aria-expanded"] });
    window.addEventListener("resize", schedule);
    document.addEventListener("click", function () { setTimeout(schedule, 0); }, true);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
