/* RAQEEM — smooth hand-off from the loading screen to the desk.
   Frappe's desk.js deletes .splash in one frame when the desk is ready. Here the
   real loading screen loses the "splash" class and a hidden stand-in takes it;
   when desk.js removes the stand-in, the real one fades out (CSS in
   templates/includes/splash_screen.html) and is then removed.
   (The light/dark memory shared with the login page lives in raqeem_quick_settings.js.)
   Must load before Frappe starts the desk (first entry of app_include_js).
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const root = document.documentElement;

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
	// preview: open /desk?rq_splash=hold to keep the loading screen up until you click it
	if (/[?&]rq_splash=hold\b/.test(location.search)) {
		splash.style.cursor = "pointer";
		splash.addEventListener("click", () => { done = false; fade_out(); });
		done = true; // ignore the desk's "ready" signal
		return;
	}
	observer.observe(document.body, { childList: true });
	// never leave it stuck if the desk fails to start
	setTimeout(fade_out, 20000);
})();
