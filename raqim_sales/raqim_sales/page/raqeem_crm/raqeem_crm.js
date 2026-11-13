/* RAQEEM CRM — Frappe CRM inside the desk (/desk/raqeem-crm/<CRM screen>).
   All the work is in public/js/raqeem_crm_desk.js (desk side) and
   public/js/raqeem_crm_embed.js (CRM side); this page only gives CRM its place.
   The desk sidebar stays, as on every other page (CRM has its own sidebar inside the frame). */

frappe.pages["raqeem-crm"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "CRM",
		single_column: true,
		hide_sidebar: false,
	});
	page.page_head.hide();
	$(wrapper).addClass("rq-crm-page");
	window.rqCrm.mount(page);
};

frappe.pages["raqeem-crm"].on_page_show = function () {
	window.rqCrm.show();
};
