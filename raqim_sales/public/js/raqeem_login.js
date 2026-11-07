/* RAQEEM — login page extras (brand panel + language switch) and, on every
   website page, the theme colour saved in the desk.
   Loaded on every website page through web_include_js, the brand panel is only
   added on the login / update-password pages. */
(function () {
	// ---- edit these to change the brand text ----------------------------
	const BRAND = {
		ar: {
			name: "RAQEEM",
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
			name: "RAQEEM",
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
		word.className = "rq-card-wordmark";
		word.textContent = "RAQEEM";
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
			<div class="rq-brand-mark">${logo ? `<img src="${esc(logo.getAttribute("src"))}" alt="">` : `<span class="rq-brand-monogram">R</span>`}</div>
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

	// language switch (guests: Frappe reads the preferred_language cookie)
	const sw = document.createElement("button");
	sw.type = "button";
	sw.className = "rq-lang-switch";
	sw.innerHTML = `${svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>')}<span>${esc(t.switch_label)}</span>`;
	sw.addEventListener("click", () => {
		document.cookie = `preferred_language=${t.switch_to}; path=/; max-age=31536000; SameSite=Lax`;
		const url = new URL(window.location.href);
		url.searchParams.delete("_lang");
		window.location.replace(url.toString());
	});
	document.body.appendChild(sw);
})();
