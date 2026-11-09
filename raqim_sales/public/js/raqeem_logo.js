/* RAQEEM logo — the «R» mark (public/images/raqeem-logo.svg) in the theme colour.
   Loaded in the desk (app_include_js) and on website pages (web_include_js).
     • window.RAQEEM_LOGO_SVG(cls): inline SVG whose shape takes the current colour,
       so CSS can paint it with the theme accent (.rq-logo { color: var(--rq-accent) })
     • replaces every stock ERPNext / Frappe logo <img> (dock, sidebar header, apps
       screen, navbar, about dialog …) with that inline SVG, as Frappe draws them
     • browser-tab icon (favicon) redrawn in the theme colour; it follows light/dark and
       colour changes from the display-settings panel
   Static fallbacks (no JS yet): hooks.py website_context favicon + app_logo_url.
   ROLLBACK: remove raqeem_logo.js from app_include_js and web_include_js in hooks.py. */
(function () {
	const D = "M99.46,99.5Q98.67,95.89 97.26,92.39Q95.85,88.9 94.34,86.27Q92.83,83.63 89.94,80.17Q87.06,76.71 84.32,74.73Q81.58,72.75 78.51,71.52Q75.45,70.3 73.18,70.01Q70.91,69.72 56.06,69.68L41.2,69.65L41.13,99.71Q98.59,100.0 99.03,99.75L99.46,99.5Z M30.46,99.28Q30.1,70.01 29.27,69.32Q28.44,68.64 22.82,66.26Q17.2,63.88 14.24,62.08Q11.28,60.27 8.87,58.29Q6.45,56.31 3.6,52.96L0.76,49.6L0.61,99.42Q29.38,99.86 29.92,99.57L30.46,99.28Z M98.59,57.46Q99.1,56.31 99.03,51.73Q98.95,47.15 98.63,40.37Q98.31,33.6 97.37,28.91Q96.43,24.22 95.21,21.27Q93.98,18.31 92.11,15.54Q90.23,12.76 88.68,11.18Q87.13,9.59 83.99,7.39Q80.86,5.19 77.04,3.57Q73.22,1.95 68.64,1.12Q64.06,0.29 32.98,0.14Q1.91,0.0 1.44,0.29L0.97,0.58Q1.41,21.63 3.03,28.59Q4.65,35.54 6.49,39.44Q8.33,43.33 9.66,45.28Q10.99,47.22 13.3,49.53Q15.61,51.84 17.23,52.92Q18.85,54.0 21.67,55.19Q24.48,56.38 27.47,56.89Q30.46,57.39 63.95,57.53Q97.44,57.68 98.02,57.57L98.59,57.46Z";
	const VIEWBOX = "0 0 100 100";

	window.RAQEEM_LOGO_D = D;
	window.RAQEEM_LOGO_SVG = function (cls) {
		return `<svg class="rq-logo ${cls || ""}" viewBox="${VIEWBOX}" role="img" aria-label="RAQEEM"><path fill="currentColor" fill-rule="evenodd" d="${D}"/></svg>`;
	};

	/* ---------- stock logo images -> inline mark ---------- */
	const STOCK = /\/assets\/(erpnext\/images\/erpnext-(logo|favicon)|frappe\/images\/frappe-(framework-logo|favicon|logo))[^"']*|\/assets\/raqim_sales\/images\/raqeem-logo/;
	function swap_images(root) {
		(root || document).querySelectorAll("img").forEach((img) => {
			if (img.dataset.rqLogo) return;
			const src = img.getAttribute("src") || "";
			if (!STOCK.test(src)) return;
			const holder = document.createElement("span");
			holder.className = "rq-logo-holder " + (img.className || "");
			holder.innerHTML = window.RAQEEM_LOGO_SVG();
			// keep the size the page gave the image
			const w = img.getAttribute("width");
			const h = img.getAttribute("height");
			if (w) holder.style.width = /^\d+$/.test(w) ? w + "px" : w;
			if (h) holder.style.height = /^\d+$/.test(h) ? h + "px" : h;
			if (img.id) holder.id = img.id;
			img.dataset.rqLogo = "1";
			img.replaceWith(holder);
		});
	}

	/* ---------- favicon in the theme colour ---------- */
	let last_fill = null;
	function accent() {
		const cs = getComputedStyle(document.documentElement);
		const v = (cs.getPropertyValue("--rq-a-500") || "").trim();
		return v || "#2d4583";
	}
	function set_favicon() {
		const fill = accent();
		if (fill === last_fill) return;
		last_fill = fill;
		const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -6 112 112"><path fill="${fill}" fill-rule="evenodd" d="${D}"/></svg>`;
		const href = "data:image/svg+xml," + encodeURIComponent(svg);
		let links = document.querySelectorAll('link[rel~="icon"]');
		if (!links.length) {
			const l = document.createElement("link");
			l.rel = "icon";
			document.head.appendChild(l);
			links = [l];
		}
		links.forEach((l) => {
			l.type = "image/svg+xml";
			l.href = href;
		});
	}

	let queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			swap_images();
		});
	}

	function start() {
		swap_images();
		set_favicon();
		new MutationObserver((records) => {
			if (records.some((r) => r.addedNodes.length)) schedule();
		}).observe(document.body, { childList: true, subtree: true });
		// colour / light-dark changes
		new MutationObserver(() => setTimeout(set_favicon, 60)).observe(document.documentElement, {
			attributes: true,
			attributeFilter: ["data-accent", "data-theme", "data-rq-theme"],
		});
		if (window.matchMedia) {
			const mq = window.matchMedia("(prefers-color-scheme: dark)");
			mq.addEventListener && mq.addEventListener("change", () => setTimeout(set_favicon, 60));
		}
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
