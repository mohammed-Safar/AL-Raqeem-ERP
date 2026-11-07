/* RAQEEM — smooth hand-off from the loading screen to the desk.
   Frappe's desk.js deletes .splash in one frame when the desk is ready. Here the
   real loading screen loses the "splash" class and a hidden stand-in takes it;
   when desk.js removes the stand-in, the real one fades out (CSS in
   templates/includes/splash_screen.html) and is then removed.
   Also remembers the light/dark choice in localStorage so the screen after the
   next sign-in starts in the right colours (read by raqeem_login.js).
   Must load before Frappe starts the desk (first entry of app_include_js).
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const root = document.documentElement;

	function remember_theme() {
		const t = root.getAttribute("data-theme");
		if (t !== "light" && t !== "dark") return;
		try {
			localStorage.setItem("raqeem_theme", t);
		} catch (e) {}
	}
	remember_theme();
	new MutationObserver(remember_theme).observe(root, { attributes: true, attributeFilter: ["data-theme"] });

	const splash = document.querySelector(".splash.rq-splash");
	if (!splash || !document.body) return;

	const stand_in = document.createElement("div");
	stand_in.className = "splash";
	stand_in.hidden = true;
	document.body.appendChild(stand_in);
	splash.classList.remove("splash");

	let done = false;
	function fade_out() {
		if (done) return;
		done = true;
		observer.disconnect();
		// two frames: let the desk paint underneath first
		requestAnimationFrame(() =>
			requestAnimationFrame(() => {
				splash.classList.add("rq-splash-out");
				setTimeout(() => splash.remove(), 600);
			})
		);
	}
	const observer = new MutationObserver(() => {
		if (!stand_in.isConnected) fade_out();
	});
	observer.observe(document.body, { childList: true });
	// never leave it stuck if the desk fails to start
	setTimeout(fade_out, 20000);
})();
