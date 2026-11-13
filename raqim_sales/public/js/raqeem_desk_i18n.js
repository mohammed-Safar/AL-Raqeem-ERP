/* RAQEEM: translate pop-up (dialog) titles in the desk.
 * Frappe translates every dialog's field labels, but sets the title exactly as the code wrote it,
 * so dialogs whose code forgot __() (e.g. HR "Add Leave Block Dates", "Update Property") showed
 * an English title. Passing the title through __() fixes all of them at once; an already
 * translated title has no entry and comes back unchanged.
 * ROLLBACK: delete this file's line in hooks.py app_include_js.
 */
(function () {
	if (!window.frappe || !frappe.ui || !frappe.ui.Dialog) return;
	var proto = frappe.ui.Dialog.prototype, orig = proto.set_title;
	if (!orig || orig.__rq) return;
	proto.set_title = function (t) {
		try {
			if (typeof t === "string" && /[A-Za-z]/.test(t) && t.indexOf("<") === -1) t = __(t);
		} catch (e) {}
		return orig.call(this, t);
	};
	proto.set_title.__rq = true;
})();
