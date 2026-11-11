/* prblm-builder — measuring preview frames (shared by the canvas and the Block library). */
(function () {
  "use strict";
  var SKIP_TAGS = /^(LINK|STYLE|SCRIPT|META|NOSCRIPT|TEMPLATE|BASE|TITLE)$/;

  // The part of a frame to show, in the frame's own pixels: {top, height}. Measures the
  // section's visible, in-flow elements (between the <template data-prblm-start/end>
  // markers when the site's own preview template is used, else <body>'s), margins included. Skips <link>/<style>/<script>,
  // hidden elements and absolutely positioned ones (decorations, closed mobile menus).
  // Fixed elements count only for a header/footer (`chrome`), when they sit on screen at
  // the top and aren't a full-screen overlay — a site header with position:fixed.
  // Also returns the section's outer margins `mt` / `mb` as the live page would see them
  // (including a first / last child's margin that collapses through the section's edge), and
  // `collapse`: whether its container lets them merge with the neighbouring sections' margins
  // (normal block flow; not a flex / grid wrapper in the site's preview template).
  function edgeMargin(win, el, side, depth) {
    var cs = win.getComputedStyle(el);
    var own = parseFloat(side === "top" ? cs.marginTop : cs.marginBottom) || 0;
    if (depth > 3) return own;
    var pad = parseFloat(side === "top" ? cs.paddingTop : cs.paddingBottom) || 0;
    var border = parseFloat(side === "top" ? cs.borderTopWidth : cs.borderBottomWidth) || 0;
    var blockish = cs.display === "block" || cs.display === "list-item";
    var newContext = cs.overflow !== "visible" || cs.position === "absolute" || cs.position === "fixed" ||
                     (cs.float && cs.float !== "none");
    // A bottom margin only passes through a box whose height comes from its content.
    var fixedHeight = side === "bottom" && (el.style.height || (parseFloat(cs.minHeight) || 0) > 0);
    if (!blockish || newContext || pad || border || fixedHeight) return own;
    var kids = Array.prototype.filter.call(el.children, function (k) {
      if (SKIP_TAGS.test(k.tagName)) return false;
      var ks = win.getComputedStyle(k);
      return ks.display !== "none" && ks.position !== "absolute" && ks.position !== "fixed";
    });
    var edge = side === "top" ? kids[0] : kids[kids.length - 1];
    if (!edge) return own;
    var inner = edgeMargin(win, edge, side, depth + 1);
    return Math.max(own, inner);
  }
  function measure(d, chrome) {
    var win = d.defaultView, start = d.querySelector("template[data-prblm-start]");
    if (!d.body || !win) return { top: 0, height: 0, mt: 0, mb: 0, collapse: false };
    var plain = !start, items = [];
    if (start) {
      for (var n = start.nextElementSibling; n && !n.hasAttribute("data-prblm-end"); n = n.nextElementSibling) items.push(n);
    } else items = Array.prototype.slice.call(d.body.children);
    var vw = win.innerWidth, vh = win.innerHeight, sy = win.scrollY || 0;
    var top = Infinity, bottom = 0, first = null, last = null;
    function visit(list, depth) {
      Array.prototype.forEach.call(list, function (c) {
        if (SKIP_TAGS.test(c.tagName)) return;
        var cs = win.getComputedStyle(c);
        if (cs.display === "none" || cs.visibility === "hidden" || cs.position === "absolute") return;
        var r = c.getBoundingClientRect();
        if (!r.width || !r.height) {
          // A wrapper with no size of its own (display:contents, or holding only a fixed
          // header): look inside it.
          if (depth < 3) visit(c.children, depth + 1);
          return;
        }
        if (cs.position === "fixed" &&
            (!chrome || r.top > 1 || r.bottom <= 0 || r.right <= 0 || r.left >= vw || r.height >= vh * 0.9)) return;
        if (cs.position !== "fixed") { if (!first) first = c; last = c; }
        top = Math.min(top, r.top + sy - (parseFloat(cs.marginTop) || 0));
        bottom = Math.max(bottom, r.bottom + sy + (parseFloat(cs.marginBottom) || 0));
      });
    }
    visit(items, 0);
    var mt = first ? edgeMargin(win, first, "top", 0) : 0;
    var mb = last ? edgeMargin(win, last, "bottom", 0) : 0;
    if (last) bottom = Math.max(bottom, last.getBoundingClientRect().bottom + sy + mb);
    var parent = start ? start.parentElement : d.body, ps = win.getComputedStyle(parent);
    var collapse = !!first && !/flex|grid/.test(ps.display);
    // A plain frame shows from its top; a section's own body height also covers inline
    // content and margins that collapse through <body> (not for chrome: a header's
    // absolutely positioned menu would inflate it).
    if (plain && !chrome) bottom = Math.max(bottom, d.body.scrollHeight);
    if (!bottom) return { top: 0, height: 0, mt: 0, mb: 0, collapse: false };
    if (plain || top === Infinity) top = 0;
    else if (first) top = Math.max(0, Math.min(top, first.getBoundingClientRect().top + sy - mt));
    return { top: Math.floor(top), height: Math.ceil(bottom - top), mt: mt, mb: mb, collapse: collapse };
  }

  window.prblmFrames = { measure: measure };
})();
