// RAQEEM dock arrows (2026-11-22): scroll buttons for the dock's module list when it does not fit.
// Classic skin: the dock is a vertical rail -> ▲ above and ▼ below the modules.
// Horizon («الأفق»): the dock is the top bar -> ◀ and ▶ at both ends of the module tabs.
// An arrow shows only when modules are hidden; it dims at its end. Styles: raqeem_theme.css 11z-g.
// ROLLBACK: delete this file's line in hooks.py (and the 11z-g CSS block).
(() => {
	const STEP = 0.7; // part of the visible length scrolled per click
	const CHEVRON =
		'<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';

	const horizontal = (items) => getComputedStyle(items).flexDirection.startsWith("row");

	function make(side) {
		const b = document.createElement("button");
		b.type = "button";
		b.className = `rq-dock-arrow rq-dock-arrow-${side}`;
		b.dataset.side = side;
		b.innerHTML = CHEVRON;
		const ar = document.documentElement.lang === "ar";
		const labels = {
			up: ar ? "للأعلى" : "Up",
			down: ar ? "للأسفل" : "Down",
			left: ar ? "لليسار" : "Left",
			right: ar ? "لليمين" : "Right",
		};
		b.setAttribute("aria-label", labels[side]);
		b.title = labels[side];
		b.addEventListener("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const items = document.querySelector(".dock .dock-items");
			if (!items) return;
			const h = horizontal(items);
			const d = Math.round((h ? items.clientWidth : items.clientHeight) * STEP);
			const sign = side === "up" || side === "left" ? -1 : 1;
			items.scrollBy(h ? { left: sign * d, behavior: "smooth" } : { top: sign * d, behavior: "smooth" });
		});
		return b;
	}

	function update() {
		const dock = document.querySelector(".dock");
		const items = dock && dock.querySelector(".dock-items");
		if (!items) return;
		if (!dock.dataset.rqArrowsObs) {
			dock.dataset.rqArrowsObs = "1"; // the dock re-renders its modules (module list changes)
			new MutationObserver(schedule).observe(dock, { childList: true, subtree: true });
		}
		const h = horizontal(items);
		const want = h ? ["left", "right"] : ["up", "down"];
		// (re)build the pair when missing or when the skin switched direction
		let arrows = [...dock.querySelectorAll(":scope > .rq-dock-arrow")];
		if (arrows.length !== 2 || arrows[0].dataset.side !== want[0] && arrows[1].dataset.side !== want[0]) {
			arrows.forEach((a) => a.remove());
			const a = make(want[0]);
			const b = make(want[1]);
			items.before(a);
			items.after(b);
			arrows = [a, b];
			if (!items.dataset.rqArrows) {
				items.dataset.rqArrows = "1";
				items.addEventListener("scroll", () => requestAnimationFrame(update), { passive: true });
			}
		}
		const max = h ? items.scrollWidth - items.clientWidth : items.scrollHeight - items.clientHeight;
		const over = max > 2;
		dock.classList.toggle("rq-dock-scrolls", over);
		let atStart, atEnd; // start = left / top end, end = right / bottom end (physical)
		if (h) {
			const rtl = getComputedStyle(items).direction === "rtl";
			const x = items.scrollLeft; // RTL: 0 at the right end, negative toward the left
			atStart = rtl ? x <= -max + 1 : x <= 1;
			atEnd = rtl ? x >= -1 : x >= max - 1;
		} else {
			atStart = items.scrollTop <= 1;
			atEnd = items.scrollTop >= max - 1;
		}
		for (const a of arrows) {
			const first = a.dataset.side === "up" || a.dataset.side === "left";
			a.hidden = !over;
			a.classList.toggle("is-end", first ? atStart : atEnd);
		}
	}

	let queued = false;
	const schedule = () => {
		if (queued) return;
		queued = true;
		setTimeout(() => {
			queued = false;
			update();
		}, 120);
	};

	function start() {
		update();
		window.addEventListener("resize", schedule);
		// dock re-renders, skin switch (html data-skin), zoom (html style)
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: false });
		new MutationObserver(schedule).observe(document.documentElement, { attributes: true, attributeFilter: ["data-skin", "style", "class", "dir"] });
		if (window.frappe && frappe.router) frappe.router.on("change", schedule);
		setTimeout(update, 800);
		setTimeout(update, 2500);
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
