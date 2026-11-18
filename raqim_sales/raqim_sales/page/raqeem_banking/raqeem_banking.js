/* RAQEEM Banking: ERPNext's Banking screen (/banking) inside the desk, with the desk sidebar kept.
   The work is in public/js/raqeem_banking_desk.js. */
frappe.pages["raqeem-banking"].on_page_load = function (wrapper) {
	// the page header stays (title + the desk's display-settings button, like every page)
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Banking"), single_column: true, hide_sidebar: false });
	$(wrapper).addClass("rq-banking-page");
	window.rqBanking.mount(page);
};
frappe.pages["raqeem-banking"].on_page_show = function () { window.rqBanking.show(); };
