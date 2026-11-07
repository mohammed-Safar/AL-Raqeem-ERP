/* ALRAQEEM — Arabic / English switch, placed after the theme-colour button.
   Saves the language on the user (raqim_sales.api.set_language) and reloads.
   The button shows the language you will switch TO: "EN" in Arabic, "ع" in English.
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const lang = () => ((window.frappe && frappe.boot && frappe.boot.lang) || "en").split("-")[0];

	function make_button() {
		const ar = lang() === "ar";
		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "btn-reset rq-lang-btn";
		btn.innerHTML = `<span class="rq-lang-label" lang="${ar ? "en" : "ar"}">${ar ? "EN" : "ع"}</span>`;
		const tip = ar ? "Switch to English" : "التبديل إلى العربية";
		btn.setAttribute("title", tip);
		btn.setAttribute("aria-label", tip);
		btn.addEventListener("click", () => switch_to(ar ? "en" : "ar"));
		return btn;
	}

	let busy = false;
	function switch_to(next) {
		if (busy) return;
		busy = true;
		document.querySelectorAll(".rq-lang-btn").forEach((b) => b.classList.add("rq-lang-busy"));
		frappe
			.xcall("raqim_sales.api.set_language", { lang: next })
			.then(() => {
				try {
					localStorage.removeItem("page_info"); // cached page layouts are per language
				} catch (e) {}
				window.location.reload();
			})
			.catch(() => {
				busy = false;
				document.querySelectorAll(".rq-lang-btn").forEach((b) => b.classList.remove("rq-lang-busy"));
			});
	}

	// after the colour button (or the light/dark button if that one is removed)
	function inject() {
		document
			.querySelectorAll(".page-head .standard-items-section:not(.rq-has-lang)")
			.forEach((section) => {
				const anchor =
					section.querySelector(":scope > .rq-accent-btn") ||
					section.querySelector(":scope > .rq-theme-toggle");
				if (!anchor) return; // wait for the other buttons
				section.classList.add("rq-has-lang");
				anchor.after(make_button());
			});
	}
	let queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			inject();
		});
	}
	function start() {
		inject();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
