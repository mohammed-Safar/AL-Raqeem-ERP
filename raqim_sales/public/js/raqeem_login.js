/* RAQEEM — login page extras (brand panel + language switch) and, on every
   website page, the theme colour saved in the desk.
   Loaded on every website page through web_include_js, the brand panel is only
   added on the login / update-password pages. */
(function () {
	// ---- edit these to change the brand text ----------------------------
	const BRAND = {
		ar: {
			name: "AL-RAQEEM",
			tagline: "مبيعاتك ومخزونك وحساباتك في مكان واحد",
			points: [
				"فواتير وعروض أسعار بضغطة زر",
				"متابعة المخزون لحظة بلحظة",
				"تقارير واضحة تساعدك على اتخاذ القرار",
			],
			switch_label: "English",
			switch_to: "en",
		},
		en: {
			name: "AL-RAQEEM",
			tagline: "Your sales, stock and accounts in one place",
			points: [
				"Invoices and quotations in a click",
				"Live stock tracking",
				"Clear reports that help you decide",
			],
			switch_label: "العربية",
			switch_to: "ar",
		},
	};
	// ----------------------------------------------------------------------

	// theme colour chosen in the desk (quick settings) -> login + portal pages too
	try {
		const a = localStorage.getItem("raqeem_accent");
		// no attribute = black & white (the default)
		if (["orange", "gold", "yellow", "red", "purple", "blue", "green"].includes(a))
			document.documentElement.setAttribute("data-accent", a);
		// light/dark chosen in the desk: the loading screen after sign-in uses it
		const m = localStorage.getItem("raqeem_theme");
		if (m === "light" || m === "dark") document.documentElement.setAttribute("data-rq-theme", m);
	} catch (e) {}

	const path = document.body && document.body.getAttribute("data-path");
	if (path !== "login" && path !== "update-password") return;
	if (document.querySelector(".rq-brand")) return;

	const lang = (document.documentElement.lang || "en").toLowerCase().startsWith("ar") ? "ar" : "en";
	const t = BRAND[lang];
	// Until a real logo is uploaded (Website Settings → App Logo), Frappe shows
	// the stock ERPNext/Frappe logo: swap it for the RAQEEM wordmark.
	let logo = document.querySelector(".page-card-head img.app-logo");
	const stock = (src) => !src || /\/assets\/(erpnext|frappe)\//.test(src);
	if (logo && stock(logo.getAttribute("src"))) {
		const word = document.createElement("div");
		word.className = "rq-card-brand";
		word.innerHTML =
			(window.RAQEEM_LOGO_SVG ? `<span class="rq-card-logo">${window.RAQEEM_LOGO_SVG()}</span>` : "") +
			'<span class="rq-card-wordmark">AL-RAQEEM</span>';
		logo.replaceWith(word);
		logo = null;
	}

	const icons = [
		'<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5"/><path d="M10 13h6M10 17h4"/>',
		'<path d="M3 8l9-5 9 5v8l-9 5-9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
		'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
	];
	const svg = (d) =>
		`<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
	const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

	const aside = document.createElement("aside");
	aside.className = "rq-brand";
	aside.setAttribute("aria-hidden", "true");
	aside.innerHTML = `
		<div class="rq-brand-inner">
			<div class="rq-brand-mark">${logo ? `<img src="${esc(logo.getAttribute("src"))}" alt="">` : (window.RAQEEM_LOGO_SVG ? `<span class="rq-brand-logo">${window.RAQEEM_LOGO_SVG()}</span>` : `<span class="rq-brand-monogram">R</span>`)}</div>
			<h1 class="rq-brand-name">${esc(t.name)}</h1>
			<p class="rq-brand-tagline">${esc(t.tagline)}</p>
			<ul class="rq-brand-points">
				${t.points.map((p, i) => `<li><span class="rq-point-icon">${svg(icons[i % icons.length])}</span><span>${esc(p)}</span></li>`).join("")}
			</ul>
			<div class="rq-brand-foot">© ${new Date().getFullYear()} ${esc(t.name)}</div>
		</div>
		<div class="rq-brand-orbit" aria-hidden="true"><span></span><span></span><span></span></div>`;
	document.body.appendChild(aside);
	document.body.classList.add("rq-login-split");

	// display settings (guests): light / dark / automatic, theme colour, language.
	// Saved in this browser (localStorage raqeem_theme / raqeem_accent and Frappe's
	// preferred_language cookie); the desk reads the same keys.
	const ar = lang === "ar";
	const L = ar
		? { title: "إعدادات العرض", appearance: "المظهر", light: "فاتح", dark: "داكن", auto: "تلقائي", colour: "لون الواجهة", language: "اللغة",
			names: { mono: "أبيض وأسود", orange: "برتقالي", gold: "ذهبي", yellow: "أصفر", red: "أحمر", purple: "بنفسجي سايبر", blue: "أزرق", green: "أخضر" } }
		: { title: "Display settings", appearance: "Appearance", light: "Light", dark: "Dark", auto: "Auto", colour: "Theme colour", language: "Language",
			names: { mono: "Black & White", orange: "Orange", gold: "Gold", yellow: "Yellow", red: "Red", purple: "Cyber Purple", blue: "Blue", green: "Green" } };
	const SWATCH = { mono: "", orange: "#f97316", gold: "#d4a72c", yellow: "#facc15", red: "#ef4444", purple: "#a855f7", blue: "#2563eb", green: "#76b900" };
	const root = document.documentElement;
	const store = (k, v) => {
		try {
			v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v);
		} catch (e) {}
	};
	const cur_theme = () => root.getAttribute("data-rq-theme") || "auto";
	const cur_accent = () => root.getAttribute("data-accent") || "mono";

	const btn = document.createElement("button");
	btn.type = "button";
	btn.className = "rq-lang-switch rq-web-qs-btn";
	btn.setAttribute("aria-haspopup", "dialog");
	btn.setAttribute("aria-expanded", "false");
	btn.title = L.title;
	btn.innerHTML = `${svg('<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none"/>')}<span>${esc(L.title)}</span>`;

	const pop = document.createElement("div");
	pop.className = "rq-web-qs";
	pop.setAttribute("role", "dialog");
	pop.setAttribute("aria-label", L.title);
	const render = () => {
		const th = cur_theme();
		const ac = cur_accent();
		pop.innerHTML = `
			<div class="rq-web-qs-title">${esc(L.title)}</div>
			<div class="rq-web-qs-label">${esc(L.appearance)}</div>
			<div class="rq-web-qs-seg">
				${["light", "dark", "auto"].map((m) => `<button type="button" data-theme-pick="${m}" class="${th === m ? "is-on" : ""}">${esc(L[m])}</button>`).join("")}
			</div>
			<div class="rq-web-qs-label">${esc(L.colour)}</div>
			<div class="rq-web-qs-swatches">
				${Object.keys(SWATCH).map((a) => `<button type="button" data-accent-pick="${a}" class="rq-web-sw ${ac === a ? "is-on" : ""}" title="${esc(L.names[a])}" aria-label="${esc(L.names[a])}" style="${SWATCH[a] ? `--sw:${SWATCH[a]}` : ""}"></button>`).join("")}
			</div>
			<div class="rq-web-qs-label">${esc(L.language)}</div>
			<div class="rq-web-qs-seg">
				<button type="button" data-lang-pick="ar" class="${ar ? "is-on" : ""}">العربية</button>
				<button type="button" data-lang-pick="en" class="${!ar ? "is-on" : ""}">English</button>
			</div>`;
	};
	const open = (yes) => {
		pop.classList.toggle("is-open", yes);
		btn.setAttribute("aria-expanded", yes ? "true" : "false");
		if (yes) render();
	};
	btn.addEventListener("click", () => open(!pop.classList.contains("is-open")));
	document.addEventListener("pointerdown", (e) => {
		if (pop.classList.contains("is-open") && !pop.contains(e.target) && !btn.contains(e.target)) open(false);
	});
	document.addEventListener("keydown", (e) => e.key === "Escape" && open(false));
	pop.addEventListener("click", (e) => {
		const b = e.target.closest("button");
		if (!b) return;
		if (b.dataset.themePick) {
			const m = b.dataset.themePick;
			root.classList.add("rq-web-fading");
			if (m === "auto") {
				root.removeAttribute("data-rq-theme");
				store("raqeem_theme", null);
			} else {
				root.setAttribute("data-rq-theme", m);
				store("raqeem_theme", m);
			}
			setTimeout(() => root.classList.remove("rq-web-fading"), 450);
			render();
		} else if (b.dataset.accentPick) {
			const a = b.dataset.accentPick;
			root.classList.add("rq-web-fading");
			a === "mono" ? root.removeAttribute("data-accent") : root.setAttribute("data-accent", a);
			store("raqeem_accent", a);
			setTimeout(() => root.classList.remove("rq-web-fading"), 450);
			render();
		} else if (b.dataset.langPick && b.dataset.langPick !== lang) {
			document.cookie = `preferred_language=${b.dataset.langPick}; path=/; max-age=31536000; SameSite=Lax`;
			const url = new URL(window.location.href);
			url.searchParams.delete("_lang");
			window.location.replace(url.toString());
		}
	});
	document.body.appendChild(btn);
	document.body.appendChild(pop);
})();
