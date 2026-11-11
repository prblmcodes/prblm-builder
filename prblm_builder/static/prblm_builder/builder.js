/* prblm-builder — one-page drag-and-drop canvas (vanilla + SortableJS). */
(function () {
  "use strict";
  var wrap = document.querySelector(".pb-wrap");
  if (!wrap) return;
  var CFG = {
    preview: wrap.dataset.previewUrl, check: wrap.dataset.checkUrl,
    context: wrap.dataset.context,
  };
  var canvas = document.getElementById("pb-canvas");   // the .pb-page
  var empty = document.getElementById("pb-empty");
  var toast = document.getElementById("pb-toast");

  // Embedded in the page editor's "Layout" tab (iframe, same origin). There the
  // builder has no Save of its own: it writes the arrangement into hidden inputs
  // on the parent edit form, so Wagtail's own Save draft / Publish saves it.
  var EMBED = document.body.classList.contains("pb-embed");
  // ⚙ section settings per block type (Meta.builder_settings): {type: {fields, defaults}}
  var SCHEMA = {};
  try { SCHEMA = JSON.parse(document.getElementById("pb-settings-schema").textContent) || {}; } catch (e) {}
  var INITIAL_IDS = [];   // ids known at load — tells a Layout-tab delete apart
                          // from a block added in the normal editor (see layout.py)
  var dirtied = false;    // only flag the page 'unsaved' after a real user change

  function parentForm() {
    try {
      var d = window.parent.document;
      return d.querySelector("form[data-edit-form]") || d.querySelector("[data-edit-form]") ||
             d.querySelector("#page-edit-form") || d.querySelector("main form") || d.querySelector("form");
    } catch (e) { return null; }
  }
  function setHidden(form, name, val) {
    var i = form.querySelector('input[name="' + name + '"]');
    if (!i) { i = window.parent.document.createElement("input"); i.type = "hidden"; i.name = name; form.appendChild(i); }
    i.value = val;
    if (dirtied) { try { i.dispatchEvent(new Event("change", { bubbles: true })); } catch (e) {} }
  }
  // The order/membership of sections, to notice structure changes (vs settings changes).
  var lastSig = null;
  function structureSig(items) { return items.map(function (s) { return s.type + ":" + s.id; }).join("|"); }
  function syncLayout() {
    if (!EMBED) return;
    var form = parentForm(); if (!form) return;
    var items = collect();
    if (lastSig === null) lastSig = structureSig(items);
    // Only write the hidden fields once the editor actually changed something: Wagtail
    // auto-saves whenever the form differs from how it loaded, so writing them on load
    // would create a pointless draft each time a page is opened.
    if (!dirtied) return;
    try {
      setHidden(form, "_pb_layout", JSON.stringify(items));
      setHidden(form, "_pb_initial", JSON.stringify(INITIAL_IDS));
    } catch (e) {}
    try {
      // Tell the editor page (save banner; tab sync after structure changes).
      window.parent.document.dispatchEvent(new CustomEvent("prblm-builder:dirty"));
      var sig = structureSig(items);
      if (sig !== lastSig) {
        lastSig = sig;
        window.parent.document.dispatchEvent(new CustomEvent("prblm-builder:structure"));
      }
    } catch (e) {}
  }

  // The Content tab's own input for a setting of a section that's already in the form
  // (``<field>-N-value-<name>``, found through the hidden ``<field>-N-id``), or null.
  function contentInput(id, name) {
    var form = parentForm(), field = wrap.dataset.fieldName;
    if (!form || !field) return null;
    var ids = form.querySelectorAll('input[name^="' + field + '-"][name$="-id"]');
    for (var i = 0; i < ids.length; i++) {
      if (ids[i].value !== String(id)) continue;
      var m = ids[i].name.match(new RegExp("^" + field + "-(\\d+)-id$"));
      if (!m) continue;
      var deleted = form.querySelector('[name="' + field + "-" + m[1] + '-deleted"]');
      if (deleted && deleted.value) continue;
      return form.querySelector('[name="' + field + "-" + m[1] + "-value-" + name + '"]');
    }
    return null;
  }
  function writeContentInput(input, value) {
    if (input.type === "checkbox") input.checked = !!value;
    else input.value = value == null ? "" : value;
    try {
      window.parent.__prblmSyncing = true;   // don't echo this back to the canvas
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } finally { window.parent.__prblmSyncing = false; }
  }

  function uuid() {
    return (crypto.randomUUID && crypto.randomUUID()) ||
      "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        var r = (Math.random() * 16) | 0; return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      });
  }

  /* ---------- preview iframes: lazy load + auto height (section frames) ---------- */
  // Embedded, the editor column is too narrow to render sections at real width, so
  // each frame renders at a fixed DESKTOP width and is scaled down to fit its host.
  var CANVAS_W = parseInt(wrap.dataset.canvasWidth, 10) || 1280;   // PRBLM_BUILDER_CANVAS_WIDTH
  // Frames keep a viewport at least this tall, so `vh` sizes (min-h-[70vh], h-screen)
  // resolve as on a typical screen instead of against a frame sized to its content.
  var CANVAS_H = parseInt(wrap.dataset.canvasHeight, 10) || 900;   // PRBLM_BUILDER_CANVAS_HEIGHT
  var measureFrame = window.prblmFrames.measureFrame;   // frames.js
  // PRBLM_BUILDER_CANVAS_OVERLAP: frames overlap where the live page does (a transparent
  // header over the first section; sections pulled over a neighbour by negative margins).
  var OVERLAP = wrap.dataset.canvasOverlap !== "0";
  // Let the page behind show through a frame (where it overlaps a neighbour): the frame's
  // own background moves onto its host, except over the overlapping strips.
  function setClear(frame, host, on, m, s, chrome) {
    var d = frame.contentDocument, st = d.getElementById("pb-clear");
    if (on && !frame._pbBg) frame._pbBg = window.prblmFrames.pageBackground(d);
    if (on && !st && d.head) {
      st = d.createElement("style"); st.id = "pb-clear";
      st.textContent = "html,body{background:transparent!important}";
      d.head.appendChild(st);
    }
    if (!on && st) st.remove();
    frame.classList.toggle("pb-frame-clear", on);
    if (!on) { host.style.background = ""; return; }
    if (chrome) { host.style.background = "transparent"; return; }
    var a = Math.round(m.above * s), b = Math.round((m.height - m.below) * s), bg = frame._pbBg;
    host.style.background = "linear-gradient(to bottom,transparent " + a + "px," + bg + " " + a + "px," +
                            bg + " " + b + "px,transparent " + b + "px)";
  }

  // Size a section / header / footer frame. Embedded, it renders at the desktop width
  // and is scaled to fit its host; standalone, at the host's width. The iframe stays at
  // least CANVAS_H tall (for vh) and is shifted so only the measured part shows.
  function fitFrame(frame, chrome) {
    try {
      var host = frame.closest(".pb-sec") || frame.closest(".pb-chrome");
      var d = frame.contentDocument;
      if (!host || !d || !d.body || d.readyState === "loading") return;
      var s = EMBED ? (host.clientWidth || CANVAS_W) / CANVAS_W : 1;
      frame.style.width = EMBED ? CANVAS_W + "px" : "100%";
      var cur = parseFloat(frame.style.height) || 0;
      if (cur < CANVAS_H) { frame.style.height = CANVAS_H + "px"; cur = CANVAS_H; }
      var m = measureFrame(frame, chrome);
      if (chrome) {
        // A header/footer with nothing visible (an empty template / hook) takes no space.
        var blank = !m.height || (!(d.body.innerText || "").trim() &&
                                  !d.body.querySelector("img,svg,picture,video,iframe,canvas"));
        host.classList.toggle("pb-chrome-empty", blank);
        if (blank) { host.style.height = "0px"; return; }
      }
      var want = Math.max(CANVAS_H, m.top + m.height);
      // Content that grows with the frame (e.g. 100vh + more) would grow forever: allow
      // only a few enlargements.
      if (want > cur && (frame._pbGrow = (frame._pbGrow || 0) + 1) > 3) want = cur;
      if (want !== cur) frame.style.height = want + "px";
      frame.style.transform = "scale(" + s + ")" + (m.top ? " translateY(" + (-m.top) + "px)" : "");
      host.style.height = Math.round(m.height * s) + "px";
      var overlay = OVERLAP && chrome && m.overlay && host.dataset.chrome === "header";
      var reach = OVERLAP && !chrome && !!(m.above || m.below);
      setClear(frame, host, overlay || reach, m, s, chrome);
      host.classList.toggle("pb-chrome-overlay", !!overlay);
      host.classList.toggle("pb-pokes-down", OVERLAP && !chrome && !!m.below);
      host._pbM = { mt: m.mt || 0, mb: m.mb || 0, collapse: !!m.collapse, s: s,
                    above: OVERLAP ? m.above || 0 : 0, below: OVERLAP ? m.below || 0 : 0, overlay: !!overlay };
      if (host.classList.contains("pb-selected")) drawSpace(host);
      queueGaps();
    } catch (e) {}
  }
  // Neighbouring sections' margins merge on a live page (the gap is the larger of the two),
  // but each canvas frame counts its own: overlap each section with the one before it by
  // the smaller margin. Not where the container keeps them apart (flex / grid).
  var gapsQueued = false;
  function queueGaps() {
    if (gapsQueued) return; gapsQueued = true;
    requestAnimationFrame(function () { gapsQueued = false; applyGaps(); });
  }
  function applyGaps() {
    var hosts = [];
    var head = document.querySelector('.pb-chrome[data-chrome="header"]');
    var foot = document.querySelector('.pb-chrome[data-chrome="footer"]');
    function usable(h) { return h && !h.hidden && !h.classList.contains("pb-chrome-empty") && h._pbM; }
    if (usable(head)) hosts.push(head);
    Array.prototype.forEach.call(sections(), function (sec) { hosts.push(sec); });
    if (usable(foot)) hosts.push(foot);
    var prev = null;
    hosts.forEach(function (h) {
      var m = h._pbM, overlap = 0, p = prev && prev._pbM;
      if (p && m && p.overlay && h.classList.contains("pb-sec")) {
        overlap = prev.offsetHeight;          // a transparent header lies over the first section
      } else if (p && m) {
        if (m.collapse && p.collapse) overlap = Math.min(p.mb, m.mt) * m.s;
        // Reaching over a neighbour (negative margins): as far as the live page does.
        overlap += (p.below || 0) * p.s + (m.above || 0) * m.s;
      }
      h.style.marginTop = overlap ? (-Math.round(overlap)) + "px" : "";
      prev = m ? h : null;
    });
  }
  function fit(frame) { fitFrame(frame, false); }
  function fitChrome(frame) { fitFrame(frame, true); }
  function refitAll() {
    canvas.querySelectorAll(".pb-frame").forEach(function (f) { fit(f); });
    document.querySelectorAll(".pb-chrome-frame").forEach(function (f) { fitChrome(f); });
  }
  // Re-fit until the height settles (fonts, late layout), then stop; capped at ~6s.
  function settle(frame, fn) {
    clearInterval(frame._pbSettle);
    var host = frame.closest(".pb-sec") || frame.closest(".pb-chrome") || frame.closest(".pb-thumb");
    var last = -1, stable = 0, n = 0;
    fn(frame);
    frame._pbSettle = setInterval(function () {
      fn(frame);
      var h = host ? host.offsetHeight : 0;
      if (h === last) { if (++stable >= 2) clearInterval(frame._pbSettle); } else { stable = 0; last = h; }
      if (++n > 24) clearInterval(frame._pbSettle);
    }, 250);
  }
  // Keep a frame fitted after it loaded: size changes of the page, images finishing,
  // web fonts, and DOM changes (Alpine x-show, carousels, accordions…), throttled.
  function watchFrame(frame, fn) {
    var d = frame.contentDocument, win = d && d.defaultView;
    if (!d || !win) return;
    var queued = false;
    function later() {
      if (queued) return; queued = true;
      win.requestAnimationFrame(function () { queued = false; fn(frame); });
    }
    try {
      if (window.ResizeObserver) {
        var ro = new ResizeObserver(later);
        ro.observe(d.documentElement); if (d.body) ro.observe(d.body);
        var start = d.querySelector("template[data-prblm-start]");
        if (start && start.parentElement) ro.observe(start.parentElement);
      }
      d.addEventListener("load", later, true);           // images (load doesn't bubble)
      if (d.fonts && d.fonts.ready) d.fonts.ready.then(later);
      if (window.MutationObserver && d.body) {
        new MutationObserver(later).observe(d.body, { childList: true, subtree: true, attributes: true,
                                                      attributeFilter: ["class", "style", "hidden", "open"] });
      }
    } catch (e) {}
  }
  var io = ("IntersectionObserver" in window) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { var f = e.target; if (!f.src && f.dataset.src) f.src = f.dataset.src; io.unobserve(f); } });
  }, { rootMargin: "600px 0px" }) : null;

  function wirePreview(frame) {
    frame.style.height = CANVAS_H + "px";
    frame.addEventListener("load", function () {
      var host = frame.closest(".pb-sec");
      frame._pbGrow = 0;
      settle(frame, fit);
      if (host) host.classList.remove("pb-sec-loading");   // reveal the rendered section
      watchFrame(frame, fit);
    });
    if (io) io.observe(frame); else frame.src = frame.dataset.src;
  }

  /* ---------- sections ---------- */
  // Only the settings changed in the Layout tab (they're sent with the save, and shown
  // on the canvas before saving).
  function changedSettings(s) {
    var out = {};
    (s.changed || []).forEach(function (k) { out[k] = (s.settings || {})[k]; });
    return out;
  }
  function previewSrc(s) {
    var q = CFG.context + "&block=" + encodeURIComponent(s.type), url;
    if (s.copyFrom) url = CFG.preview + "?" + q + "&section=" + encodeURIComponent(s.copyFrom);
    else if (s.isNew) url = CFG.preview + "?" + q + "&demo=1";
    else url = CFG.preview + "?" + q + "&section=" + encodeURIComponent(s.id);
    var ch = changedSettings(s);
    if (Object.keys(ch).length) url += "&settings=" + encodeURIComponent(JSON.stringify(ch));
    return url;
  }
  function sectionState(c) {
    return { type: c.dataset.type, id: c.dataset.id,
             label: (c.querySelector(".pb-sec-name").firstChild.textContent || "").trim(),
             copyFrom: c.dataset.copyFrom || undefined,
             isNew: !!c.dataset.unsaved && !c.dataset.copyFrom,
             unedited: !!c.dataset.unedited,
             settings: JSON.parse(c.dataset.settings || "{}"),
             changed: JSON.parse(c.dataset.changed || "[]") };
  }

  // Section toolbar icons: one line-icon style, 17px inside 26px buttons.
  function svgIcon(inner) {
    return '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" ' +
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + inner + '</svg>';
  }
  var ICON = {
    grab: svgIcon('<circle cx="9" cy="6" r="1.2"/><circle cx="15" cy="6" r="1.2"/><circle cx="9" cy="12" r="1.2"/>' +
                  '<circle cx="15" cy="12" r="1.2"/><circle cx="9" cy="18" r="1.2"/><circle cx="15" cy="18" r="1.2"/>'),
    up: svgIcon('<path d="M6 15l6-6 6 6"/>'),
    down: svgIcon('<path d="M6 9l6 6 6-6"/>'),
    settings: svgIcon('<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/>' +
                      '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>'),
    copy: svgIcon('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
    dup: svgIcon('<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V6a2 2 0 0 1 2-2h10"/><path d="M14 11v6M11 14h6"/>'),
    del: svgIcon('<path d="M6 6l12 12M18 6L6 18"/>'),
  };

  function makeSection(s) {
    var el = document.createElement("section");
    el.className = "pb-sec pb-sec-loading"; el.dataset.id = s.id; el.dataset.type = s.type;
    if (s.copyFrom) el.dataset.copyFrom = s.copyFrom;
    // New sections, and saved ones still holding their demo content, get a badge so
    // placeholder text isn't published by accident.
    var unedited = !!(s.isNew || s.unedited);
    if (unedited) el.dataset.unedited = "1";
    var sch = SCHEMA[s.type];
    el.dataset.settings = JSON.stringify(s.settings || (sch && sch.defaults) || {});
    el.dataset.changed = JSON.stringify(s.changed || []);
    el.innerHTML =
      '<iframe class="pb-frame" title="preview" scrolling="no"></iframe>' +
      (unedited ? '<span class="pb-unedited" title="This section still has demo content \u2014 edit it in the Content tab">Not edited yet</span>' : '') +
      '<div class="pb-sec-hit"></div>' +
      '<div class="pb-sec-bar">' +
        '<span class="pb-sec-name"></span>' +
        '<span class="pb-sec-ctrls">' +
          '<button class="pb-grab" data-act="grab" aria-label="Drag to move" data-tip="Drag to move this section">' + ICON.grab + '</button>' +
          '<button data-act="up" aria-label="Move up" data-tip="Move up">' + ICON.up + '</button>' +
          '<button data-act="down" aria-label="Move down" data-tip="Move down">' + ICON.down + '</button>' +
          (sch ? '<button data-act="settings" aria-haspopup="dialog" aria-label="Section settings" data-tip="Settings (background, anchor ID…)">' + ICON.settings + '</button>' : '') +
          '<button data-act="copy" aria-label="Copy section" data-tip="Copy section (Ctrl/⌘+C)">' + ICON.copy + '</button>' +
          '<button data-act="dup" aria-label="Duplicate" data-tip="Duplicate (adds a copy right below)">' + ICON.dup + '</button>' +
          '<button class="pb-del" data-act="del" aria-label="Remove section" data-tip="Remove this section">' + ICON.del + '</button>' +
        '</span>' +
      '</div>';
    el.querySelector(".pb-sec-name").textContent = s.label || s.type;
    el.querySelector(".pb-sec-name").insertAdjacentHTML("beforeend",
      (s.isNew || s.copyFrom) ? ' <span class="pb-sec-tag pb-sec-tag-demo">demo</span>'
                              : ' <span class="pb-sec-tag pb-sec-tag-live">live</span>');
    el.querySelector(".pb-frame").dataset.src = previewSrc(s);
    if (s.isNew || s.copyFrom) el.dataset.unsaved = "1";
    return el;
  }

  function addSection(s, atStart) {
    var el = makeSection(s);
    if (atStart && canvas.querySelector(".pb-sec")) canvas.insertBefore(el, canvas.querySelector(".pb-sec"));
    else canvas.appendChild(el);
    wirePreview(el.querySelector(".pb-frame"));
    refresh();
    return el;
  }

  function sections() { return canvas.querySelectorAll(".pb-sec"); }

  function refresh() {
    var secs = sections();
    empty.style.display = secs.length ? "none" : "";
    secs.forEach(function (c, i) {
      c.querySelector('[data-act="up"]').disabled = (i === 0);
      c.querySelector('[data-act="down"]').disabled = (i === secs.length - 1);
    });
    syncLayout();   // keep the parent edit form's hidden layout fields in step
    queueGaps();    // neighbours changed: re-merge the gaps between sections
  }

  function select(sec) {
    sections().forEach(function (s) { s.classList.toggle("pb-selected", s === sec); drawSpace(s); });
  }
  // The selected section's margins (space above / below its content), shown as striped
  // bands with their size — explains why neighbouring sections' spacing overlaps.
  function drawSpace(sec) {
    Array.prototype.slice.call(sec.querySelectorAll(".pb-space")).forEach(function (b) { b.remove(); });
    var m = sec._pbM;
    if (!sec.classList.contains("pb-selected") || !m) return;
    [["top", m.mt], ["bottom", m.mb]].forEach(function (side) {
      var px = Math.round(side[1] || 0);
      if (px < 1) return;
      var band = document.createElement("div");
      band.className = "pb-space pb-space-" + side[0];
      band.style.height = Math.max(2, Math.round(px * m.s)) + "px";
      band.innerHTML = '<span class="pb-space-label">Space \u00b7 ' + px + "px</span>";
      band.title = (side[0] === "top" ? "Space above" : "Space below") + " this section's content (its margin). " +
                   "Next to another section, the larger of the two spaces is used.";
      sec.appendChild(band);
    });
  }

  /* ---------- undo / redo (Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z or Ctrl+Y) ---------- */
  var history = [], hi = -1, restoring = false;
  function snapshot() {
    return Array.prototype.map.call(sections(), function (c) {
      return { type: c.dataset.type, id: c.dataset.id,
               copyFrom: c.dataset.copyFrom || null, unsaved: c.dataset.unsaved || null,
               unedited: c.dataset.unedited || null,
               settings: c.dataset.settings || "{}", changed: c.dataset.changed || "[]",
               label: (c.querySelector(".pb-sec-name").firstChild.textContent || "").trim() };
    });
  }
  function pushHistory() {
    if (restoring) return;
    var snap = snapshot();
    if (hi >= 0 && JSON.stringify(history[hi]) === JSON.stringify(snap)) return;  // no change
    history = history.slice(0, hi + 1);
    history.push(snap);
    hi = history.length - 1;
  }
  function restore(snap) {
    restoring = true;
    Array.prototype.slice.call(sections()).forEach(function (s) { s.remove(); });
    snap.forEach(function (d) {
      var el = makeSection({ type: d.type, id: d.id, label: d.label,
                             copyFrom: d.copyFrom || undefined, isNew: !!d.unsaved && !d.copyFrom,
                             unedited: !!d.unedited,
                             settings: JSON.parse(d.settings || "{}"), changed: JSON.parse(d.changed || "[]") });
      canvas.appendChild(el);
      wirePreview(el.querySelector(".pb-frame"));
    });
    dirtied = true;
    refresh();            // updates controls + writes the hidden layout fields
    restoring = false;
  }
  function undo() { if (hi > 0) { hi--; restore(history[hi]); showToast("Undo", true); } }
  function redo() { if (hi < history.length - 1) { hi++; restore(history[hi]); showToast("Redo", true); } }
  document.addEventListener("keydown", function (e) {
    if (!(e.ctrlKey || e.metaKey)) return;
    var tag = (document.activeElement && document.activeElement.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA") return;   // leave text undo alone
    var k = (e.key || "").toLowerCase();
    if (k === "z") { e.preventDefault(); if (e.shiftKey) redo(); else undo(); }
    else if (k === "y") { e.preventDefault(); redo(); }
  });

  /* ---------- section actions (toolbar, keyboard, right-click menu) ---------- */
  // Copy & paste work within this page: the pasted section copies the source's saved
  // content (like Duplicate) plus any settings changed but not yet saved. Copy has a
  // toolbar button; paste is in the right-click menu (above / below) and Ctrl/⌘+V.
  var CLIP_KEY = "prblm-builder:clip:" + CFG.context;
  var clip = null;
  try { clip = JSON.parse(window.sessionStorage.getItem(CLIP_KEY) || "null"); } catch (e) {}
  function setClip(c) {
    clip = c;
    document.body.classList.toggle("pb-has-clip", !!c);
    try { window.sessionStorage.setItem(CLIP_KEY, JSON.stringify(c)); } catch (e) {}
  }
  setClip(clip);
  function copySection(sec) {
    var st = sectionState(sec);
    st.copyFrom = sec.dataset.copyFrom || sec.dataset.id;
    setClip(st);
    showToast("Copied “" + st.label + "” — right-click a section (or press Ctrl/⌘+V) to paste it", true);
  }
  function pasteSection(ref, where) {
    if (!clip) return null;
    var el = makeSection({ type: clip.type, label: clip.label, id: uuid(), copyFrom: clip.copyFrom,
                           unedited: clip.unedited, settings: clip.settings, changed: clip.changed });
    if (!ref) canvas.appendChild(el);
    else if (where === "above") ref.parentNode.insertBefore(el, ref);
    else ref.parentNode.insertBefore(el, ref.nextElementSibling);
    wirePreview(el.querySelector(".pb-frame")); select(el);
    return el;
  }
  function act(sec, name, btn) {
    if (name === "settings") { openSettings(sec, btn || sec.querySelector('[data-act="settings"]')); return; }
    if (name === "copy") { copySection(sec); return; }
    if (name === "up" && sec.previousElementSibling && sec.previousElementSibling.classList.contains("pb-sec"))
      sec.parentNode.insertBefore(sec, sec.previousElementSibling);
    else if (name === "down" && sec.nextElementSibling) sec.parentNode.insertBefore(sec.nextElementSibling, sec);
    else if (name === "del") { closeSettings(); sec.remove(); }
    else if (name === "dup") {
      var copy = makeSection({ type: sec.dataset.type, label: sec.querySelector(".pb-sec-name").firstChild.textContent,
        id: uuid(), copyFrom: sec.dataset.copyFrom || sec.dataset.id, unedited: !!sec.dataset.unedited,
        settings: JSON.parse(sec.dataset.settings || "{}"), changed: JSON.parse(sec.dataset.changed || "[]") });
      sec.parentNode.insertBefore(copy, sec.nextElementSibling);
      wirePreview(copy.querySelector(".pb-frame")); select(copy);
    }
    else if (name === "paste" || name === "paste-below") { if (!pasteSection(sec, "below")) return; }
    else if (name === "paste-above") { if (!pasteSection(sec, "above")) return; }
    else return;
    dirtied = true;   // a real layout change → page is now unsaved
    refresh();
    pushHistory();
  }

  canvas.addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-act]");
    if (btn) { act(btn.closest(".pb-sec"), btn.dataset.act, btn); return; }
    select(e.target.closest(".pb-sec"));  // click a section (or empty) to (de)select
  });

  // Ctrl/⌘+C / Ctrl/⌘+V on the selected section (not while typing or selecting text).
  document.addEventListener("keydown", function (e) {
    if (!(e.ctrlKey || e.metaKey) || e.shiftKey || e.altKey) return;
    var tag = (document.activeElement && document.activeElement.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    var k = (e.key || "").toLowerCase(), sel = canvas.querySelector(".pb-sec.pb-selected");
    if (k === "c" && sel && !String(window.getSelection() || "")) { e.preventDefault(); act(sel, "copy"); }
    else if (k === "v" && clip) {
      e.preventDefault();
      if (sel) act(sel, "paste-below");
      else { pasteSection(null); dirtied = true; refresh(); pushHistory(); }
    }
  });

  // Right-click menu on a section.
  var menu = null;
  function closeMenu() { if (menu) { menu.remove(); menu = null; } }
  canvas.addEventListener("contextmenu", function (e) {
    var sec = e.target.closest(".pb-sec");
    if (!sec) return;
    e.preventDefault();
    closeMenu(); closeSettings(); select(sec);
    var items = [["copy", "Copy"], ["paste-above", "Paste above", !clip], ["paste-below", "Paste below", !clip],
                 null, ["dup", "Duplicate"]];
    if (SCHEMA[sec.dataset.type]) items.push(["settings", "Settings…"]);
    items.push(null, ["up", "Move up", !sec.previousElementSibling || !sec.previousElementSibling.classList.contains("pb-sec")],
               ["down", "Move down", !sec.nextElementSibling || !sec.nextElementSibling.classList.contains("pb-sec")],
               null, ["del", "Delete", false, true]);
    menu = document.createElement("div");
    menu.className = "pb-menu"; menu.setAttribute("role", "menu");
    items.forEach(function (it) {
      if (!it) { var hr = document.createElement("div"); hr.className = "pb-menu-sep"; menu.appendChild(hr); return; }
      var b = document.createElement("button"); b.type = "button"; b.setAttribute("role", "menuitem");
      b.textContent = it[1]; b.disabled = !!it[2]; if (it[3]) b.className = "pb-menu-danger";
      b.addEventListener("click", function () { closeMenu(); act(sec, it[0]); });
      menu.appendChild(b);
    });
    document.body.appendChild(menu);
    menu.style.left = Math.min(e.clientX, window.innerWidth - menu.offsetWidth - 6) + "px";
    menu.style.top = Math.min(e.clientY, window.innerHeight - menu.offsetHeight - 6) + "px";
    var first = menu.querySelector("button:not([disabled])"); if (first) first.focus();
  });
  document.addEventListener("mousedown", function (e) { if (menu && !menu.contains(e.target)) closeMenu(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenu(); });
  window.addEventListener("scroll", closeMenu, true);

  /* ---------- tooltips for the section toolbar buttons ---------- */
  // One tooltip element, shown on hover or keyboard focus of any [data-tip] button and
  // placed with position:fixed so short sections can't clip it.
  var tip = document.createElement("div");
  tip.className = "pb-tip"; tip.setAttribute("role", "tooltip"); tip.hidden = true;
  document.body.appendChild(tip);
  var tipFor = null;
  function showTip(el) {
    tipFor = el;
    tip.textContent = el.getAttribute("data-tip");
    tip.hidden = false;
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var top = r.bottom + 8, below = true;
    if (top + h > window.innerHeight - 4) { top = r.top - h - 8; below = false; }
    tip.classList.toggle("pb-tip-above", !below);
    tip.style.top = top + "px";
    tip.style.left = Math.max(6, Math.min(window.innerWidth - w - 6, r.left + r.width / 2 - w / 2)) + "px";
  }
  function hideTip() { tip.hidden = true; tipFor = null; }
  document.addEventListener("mouseover", function (e) {
    var el = e.target.closest && e.target.closest("[data-tip]");
    if (el && el !== tipFor) showTip(el); else if (!el && tipFor) hideTip();
  });
  document.addEventListener("focusin", function (e) {
    var el = e.target.closest && e.target.closest("[data-tip]");
    if (el && el.matches(":focus-visible")) showTip(el);
  });
  document.addEventListener("focusout", hideTip);
  document.addEventListener("mousedown", hideTip);
  window.addEventListener("scroll", hideTip, true);

  /* ---------- sidebar tabs (Sections | Page) + page options ---------- */
  var tabBtns = Array.prototype.slice.call(document.querySelectorAll('.pb-tabs [role="tab"]'));
  function showTab(name) {
    tabBtns.forEach(function (b) {
      var on = b.dataset.tab === name;
      b.setAttribute("aria-selected", on ? "true" : "false"); b.tabIndex = on ? 0 : -1;
      document.getElementById(b.getAttribute("aria-controls")).hidden = !on;
    });
  }
  tabBtns.forEach(function (b, i) {
    b.addEventListener("click", function () { showTab(b.dataset.tab); });
    b.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var n = tabBtns[(i + (e.key === "ArrowRight" ? 1 : -1) + tabBtns.length) % tabBtns.length];
      n.focus(); showTab(n.dataset.tab);
    });
  });
  // The sidebar always opens on Sections; Page only when the editor clicks it.

  // Each "Page" option writes into real (hidden) fields of the page's edit form, so it
  // saves — and auto-saves — like any other field.
  function parentField(name) { var f = parentForm(); return f && f.querySelector('[name="' + name + '"]'); }
  function optionSet(o) { try { return JSON.parse(o.dataset.set || "{}"); } catch (e) { return {}; } }
  function refreshChrome(kind, value) {
    var box = document.querySelector('.pb-chrome[data-chrome="' + kind + '"]');
    if (!box) return;
    if (value === "none") { box.hidden = true; return; }
    var opts = {}; opts[kind] = value;
    box.hidden = false;
    box.querySelector(".pb-chrome-frame").src =
      box.dataset.chromeBase + "&options=" + encodeURIComponent(JSON.stringify(opts));
  }
  document.querySelectorAll(".pb-opt-select").forEach(function (sel) {
    var kind = sel.dataset.chrome;
    if (EMBED) {
      // Start from the edit form's current values (they may hold unsaved changes).
      var match = Array.prototype.find.call(sel.options, function (o) {
        var set = optionSet(o), keys = Object.keys(set).filter(function (k) { return set[k] !== ""; });
        return keys.length && keys.every(function (k) { var f = parentField(k); return f && String(f.value) === String(set[k]); });
      });
      if (match && match.value !== sel.value) { sel.value = match.value; if (kind) refreshChrome(kind, sel.value); }
    }
    sel.addEventListener("change", function () {
      var set = optionSet(sel.options[sel.selectedIndex]);
      Object.keys(set).forEach(function (k) {
        var f = parentField(k); if (!f) return;
        f.value = set[k];
        ["input", "change"].forEach(function (t) { try { f.dispatchEvent(new Event(t, { bubbles: true })); } catch (e) {} });
      });
      dirtied = true; syncLayout();
      if (kind) refreshChrome(kind, sel.value);
    });
  });

  /* ---------- ⚙ section settings popover ---------- */
  var pop = null, popBtn = null;
  function closeSettings() {
    if (!pop) return;
    pop.remove(); pop = null;
    if (popBtn) { popBtn.setAttribute("aria-expanded", "false"); popBtn.focus(); popBtn = null; }
  }
  function placeSettings() {
    if (!pop || !popBtn) return;
    var r = popBtn.getBoundingClientRect(), w = pop.offsetWidth;
    pop.style.top = Math.min(window.innerHeight - pop.offsetHeight - 8, r.bottom + 8) + "px";
    pop.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.right - w)) + "px";
  }
  function setSetting(sec, name, value) {
    var st = sectionState(sec);
    st.settings[name] = value;
    if (st.changed.indexOf(name) < 0) st.changed.push(name);
    sec.dataset.settings = JSON.stringify(st.settings);
    sec.dataset.changed = JSON.stringify(st.changed);
    dirtied = true; refresh(); pushHistory();
    var frame = sec.querySelector(".pb-frame");
    frame.src = previewSrc(sectionState(sec));   // live update on the canvas
    // Same field in the Content tab (sections already saved there): update it too.
    var input = contentInput(sec.dataset.id, name);
    if (input) writeContentInput(input, value);
  }

  // Called by the editor page when a settings field is changed in the Content tab.
  function applySetting(id, name, value) {
    var sec = canvas.querySelector('.pb-sec[data-id="' + id + '"]');
    var sch = sec && SCHEMA[sec.dataset.type];
    if (!sch || !sch.fields.some(function (f) { return f.name === name; })) return;
    var st = sectionState(sec);
    if (st.settings[name] === value) return;
    st.settings[name] = value;
    if (st.changed.indexOf(name) < 0) st.changed.push(name);
    sec.dataset.settings = JSON.stringify(st.settings);
    sec.dataset.changed = JSON.stringify(st.changed);
    sec.querySelector(".pb-frame").src = previewSrc(sectionState(sec));
    if (pop && popBtn && popBtn.closest(".pb-sec") === sec) closeSettings();   // reopen shows the new value
    dirtied = true; refresh();
  }
  // Reload every preview (after Content-tab edits were auto-saved to the draft).
  function refreshPreviews() {
    document.querySelectorAll(".pb-frame, .pb-chrome-frame").forEach(function (f) {
      if (!f.getAttribute("src")) return;
      var src = f.getAttribute("src").replace(/([?&])_r=\d+/, "");
      f.src = src + (src.indexOf("?") < 0 ? "?" : "&") + "_r=" + Date.now();
    });
  }
  window.prblmBuilder = { applySetting: applySetting, refreshPreviews: refreshPreviews };
  function field(sec, f, value) {
    var row = document.createElement("div"); row.className = "pb-pop-field";
    var id = "pb-set-" + f.name;
    var label = '<label class="pb-pop-label" for="' + id + '">' + f.label + "</label>";
    if (f.kind === "choice" && f.swatches) {
      row.innerHTML = '<span class="pb-pop-label" id="' + id + '">' + f.label + '</span><div class="pb-swatches" role="radiogroup" aria-labelledby="' + id + '"></div>';
      var box = row.querySelector(".pb-swatches");
      f.choices.forEach(function (c) {
        var b = document.createElement("button"); b.type = "button"; b.className = "pb-swatch";
        b.setAttribute("role", "radio"); b.setAttribute("aria-checked", c[0] === value ? "true" : "false");
        // Colours come from the site's Theme (built-in blocks); otherwise names only.
        var color = f.colors && f.colors[c[0]];
        b.innerHTML = (color ? '<span class="pb-swatch-chip" style="background:' + color + '"></span>' : '') +
                      '<span>' + c[1] + "</span>";
        b.addEventListener("click", function () {
          box.querySelectorAll(".pb-swatch").forEach(function (x) { x.setAttribute("aria-checked", x === b ? "true" : "false"); });
          setSetting(sec, f.name, c[0]);
        });
        box.appendChild(b);
      });
    } else if (f.kind === "choice") {
      row.innerHTML = label + '<select id="' + id + '"></select>';
      var sel = row.querySelector("select");
      if (!f.required) sel.add(new Option("—", ""));
      f.choices.forEach(function (c) { sel.add(new Option(c[1], c[0], false, c[0] === value)); });
      sel.addEventListener("change", function () { setSetting(sec, f.name, sel.value); });
    } else if (f.kind === "boolean") {
      row.innerHTML = '<label class="pb-pop-check"><input type="checkbox" id="' + id + '"> ' + f.label + "</label>";
      var cb = row.querySelector("input"); cb.checked = !!value;
      cb.addEventListener("change", function () { setSetting(sec, f.name, cb.checked); });
    } else {
      var num = f.kind === "number";
      row.innerHTML = label + '<input type="' + (num ? "number" : "text") + '" id="' + id + '">' +
                      '<p class="pb-pop-error" role="alert" hidden></p>';
      var inp = row.querySelector("input"), err = row.querySelector(".pb-pop-error");
      inp.value = value == null ? "" : value;
      if (f.max_length) inp.maxLength = f.max_length;
      if (num) {
        if (f.min != null) inp.min = f.min;
        if (f.max != null) inp.max = f.max;
        inp.step = f.step || "any";
      }
      // Checked with the block's own rules as you type; only a valid value is applied.
      var lastOk = true, tm = null, seq = 0;
      function check(then) {
        var v = inp.value.trim(), mine = ++seq;
        if (!CFG.check) { lastOk = true; if (then) then(true); return; }
        var url = CFG.check + "?" + CFG.context + "&block=" + encodeURIComponent(sec.dataset.type) +
                  "&name=" + encodeURIComponent(f.name) + "&value=" + encodeURIComponent(v);
        fetch(url, { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (d) {
          if (mine !== seq) return;
          lastOk = !!d.ok;
          err.textContent = d.ok ? "" : (d.error || "Enter a valid value.");
          err.hidden = !!d.ok; inp.setAttribute("aria-invalid", d.ok ? "false" : "true");
          if (then) then(lastOk);
        }).catch(function () { if (then) then(true); });
      }
      inp.addEventListener("input", function () { clearTimeout(tm); tm = setTimeout(function () { check(); }, 300); });
      inp.addEventListener("change", function () {
        clearTimeout(tm);
        check(function (ok) { if (ok) setSetting(sec, f.name, inp.value.trim()); });
      });
      inp.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); inp.blur(); } });
    }
    if (f.help) {
      var h = document.createElement("p"); h.className = "pb-pop-help"; h.textContent = f.help; row.appendChild(h);
    }
    return row;
  }
  function openSettings(sec, btn) {
    var again = pop && popBtn === btn;
    closeSettings();
    if (again) return;   // clicking ⚙ again closes it
    var sch = SCHEMA[sec.dataset.type]; if (!sch) return;
    var values = sectionState(sec).settings;
    pop = document.createElement("div");
    pop.className = "pb-pop"; pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "Section settings");
    pop.innerHTML = '<div class="pb-pop-head"><strong>Section settings</strong>' +
      '<button type="button" class="pb-pop-close" aria-label="Close">&#10005;</button></div>';
    sch.fields.forEach(function (f) { pop.appendChild(field(sec, f, values[f.name])); });
    var note = document.createElement("p"); note.className = "pb-pop-note";
    note.textContent = "Saved with the page (Save draft / Publish).";
    pop.appendChild(note);
    pop.querySelector(".pb-pop-close").addEventListener("click", closeSettings);
    document.body.appendChild(pop);
    popBtn = btn; btn.setAttribute("aria-expanded", "true");
    placeSettings();
    var first = pop.querySelector("button.pb-swatch, select, input"); if (first) first.focus();
  }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeSettings(); });
  document.addEventListener("mousedown", function (e) {
    if (pop && !pop.contains(e.target) && !e.target.closest('[data-act="settings"]')) closeSettings();
  });
  window.addEventListener("scroll", placeSettings, true);
  window.addEventListener("resize", placeSettings);

  /* ---------- drag/drop ---------- */
  var dragSig = null;
  new Sortable(canvas, {
    group: { name: "pb", put: true }, animation: 150, handle: ".pb-grab", draggable: ".pb-sec",
    forceFallback: true, fallbackOnBody: true,
    onStart: function () { canvas.classList.add("pb-drop"); dragSig = structureSig(collect()); },
    onEnd: function () {
      canvas.classList.remove("pb-drop");
      // Dropped back where it was: not a change (no banner, no auto-saved draft).
      if (structureSig(collect()) === dragSig) return;
      dirtied = true; refresh(); pushHistory();
    },
    onAdd: function (evt) {
      var el = evt.item;
      dirtied = true;
      if (el.classList && el.classList.contains("pb-pitem")) {
        var sec = makeSection({ type: el.dataset.type, label: el.dataset.label, id: uuid(), isNew: true });
        canvas.insertBefore(sec, el); el.parentNode.removeChild(el);
        wirePreview(sec.querySelector(".pb-frame")); select(sec);
      }
      refresh();
      pushHistory();
    },
    onSort: refresh,
  });
  document.querySelectorAll(".pb-pgroup-items").forEach(function (g) {
    new Sortable(g, { group: { name: "pb", pull: "clone", put: false }, sort: false,
      draggable: ".pb-pitem", forceFallback: true, fallbackOnBody: true });
  });

  /* click a palette item to append it */
  document.getElementById("pb-palette-list").addEventListener("click", function (e) {
    var item = e.target.closest(".pb-pitem"); if (!item) return;
    dirtied = true;
    var sec = addSection({ type: item.dataset.type, label: item.dataset.label, id: uuid(), isNew: true });
    select(sec); sec.scrollIntoView({ behavior: "smooth", block: "nearest" });
    pushHistory();
  });

  /* ---------- palette thumbnails: lazy-load the scaled desktop renders ---------- */
  var tio = ("IntersectionObserver" in window) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { var f = e.target; if (!f.src && f.dataset.src) f.src = f.dataset.src; tio.unobserve(f); } });
  }, { root: document.querySelector(".pb-palette"), rootMargin: "300px 0px" }) : null;
  function fitThumb(f) {
    try {
      var thumb = f.closest(".pb-thumb"), doc = f.contentDocument;
      if (!thumb || !doc || !doc.body) return;
      f.style.width = CANVAS_W + "px";
      if ((parseFloat(f.style.height) || 0) < CANVAS_H) f.style.height = CANVAS_H + "px";
      var m = measureFrame(f, false);
      if (m.top + m.height > parseFloat(f.style.height)) f.style.height = (m.top + m.height) + "px";
      var scale = thumb.clientWidth / CANVAS_W;
      f.style.transform = "scale(" + scale + ")" + (m.top ? " translateY(" + (-m.top) + "px)" : "");
      // height fits the section's real (scaled) height — narrow sections get short
      // thumbnails — capped so a very tall section can't dominate the list.
      thumb.style.height = Math.min(240, Math.max(44, Math.round(m.height * scale))) + "px";
    } catch (e) {}
  }
  document.querySelectorAll(".pb-thumb-frame").forEach(function (f) {
    f.addEventListener("load", function () { fitThumb(f); setTimeout(function () { fitThumb(f); }, 400); });
    if (tio) tio.observe(f); else f.src = f.dataset.src;
  });

  /* ---------- site header/footer chrome (fixed top/bottom of the page) ---------- */
  document.querySelectorAll(".pb-chrome-frame").forEach(function (f) {
    f.style.height = CANVAS_H + "px";
    f.addEventListener("load", function () { f._pbGrow = 0; settle(f, fitChrome); watchFrame(f, fitChrome); });
    f.src = f.dataset.src;
  });

  /* ---------- palette search ---------- */
  var search = document.getElementById("pb-search");
  var pills = document.querySelector("[data-kind-filter]"), kindShown = "all";
  function filterPalette() {
    var q = search ? search.value.trim().toLowerCase() : "";
    document.body.classList.toggle("pb-searching", !!q);   // searching shows folded groups too
    // A kind pill narrows the list; a search always looks through every kind.
    document.querySelectorAll("[data-kind-block]").forEach(function (b) {
      b.style.display = (q || kindShown === "all" || b.dataset.kindBlock === kindShown) ? "" : "none";
    });
    if (pills) pills.classList.toggle("pb-kinds-search", !!q);
    document.querySelectorAll(".pb-pitem").forEach(function (it) {
      it.style.display = (!q || it.dataset.search.indexOf(q) !== -1) ? "" : "none";
    });
    document.querySelectorAll(".pb-pgroup").forEach(function (g) {
      g.style.display = g.querySelectorAll('.pb-pitem:not([style*="display: none"])').length ? "" : "none";
    });
    // Thumbnails that just became visible load now.
    document.querySelectorAll(".pb-thumb-frame").forEach(function (f) {
      if (!f.src && f.dataset.src && f.offsetParent !== null && !tio) f.src = f.dataset.src;
    });
  }
  if (search) search.addEventListener("input", filterPalette);
  if (pills) pills.querySelectorAll("button").forEach(function (b) {
    b.addEventListener("click", function () {
      kindShown = b.dataset.kind;
      pills.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      filterPalette();
      var pal = document.querySelector(".pb-palette"); if (pal) pal.scrollTop = 0;
    });
  });

  /* ---------- responsive preview toggle ---------- */
  var deviceBtns = document.querySelectorAll(".pb-devices button");
  deviceBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      deviceBtns.forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active");
      (canvas.closest(".pb-page") || canvas).setAttribute("data-device", b.dataset.device);
      setTimeout(function () {
        canvas.querySelectorAll(".pb-frame").forEach(function (f) { settle(f, fit); });
        document.querySelectorAll(".pb-chrome-frame").forEach(function (f) { settle(f, fitChrome); });
      }, 240);
    });
  });

  /* ---------- save ---------- */
  function collect() {
    return Array.prototype.map.call(sections(), function (c) {
      var s = { type: c.dataset.type, id: c.dataset.id };
      if (c.dataset.copyFrom) s.copy_from = c.dataset.copyFrom;
      else if (c.dataset.unsaved) s.new = true;   // brand-new → seed with demo content
      var ch = changedSettings(sectionState(c));
      if (Object.keys(ch).length) s.settings = ch;  // ⚙ settings changed in the Layout tab
      return s;
    });
  }
  function showToast(msg, ok) {
    toast.textContent = msg; toast.className = "pb-toast pb-show " + (ok ? "pb-ok" : "pb-err");
    setTimeout(function () { toast.className = "pb-toast"; }, 3200);
  }
  /* ---------- embed: expand toggle + keep the scale right on resize ---------- */
  if (EMBED) {
    var expandBtn = document.createElement("button");
    expandBtn.type = "button";
    expandBtn.className = "pb-expand";
    expandBtn.title = "Hide the section list for a wider preview";
    var ICON_EXPAND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>';
    var ICON_COLLAPSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg>';
    function paintExpand() {
      var on = document.body.classList.contains("pb-expanded");
      expandBtn.innerHTML = (on ? ICON_COLLAPSE : ICON_EXPAND) + "<span>" + (on ? "Show list" : "Wider preview") + "</span>";
    }
    expandBtn.addEventListener("click", function () {
      document.body.classList.toggle("pb-expanded");
      paintExpand();
      setTimeout(refitAll, 60);
    });
    paintExpand();
    document.body.appendChild(expandBtn);

    var rt;
    window.addEventListener("resize", function () {
      clearTimeout(rt); rt = setTimeout(refitAll, 120);
    });

    // Draggable divider: widen/narrow the palette so the canvas can be bigger.
    var divider = document.querySelector(".pb-divider");
    if (divider) {
      var dragging = false;
      divider.addEventListener("pointerdown", function (e) {
        dragging = true; document.body.classList.add("pb-dragging");
        try { divider.setPointerCapture(e.pointerId); } catch (x) {}
        e.preventDefault();
      });
      window.addEventListener("pointermove", function (e) {
        if (!dragging) return;
        var w = Math.max(160, Math.min(560, e.clientX - wrap.getBoundingClientRect().left));
        wrap.style.setProperty("--pb-pal", w + "px");
      });
      window.addEventListener("pointerup", function () {
        if (!dragging) return;
        dragging = false; document.body.classList.remove("pb-dragging");
        setTimeout(refitAll, 40);
      });
    }
  }

  /* ---------- initial render ---------- */
  (function init() {
    var node = document.getElementById("pb-sections"); var data = [];
    try { data = JSON.parse(node.textContent); } catch (e) {}
    INITIAL_IDS = data.map(function (s) { return s.id; });
    // After a failed save the editor page hands back the submitted arrangement — restore
    // it (new sections included) instead of starting from the stored page.
    var restore = null;
    if (EMBED) {
      try { var rn = window.parent.document.getElementById("pb-restore"); if (rn) restore = JSON.parse(rn.textContent); } catch (e) {}
    }
    if (restore && restore.layout) {
      try {
        var stored = {}; data.forEach(function (s) { stored[s.id] = s; });
        var layout = JSON.parse(restore.layout);
        INITIAL_IDS = JSON.parse(restore.initial || "[]");
        data = layout.map(function (it) {
          var pal = document.querySelector('.pb-pitem[data-type="' + it.type + '"]');
          var known = stored[it.id] || {};
          var base = known.settings || (SCHEMA[it.type] && SCHEMA[it.type].defaults) || {};
          return { type: it.type, id: it.id, label: known.label || (pal && pal.dataset.label) || it.type,
                   isNew: !!it["new"] && !it.copy_from, copyFrom: it.copy_from || undefined,
                   unedited: !!(it["new"] || it.copy_from || known.unedited),
                   settings: Object.assign({}, base, it.settings || {}),
                   changed: Object.keys(it.settings || {}) };
        });
        dirtied = true;
      } catch (e) {}
    }
    data.forEach(function (s) { addSection(s); });
    refresh();   // seeds the parent form's hidden fields with the current order (no-op save)
    pushHistory();   // baseline state for undo
  })();
})();
