/* ALRAQEEM — Raqeem duotone icons for the dock (app rail) and the sidebar.
   Nothing in the database or in Frappe/ERPNext files changes: only the
   drawing is replaced in the browser.

   ROLLBACK: set ENABLED to false below (or remove raqeem_icons.js,
   raqeem_icon_names.js and raqeem-sidebar.svg from hooks.py), clear the cache.

   How:
   - dock icons ("…-soft", module icons used only for apps/modules): the
     symbol itself (#icon-<name>) gets the Raqeem drawing, so every place that
     draws that module — dock, app grid — changes at once.
   - sidebar icons (plain Lucide names such as "house", "funnel" that Frappe
     also uses for buttons): only the sidebar's own <use> is pointed at
     #rq-<name>, so filter/search buttons elsewhere keep their usual icons. */
(function () {
	const ENABLED = true;
	if (!ENABLED) return;

	const SPRITE = "/assets/raqim_sales/icons/raqeem-sidebar.svg?r=3";
	const names = new Set(window.RAQEEM_ICON_NAMES || []);
	const soft = [...names].filter((n) => n.endsWith("-soft"));
	let replaced = 0;
	let swapped = 0;

	// 1) make sure the Raqeem sprite is in the page (Frappe's app_include_icons loads it
	//    too; this is the fallback if that did not happen)
	function ensure_sprite() {
		if (document.getElementById("rq-house") || document.getElementById("rq-sprite-loading")) return;
		const marker = document.createElement("i");
		marker.id = "rq-sprite-loading";
		marker.hidden = true;
		document.body.appendChild(marker);
		fetch(SPRITE, { credentials: "same-origin" })
			.then((r) => r.text())
			.then((svg) => {
				if (document.getElementById("rq-house")) return;
				const holder = document.createElement("div");
				holder.style.display = "none";
				holder.innerHTML = svg;
				document.body.appendChild(holder);
				run();
			})
			.catch((e) => console.warn("[raqeem icons] could not load sprite", e));
	}

	// 2) dock/module icons: copy the Raqeem drawing into the original symbol
	function replace_symbols() {
		soft.forEach((name) => {
			const orig = document.getElementById("icon-" + name);
			const mine = document.getElementById("rq-" + name);
			if (!orig || !mine || orig.getAttribute("data-rq") === "1") return;
			orig.innerHTML = mine.innerHTML;
			orig.setAttribute("viewBox", "0 0 24 24");
			orig.classList.remove("soft-icon");
			orig.classList.add("rq-symbol");
			orig.setAttribute("data-rq", "1");
			replaced++;
		});
	}

	// 3) labelled sidebar rows: point only their <use> at the Raqeem symbol
	function swap_sidebar() {
		document
			.querySelectorAll(".sidebar-item-icon[item-icon]:not([data-rq-icon])")
			.forEach((span) => {
				const name = span.getAttribute("item-icon");
				span.setAttribute("data-rq-icon", "0");
				if (!names.has(name)) return;
				const use = span.querySelector("use");
				if (!use) return;
				use.setAttribute("href", "#rq-" + name);
				span.setAttribute("data-rq-icon", "1");
				span.classList.add("rq-icon");
				swapped++;
			});
		// tag dock tiles so the CSS can tint the duotone fill
		document.querySelectorAll(".dock .dock-item-icon:not(.rq-icon)").forEach((span) => {
			const use = span.querySelector("use");
			const href = (use && use.getAttribute("href")) || "";
			if (names.has(href.replace("#icon-", ""))) span.classList.add("rq-icon");
		});
	}

	function run() {
		replace_symbols();
		swap_sidebar();
	}

	let queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			run();
		});
	}

	function start() {
		document.documentElement.classList.add("rq-icons-on");
		run();
		setTimeout(ensure_sprite, 2500);
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
		setTimeout(() => {
			console.info(
				`[raqeem icons] names: ${names.size}, sprite loaded: ${!!document.getElementById("rq-house")}, ` +
					`dock symbols replaced: ${replaced}/${soft.length}, sidebar rows swapped: ${swapped}`
			);
		}, 6000);
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
