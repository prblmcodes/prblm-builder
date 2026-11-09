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
  function syncLayout() {
    if (!EMBED) return;
    var form = parentForm(); if (!form) return;
    try {
      setHidden(form, "_pb_layout", JSON.stringify(collect()));
      setHidden(form, "_pb_initial", JSON.stringify(INITIAL_IDS));
    } catch (e) {}
    // Tell the editor page (it shows a "Save to edit these sections" banner).
    if (dirtied) {
      try { window.parent.document.dispatchEvent(new CustomEvent("prblm-builder:dirty")); } catch (e) {}
    }
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
    edit: svgIcon('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>'),
    grab: svgIcon('<circle cx="9" cy="6" r="1.2"/><circle cx="15" cy="6" r="1.2"/><circle cx="9" cy="12" r="1.2"/>' +
                  '<circle cx="15" cy="12" r="1.2"/><circle cx="9" cy="18" r="1.2"/><circle cx="15" cy="18" r="1.2"/>'),
    up: svgIcon('<path d="M6 15l6-6 6 6"/>'),
    down: svgIcon('<path d="M6 9l6 6 6-6"/>'),
    settings: svgIcon('<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/>' +
                      '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>'),
    copy: svgIcon('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
    paste: svgIcon('<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1M12 10v7M9 14l3 3 3-3"/>'),
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
          // In the Layout tab, content is edited in the Content tab — so no pencil.
          (EMBED ? '' : '<button data-act="edit" aria-label="Edit content" data-tip="Edit this section\'s words and images">' + ICON.edit + '</button>') +
          '<button class="pb-grab" data-act="grab" aria-label="Drag to move" data-tip="Drag to move this section">' + ICON.grab + '</button>' +
          '<button data-act="up" aria-label="Move up" data-tip="Move up">' + ICON.up + '</button>' +
          '<button data-act="down" aria-label="Move down" data-tip="Move down">' + ICON.down + '</button>' +
          (sch ? '<button data-act="settings" aria-haspopup="dialog" aria-label="Section settings" data-tip="Settings (background, anchor ID…)">' + ICON.settings + '</button>' : '') +
          '<button data-act="copy" aria-label="Copy section" data-tip="Copy section (Ctrl/⌘+C)">' + ICON.copy + '</button>' +
          '<button data-act="paste" class="pb-paste" aria-label="Paste below" data-tip="Paste the copied section below (Ctrl/⌘+V)">' + ICON.paste + '</button>' +
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
  // content (like Duplicate) plus any settings changed but not yet saved.
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
    showToast("Copied “" + st.label + "” — paste it anywhere on this page", true);
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
    if (name === "edit") {
      if (sec.dataset.unsaved) showToast("Save draft first to edit this new section's content", false);
      else window.open(CFG.edit + "#block-" + sec.dataset.id, "_blank");
      return;
    }
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
    try { window.sessionStorage.setItem("prblm-builder:tab", name); } catch (e) {}
  }
  tabBtns.forEach(function (b, i) {
    b.addEventListener("click", function () { showTab(b.dataset.tab); });
    b.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var n = tabBtns[(i + (e.key === "ArrowRight" ? 1 : -1) + tabBtns.length) % tabBtns.length];
      n.focus(); showTab(n.dataset.tab);
    });
  });
  if (tabBtns.length) {
    try { if (window.sessionStorage.getItem("prblm-builder:tab") === "page") showTab("page"); } catch (e) {}
  }

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
  var SWATCH = { light: "#ffffff", muted: "#f3f4f6", dark: "#0f172a", brand: "#2563eb" };
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
  }
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
        b.innerHTML = '<span class="pb-swatch-chip" style="background:' + (SWATCH[c[0]] || "#ccc") + '"></span><span>' + c[1] + "</span>";
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
      row.innerHTML = label + '<input type="text" id="' + id + '">';
      var inp = row.querySelector("input"); inp.value = value == null ? "" : value;
      if (f.max_length) inp.maxLength = f.max_length;
      inp.addEventListener("change", function () { setSetting(sec, f.name, inp.value.trim()); });
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
      if (!thumb || !doc || !doc.documentElement) return;
      f.style.width = CANVAS_W + "px";
      var h = doc.documentElement.scrollHeight;
      f.style.height = h + "px";
      var scale = thumb.clientWidth / CANVAS_W;
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
    document.body.classList.toggle("pb-searching", !!q);   // searching shows folded groups too
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
      var ch = changedSettings(sectionState(c));
      if (Object.keys(ch).length) s.settings = ch;  // ⚙ settings changed in the Layout tab
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
