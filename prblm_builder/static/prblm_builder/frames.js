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
  function measure(d, chrome) {
    var win = d.defaultView, start = d.querySelector("template[data-prblm-start]");
    if (!d.body || !win) return { top: 0, height: 0 };
    var plain = !start, items = [];
    if (start) {
      for (var n = start.nextElementSibling; n && !n.hasAttribute("data-prblm-end"); n = n.nextElementSibling) items.push(n);
    } else items = Array.prototype.slice.call(d.body.children);
    var vw = win.innerWidth, vh = win.innerHeight, sy = win.scrollY || 0;
    var top = Infinity, bottom = 0;
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
        top = Math.min(top, r.top + sy - (parseFloat(cs.marginTop) || 0));
        bottom = Math.max(bottom, r.bottom + sy + (parseFloat(cs.marginBottom) || 0));
      });
    }
    visit(items, 0);
    // A plain frame shows from its top; a section's own body height also covers inline
    // content and margins that collapse through <body> (not for chrome: a header's
    // absolutely positioned menu would inflate it).
    if (plain && !chrome) bottom = Math.max(bottom, d.body.scrollHeight);
    if (!bottom) return { top: 0, height: 0 };
    top = plain || top === Infinity ? 0 : Math.max(0, top);
    return { top: Math.floor(top), height: Math.ceil(bottom - top) };
  }

  window.prblmFrames = { measure: measure };
})();
