/* prblm-builder — built-in LinkBlock: show only the field for the chosen link type.
   Uses Wagtail's documented StructBlockDefinition extension point. Without this script
   every field is simply shown, so nothing breaks. */
(function () {
  "use strict";
  var FIELDS = { page: "page", url: "url", anchor: "anchor", document: "document", email: "email", phone: "phone" };
  var Base = window.wagtailStreamField && window.wagtailStreamField.blocks &&
             window.wagtailStreamField.blocks.StructBlockDefinition;
  if (!Base || !window.telepath) return;

  // The whole child block (label + help + input) is the element marked with its name.
  function wrapper(prefix, name) {
    var el = document.getElementById(prefix + "-" + name);
    if (!el) return null;
    return el.closest('[data-contentpath="' + name + '"]') || el.closest("[data-field-wrapper]");
  }

  class LinkBlockDefinition extends Base {
    render(placeholder, prefix, initialState, initialError) {
      var block = super.render(placeholder, prefix, initialState, initialError);
      var select = document.getElementById(prefix + "-link_type");
      if (!select) return block;
      // Links saved before 0.5 have no type: show the one that matches their content.
      if (!select.value) {
        var page = document.getElementById(prefix + "-page");
        select.value = page && page.value ? "page" : "url";
      }
      function update() {
        Object.keys(FIELDS).forEach(function (type) {
          var w = wrapper(prefix, FIELDS[type]);
          if (w) w.hidden = type !== select.value;
        });
      }
      select.addEventListener("change", update);
      update();
      return block;
    }
  }
  window.telepath.register("prblm_builder.blocks.LinkBlock", LinkBlockDefinition);
})();
