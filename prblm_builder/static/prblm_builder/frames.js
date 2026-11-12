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
  // The margin at a section's top / bottom edge as the page sees it: its own, merged with a
  // first / last child's margin that collapses through the edge. CSS merges them as
  // (largest positive) + (most negative), so a negative margin pulls the section over its
  // neighbour.
  function edgeMargin(win, el, side, depth) {
    var r = edgeMargins(win, el, side, depth);
    return r[0] + r[1];
  }
  function edgeMargins(win, el, side, depth) {
    var cs = win.getComputedStyle(el);
    var own = parseFloat(side === "top" ? cs.marginTop : cs.marginBottom) || 0;
    var mine = [Math.max(0, own), Math.min(0, own)];
    if (depth > 3) return mine;
    var pad = parseFloat(side === "top" ? cs.paddingTop : cs.paddingBottom) || 0;
    var border = parseFloat(side === "top" ? cs.borderTopWidth : cs.borderBottomWidth) || 0;
    var blockish = cs.display === "block" || cs.display === "list-item";
    var newContext = cs.overflow !== "visible" || cs.position === "absolute" || cs.position === "fixed" ||
                     (cs.float && cs.float !== "none");
    // A bottom margin only passes through a box whose height comes from its content.
    var fixedHeight = side === "bottom" && (el.style.height || (parseFloat(cs.minHeight) || 0) > 0);
    if (!blockish || newContext || pad || border || fixedHeight) return mine;
    var kids = Array.prototype.filter.call(el.children, function (k) {
      if (SKIP_TAGS.test(k.tagName)) return false;
      var ks = win.getComputedStyle(k);
      return ks.display !== "none" && ks.position !== "absolute" && ks.position !== "fixed";
    });
    var edge = side === "top" ? kids[0] : kids[kids.length - 1];
    if (!edge) return mine;
    var inner = edgeMargins(win, edge, side, depth + 1);
    return [Math.max(mine[0], inner[0]), Math.min(mine[1], inner[1])];
  }
  function transparent(cs) {
    var bg = cs.backgroundColor || "";
    var clear = bg === "transparent" || /rgba\([^)]*,\s*0\)$/.test(bg.replace(/\s+/g, " "));
    return clear && (!cs.backgroundImage || cs.backgroundImage === "none");
  }
  // A header that sits on top of the page's first section on the live site: fixed or
  // absolutely positioned, with no background of its own (nor its wrappers, nor a
  // full-width bar inside it) — typically white text over a dark hero.
  function overlayHeader(win, el) {
    var cs = win.getComputedStyle(el);
    if (cs.position !== "fixed" && cs.position !== "absolute") return false;
    for (var a = el; a && a !== el.ownerDocument.body; a = a.parentElement) {
      if (!transparent(win.getComputedStyle(a))) return false;
    }
    var w = el.getBoundingClientRect().width, h = el.getBoundingClientRect().height;
    return !Array.prototype.some.call(el.children, function (k) {
      var r = k.getBoundingClientRect();
      return r.width >= w * 0.9 && r.height >= h * 0.5 && !transparent(win.getComputedStyle(k));
    });
  }
  // In-flow elements drawn outside the section's own box — pulled up or down by negative
  // margins (or transforms) so they overlap the neighbouring section on the live page.
  // Skips absolutely / fixed positioned things (decorations, off-canvas menus) and
  // anything inside a box that clips its overflow. → {top, bottom} in document pixels.
  function pokes(win, d, root, top, bottom) {
    var sy = win.scrollY || 0, vw = win.innerWidth, out = { top: top, bottom: bottom };
    var all = root.getElementsByTagName("*"), n = Math.min(all.length, 4000);
    for (var i = 0; i < n; i++) {
      var el = all[i];
      if (SKIP_TAGS.test(el.tagName)) continue;
      var r = el.getBoundingClientRect();
      if (!r.width || !r.height || r.right <= 0 || r.left >= vw) continue;
      var t = r.top + sy, b = r.bottom + sy;
      if (t >= out.top - 0.5 && b <= out.bottom + 0.5) continue;
      if (t < -3000 || b > out.bottom + 3000) continue;
      var ok = true;
      for (var a = el; a && a !== d.body && a !== d.documentElement; a = a.parentElement) {
        var cs = win.getComputedStyle(a);
        if (cs.position === "absolute" || cs.position === "fixed" || cs.display === "none" ||
            cs.visibility === "hidden" || (a !== el && cs.overflow !== "visible")) { ok = false; break; }
      }
      if (!ok) continue;
      if (t < out.top) out.top = t;
      if (b > out.bottom) out.bottom = b;
    }
    return out;
  }
  // Returns, in the frame's own pixels:
  //   top / height  the part to show (margins included; parts drawn above / below the
  //                 section by negative margins included too)
  //   mt / mb       the section's positive outer margins (for merging with neighbours)
  //   collapse      whether its container lets those margins merge (see above)
  //   above / below how far it reaches over the previous / next section (negative margins)
  //   pad           the outer element's top / bottom padding and where they sit (from the
  //                 top / bottom of the shown part)
  //   rawTop        the topmost drawn point (negative = cut off above the document)
  //   overlay       (headers) a transparent fixed/absolute header over the first section
  function measure(d, chrome) {
    var win = d.defaultView, start = d.querySelector("template[data-prblm-start]");
    var none = { top: 0, height: 0, mt: 0, mb: 0, collapse: false, above: 0, below: 0, rawTop: 0, overlay: false };
    if (!d.body || !win) return none;
    var plain = !start, items = [];
    if (start) {
      for (var n = start.nextElementSibling; n && !n.hasAttribute("data-prblm-end"); n = n.nextElementSibling) items.push(n);
    } else items = Array.prototype.slice.call(d.body.children);
    var vw = win.innerWidth, vh = win.innerHeight, sy = win.scrollY || 0;
    var top = Infinity, bottom = 0, first = null, last = null, floating = null;
    function visit(list, depth) {
      Array.prototype.forEach.call(list, function (c) {
        if (SKIP_TAGS.test(c.tagName)) return;
        var cs = win.getComputedStyle(c);
        if (cs.display === "none" || cs.visibility === "hidden") return;
        // Absolutely positioned: decorations / closed menus — except a header's own bar.
        if (cs.position === "absolute" && !(chrome && depth === 0)) return;
        var r = c.getBoundingClientRect();
        if (!r.width || !r.height) {
          // A wrapper with no size of its own (display:contents, or holding only a fixed
          // header): look inside it.
          if (depth < 3) visit(c.children, depth + 1);
          return;
        }
        var lifted = cs.position === "fixed" || cs.position === "absolute";
        if (lifted &&
            (!chrome || r.top > 1 || r.bottom <= 0 || r.right <= 0 || r.left >= vw || r.height >= vh * 0.9)) return;
        if (lifted) { if (!floating) floating = c; }
        else { if (!first) first = c; last = c; }
        top = Math.min(top, r.top + sy - Math.max(0, parseFloat(cs.marginTop) || 0));
        bottom = Math.max(bottom, r.bottom + sy + Math.max(0, parseFloat(cs.marginBottom) || 0));
      });
    }
    visit(items, 0);
    var mtEdge = first ? edgeMargin(win, first, "top", 0) : 0;
    var mbEdge = last ? edgeMargin(win, last, "bottom", 0) : 0;
    // Where the section starts / ends in the page's flow (its margins included).
    var flowTop = first ? first.getBoundingClientRect().top + sy - mtEdge : top;
    var flowBottom = last ? last.getBoundingClientRect().bottom + sy + mbEdge : bottom;
    if (last) bottom = Math.max(bottom, flowBottom);
    if (first) top = Math.min(top, flowTop);
    var parent = start ? start.parentElement : d.body, ps = win.getComputedStyle(parent);
    var collapse = !!first && !/flex|grid/.test(ps.display);
    var flowEnd = bottom;
    // A plain frame shows from its top; a section's own body height also covers inline
    // content and margins that collapse through <body> (not for chrome: a header's
    // absolutely positioned menu would inflate it).
    if (plain && !chrome) bottom = Math.max(bottom, d.body.getBoundingClientRect().top + sy + d.body.scrollHeight);
    if (!bottom) return none;
    var above = 0, below = 0;
    if (!chrome && first) {
      var p = pokes(win, d, start ? parent : d.body, plain ? Math.max(0, top) : top, flowEnd);
      top = Math.min(top, p.top);
      bottom = Math.max(bottom, p.bottom);
      above = Math.max(0, flowTop - p.top);
      below = Math.max(0, p.bottom - flowBottom);
    }
    var rawTop = top === Infinity ? 0 : top;
    // Nothing can show above the document's top (fitFrame pads the frame when rawTop < 0).
    top = (plain || top === Infinity) ? 0 : Math.max(0, top);
    var height = Math.ceil(bottom - top);
    // The section's own padding (its outer element's top / bottom), and where it starts /
    // ends inside the shown part — for the canvas's "Padding" bands.
    var pad = { top: 0, topAt: 0, bottom: 0, bottomAt: 0 };
    if (first && last && !chrome) {
      pad.top = parseFloat(win.getComputedStyle(first).paddingTop) || 0;
      pad.bottom = parseFloat(win.getComputedStyle(last).paddingBottom) || 0;
      pad.topAt = first.getBoundingClientRect().top + sy - Math.floor(top);
      pad.bottomAt = Math.floor(top) + height - (last.getBoundingClientRect().bottom + sy);
    }
    return { top: Math.floor(top), height: height, mt: Math.max(0, mtEdge), mb: Math.max(0, mbEdge),
             collapse: collapse, above: Math.round(above), below: Math.round(below), rawTop: Math.floor(rawTop),
             pad: pad, overlay: !!(chrome && floating && !first && overlayHeader(win, floating)) };
  }

  // measure() for an iframe, after making room for anything drawn above the document's
  // top (a negative top margin): <html> gets that much padding, so nothing is cut off.
  function measureFrame(frame, chrome) {
    var d = frame.contentDocument;
    if (frame._pbDoc !== d) { frame._pbDoc = d; frame._pbPad = 0; frame._pbBg = null; }   // reloaded
    var m = measure(d, chrome);
    if (chrome || !d.documentElement) return m;
    var pad = frame._pbPad || 0, need = Math.max(0, Math.ceil(pad - m.rawTop));
    if (need !== pad) {
      if (need) d.documentElement.style.setProperty("padding-top", need + "px", "important");
      else d.documentElement.style.removeProperty("padding-top");
      frame._pbPad = need;
      m = measure(d, chrome);
    }
    return m;
  }
  // The colour behind a frame's content (its <body>, else <html>, else white) — used
  // when the frame is made see-through.
  function pageBackground(d) {
    var win = d.defaultView;
    var b = win.getComputedStyle(d.body), h = win.getComputedStyle(d.documentElement);
    if (!transparent(b)) return b.backgroundColor;
    if (!transparent(h)) return h.backgroundColor;
    return "#fff";
  }
  window.prblmFrames = { measure: measure, measureFrame: measureFrame, transparent: transparent,
                         pageBackground: pageBackground };
})();
