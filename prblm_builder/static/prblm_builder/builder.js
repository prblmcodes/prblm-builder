/* prblm-builder — one-page drag-and-drop canvas (vanilla + SortableJS). */
(function () {
  "use strict";
  var wrap = document.querySelector(".pb-wrap");
  if (!wrap) return;
  var CFG = {
    preview: wrap.dataset.previewUrl, save: wrap.dataset.saveUrl,
    context: wrap.dataset.context, csrf: wrap.dataset.csrf, edit: wrap.dataset.editUrl,
  };
  var canvas = document.getElementById("pb-canvas");   // the .pb-page
  var empty = document.getElementById("pb-empty");
  var toast = document.getElementById("pb-toast");

  // Embedded in the page editor's "Layout" tab (iframe, same origin). There the
  // builder has no Save of its own: it writes the arrangement into hidden inputs
  // on the parent edit form, so Wagtail's own Save draft / Publish saves it.
  var EMBED = document.body.classList.contains("pb-embed");
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
  function syncLayout() {
    if (!EMBED) return;
    var form = parentForm(); if (!form) return;
    try {
      setHidden(form, "_pb_layout", JSON.stringify(collect()));
      setHidden(form, "_pb_initial", JSON.stringify(INITIAL_IDS));
    } catch (e) {}
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
  var CANVAS_W = 1280;
  function scaleFit(frame, isChrome) {
    try {
      var host = frame.closest(".pb-sec") || frame.closest(".pb-chrome");
      var d = frame.contentDocument;
      if (!host || !d || !d.body) return;
      var avail = host.clientWidth || CANVAS_W;
      var s = avail / CANVAS_W;
      var el = d.body.firstElementChild;
      // For a section use body.scrollHeight (the real content height) — documentElement
      // .scrollHeight can be inflated by decorative/absolute elements overflowing <html>,
      // which left empty space at the bottom of the section. Chrome keeps measuring its
      // one element (the header/footer) to avoid its hidden mobile menu inflating things.
      var h = isChrome ? ((el && el.offsetHeight) || d.documentElement.scrollHeight)
                       : (d.body.scrollHeight || d.documentElement.scrollHeight);
      frame.style.width = CANVAS_W + "px";
      // Give the iframe its full content height BEFORE scaling — otherwise it keeps the
      // default 150px and clips everything below that (only the top of the section shows).
      frame.style.height = h + "px";
      frame.style.transform = "scale(" + s + ")";
      host.style.height = Math.round(h * s) + "px";
    } catch (e) {}
  }
  function fit(frame) {
    if (EMBED) return scaleFit(frame, false);
    try {
      var d = frame.contentDocument;
      if (!d || !d.documentElement) return;
      frame.style.height = "0px";
      frame.style.height = d.documentElement.scrollHeight + "px";
    } catch (e) {}
  }
  function refitAll() {
    canvas.querySelectorAll(".pb-frame").forEach(function (f) { fit(f); });
    document.querySelectorAll(".pb-chrome-frame").forEach(function (f) { fitChrome(f); });
  }
  var io = ("IntersectionObserver" in window) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { var f = e.target; if (!f.src && f.dataset.src) f.src = f.dataset.src; io.unobserve(f); } });
  }, { rootMargin: "600px 0px" }) : null;

  function wirePreview(frame) {
    frame.addEventListener("load", function () {
      var host = frame.closest(".pb-sec");
      fit(frame);
      if (host) host.classList.remove("pb-sec-loading");   // reveal the rendered section
      // Keep re-fitting until the measured height stabilises (fonts/late layout), then
      // stop — avoids a section stuck clipped from the top with the wrong height.
      var last = -1, stable = 0, n = 0;
      var iv = setInterval(function () {
        fit(frame);
        var h = host ? host.offsetHeight : 0;
        if (h === last) { if (++stable >= 2) clearInterval(iv); } else { stable = 0; last = h; }
        if (++n > 24) clearInterval(iv);   // ~6s hard cap
      }, 250);
      try {
        var b = frame.contentDocument && frame.contentDocument.body;
        if (b && window.ResizeObserver) new ResizeObserver(function () { fit(frame); }).observe(b);
      } catch (e) {}
    });
    if (io) io.observe(frame); else frame.src = frame.dataset.src;
  }

  /* ---------- sections ---------- */
  function previewSrc(s) {
    var q = CFG.context + "&block=" + encodeURIComponent(s.type);
    if (s.copyFrom) return CFG.preview + "?" + q + "&section=" + encodeURIComponent(s.copyFrom);
    if (s.isNew) return CFG.preview + "?" + q + "&demo=1";
    return CFG.preview + "?" + q + "&section=" + encodeURIComponent(s.id);
  }

  function makeSection(s) {
    var el = document.createElement("section");
    el.className = "pb-sec pb-sec-loading"; el.dataset.id = s.id; el.dataset.type = s.type;
    if (s.copyFrom) el.dataset.copyFrom = s.copyFrom;
    el.innerHTML =
      '<iframe class="pb-frame" title="preview" scrolling="no"></iframe>' +
      '<div class="pb-sec-hit"></div>' +
      '<div class="pb-sec-bar">' +
        '<span class="pb-sec-name"></span>' +
        '<span class="pb-sec-ctrls">' +
          // In the Layout tab, content is edited in the Content tab — so no pencil.
          (EMBED ? '' : '<button data-act="edit" title="Edit this section\'s content">&#9998;</button>') +
          '<button class="pb-grab" data-act="grab" title="Drag to reorder">&#8942;&#8942;</button>' +
          '<button data-act="up" title="Move up">&#8593;</button>' +
          '<button data-act="down" title="Move down">&#8595;</button>' +
          '<button data-act="dup" title="Duplicate">&#10697;</button>' +
          '<button class="pb-del" data-act="del" title="Remove">&#10005;</button>' +
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
  }

  function select(sec) {
    sections().forEach(function (s) { s.classList.toggle("pb-selected", s === sec); });
  }

  /* ---------- undo / redo (Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z or Ctrl+Y) ---------- */
  var history = [], hi = -1, restoring = false;
  function snapshot() {
    return Array.prototype.map.call(sections(), function (c) {
      return { type: c.dataset.type, id: c.dataset.id,
               copyFrom: c.dataset.copyFrom || null, unsaved: c.dataset.unsaved || null,
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
                             copyFrom: d.copyFrom || undefined, isNew: !!d.unsaved && !d.copyFrom });
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

  /* ---------- controls + select (delegation) ---------- */
  canvas.addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-act]");
    if (btn) {
      var sec = btn.closest(".pb-sec"), act = btn.dataset.act;
      if (act !== "edit") dirtied = true;   // a real layout change → page is now unsaved
      if (act === "up" && sec.previousElementSibling && sec.previousElementSibling.classList.contains("pb-sec"))
        sec.parentNode.insertBefore(sec, sec.previousElementSibling);
      else if (act === "down" && sec.nextElementSibling) sec.parentNode.insertBefore(sec.nextElementSibling, sec);
      else if (act === "edit") {
        if (sec.dataset.unsaved) showToast("Save draft first to edit this new section's content", false);
        else window.open(CFG.edit + "#block-" + sec.dataset.id, "_blank");
        return;
      }
      else if (act === "del") { sec.remove(); }
      else if (act === "dup") {
        var copy = makeSection({ type: sec.dataset.type, label: sec.querySelector(".pb-sec-name").firstChild.textContent,
          id: uuid(), copyFrom: sec.dataset.copyFrom || sec.dataset.id });
        sec.parentNode.insertBefore(copy, sec.nextElementSibling);
        wirePreview(copy.querySelector(".pb-frame")); select(copy);
      }
      refresh();
      if (act !== "edit") pushHistory();
      return;
    }
    select(e.target.closest(".pb-sec"));  // click a section (or empty) to (de)select
  });

  /* ---------- drag/drop ---------- */
  new Sortable(canvas, {
    group: { name: "pb", put: true }, animation: 150, handle: ".pb-grab", draggable: ".pb-sec",
    forceFallback: true, fallbackOnBody: true,
    onStart: function () { canvas.classList.add("pb-drop"); },
    onEnd: function () { canvas.classList.remove("pb-drop"); dirtied = true; refresh(); pushHistory(); },
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
  document.querySelectorAll(".pb-pgroup").forEach(function (g) {
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
      if (!thumb || !doc || !doc.documentElement) return;
      var h = doc.documentElement.scrollHeight;
      f.style.height = h + "px";
      var scale = thumb.clientWidth / 1280;
      f.style.transform = "scale(" + scale + ")";
      // height fits the section's real (scaled) height — narrow sections get short
      // thumbnails — capped so a very tall section can't dominate the list.
      thumb.style.height = Math.min(240, Math.max(44, Math.round(h * scale))) + "px";
    } catch (e) {}
  }
  document.querySelectorAll(".pb-thumb-frame").forEach(function (f) {
    f.addEventListener("load", function () { fitThumb(f); setTimeout(function () { fitThumb(f); }, 400); });
    if (tio) tio.observe(f); else f.src = f.dataset.src;
  });

  /* ---------- site header/footer chrome (fixed top/bottom of the page) ---------- */
  function fitChrome(f) {
    if (EMBED) return scaleFit(f, true);
    try {
      var doc = f.contentDocument;
      if (!doc || !doc.body) return;
      // Measure the header/footer ELEMENT, not documentElement.scrollHeight — the
      // header's hidden mobile-menu panel is absolutely positioned and would
      // otherwise inflate the height, leaving a big gap below the header.
      var el = doc.body.firstElementChild;
      f.style.height = ((el && el.offsetHeight) || doc.documentElement.scrollHeight) + "px";
    } catch (e) {}
  }
  document.querySelectorAll(".pb-chrome-frame").forEach(function (f) {
    f.addEventListener("load", function () { fitChrome(f); setTimeout(function () { fitChrome(f); }, 400); });
    f.src = f.dataset.src;
  });

  /* ---------- palette search ---------- */
  var search = document.getElementById("pb-search");
  if (search) search.addEventListener("input", function () {
    var q = search.value.trim().toLowerCase();
    document.querySelectorAll(".pb-pitem").forEach(function (it) {
      it.style.display = (!q || it.dataset.search.indexOf(q) !== -1) ? "" : "none";
    });
    document.querySelectorAll(".pb-pgroup").forEach(function (g) {
      g.style.display = g.querySelectorAll('.pb-pitem:not([style*="display: none"])').length ? "" : "none";
    });
  });

  /* ---------- responsive preview toggle ---------- */
  var deviceBtns = document.querySelectorAll(".pb-devices button");
  deviceBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      deviceBtns.forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active");
      (canvas.closest(".pb-page") || canvas).setAttribute("data-device", b.dataset.device);
      setTimeout(function () { document.querySelectorAll(".pb-frame,.pb-chrome-frame").forEach(fit); }, 240);
    });
  });

  /* ---------- save ---------- */
  function collect() {
    return Array.prototype.map.call(sections(), function (c) {
      var s = { type: c.dataset.type, id: c.dataset.id };
      if (c.dataset.copyFrom) s.copy_from = c.dataset.copyFrom;
      else if (c.dataset.unsaved) s.new = true;   // brand-new → seed with demo content
      return s;
    });
  }
  function showToast(msg, ok) {
    toast.textContent = msg; toast.className = "pb-toast pb-show " + (ok ? "pb-ok" : "pb-err");
    setTimeout(function () { toast.className = "pb-toast"; }, 3200);
  }
  function doSave(publish, btn) {
    var label = btn.textContent; btn.disabled = true; btn.textContent = "Saving…";
    fetch(CFG.save, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": CFG.csrf },
      body: JSON.stringify({ sections: collect(), publish: publish }) })
      .then(function (r) { return r.json(); }).then(function (d) {
        btn.disabled = false; btn.textContent = label;
        if (d.ok) sections().forEach(function (s) { delete s.dataset.unsaved; });  // now saved → content editable
        showToast(d.ok ? (publish ? "Published ✓" : "Draft saved ✓") : ("Save failed: " + (d.error || "error")), !!d.ok);
      }).catch(function () { btn.disabled = false; btn.textContent = label; showToast("Save failed", false); });
  }
  // Standalone builder only — the toolbar (and its Save/Preview buttons) is absent
  // when embedded as the Layout tab, so guard every lookup.
  var saveBtn = document.getElementById("pb-save");
  var publishBtn = document.getElementById("pb-publish");
  if (saveBtn) saveBtn.addEventListener("click", function () { doSave(false, this); });
  if (publishBtn) publishBtn.addEventListener("click", function () { doSave(true, this); });

  /* ---------- preview mode (hide chrome) — standalone builder only ---------- */
  function setPreview(on) {
    document.body.classList.toggle("pb-preview-mode", on);
    setTimeout(function () { canvas.querySelectorAll(".pb-frame").forEach(fit); }, 60);
  }
  var previewBtn = document.getElementById("pb-preview");
  var exitPreviewBtn = document.getElementById("pb-exit-preview");
  if (previewBtn) previewBtn.addEventListener("click", function () { setPreview(true); });
  if (exitPreviewBtn) exitPreviewBtn.addEventListener("click", function () { setPreview(false); });
  if (previewBtn) document.addEventListener("keydown", function (e) { if (e.key === "Escape") setPreview(false); });

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
    data.forEach(function (s) { addSection(s); });
    refresh();   // seeds the parent form's hidden fields with the current order (no-op save)
    pushHistory();   // baseline state for undo
  })();
})();
