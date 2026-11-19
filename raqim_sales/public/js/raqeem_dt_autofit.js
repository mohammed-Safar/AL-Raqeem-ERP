/* RAQEEM: report tables — number columns grow to fit their numbers (2026-11-19).
 * Frappe gives amount columns a fixed width (General Ledger: 130px), so a big amount such as
 * 2,000,000,000.000 د.ل was cut and showed only "000,000,000.000" — a wrong-looking number.
 * Fix: after the table draws, any Currency / Float / Int / Percent column whose numbers do not
 * fit is widened just enough (max 320px). Columns only grow, never shrink; text columns keep
 * Frappe's "..." behaviour.
 * ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	"use strict";
	if (window.__rq_dt_autofit) return;
	window.__rq_dt_autofit = true;

	const NUMERIC = ["Currency", "Float", "Int", "Percent"];
	const MAX = 320;

	function needed(el) {
		let w = el.scrollWidth;
		// formatted values sit in an inner <div>: measure it too, plus the cell's side padding
		const cs = getComputedStyle(el);
		const pad = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
		for (const c of el.querySelectorAll("*")) w = Math.max(w, c.scrollWidth + pad);
		return Math.ceil(w);
	}

	function fit(dt) {
		if (!dt || !dt.datamanager || !dt.bodyScrollable || !dt.wrapper.isConnected) return;
		let changed = false;
		for (const col of dt.datamanager.getColumns()) {
			if (!NUMERIC.includes(col.fieldtype) || !col.width) continue;
			const sel = `.dt-cell__content--col-${col.colIndex}`;
			const cells = [
				...dt.bodyScrollable.querySelectorAll(sel),
				...(dt.footer ? dt.footer.querySelectorAll(sel) : []),
			];
			let need = 0;
			for (const el of cells) need = Math.max(need, needed(el));
			if (need > col.width + 1 && col.width < MAX) {
				dt.datamanager.updateColumn(col.colIndex, { width: Math.min(need + 4, MAX) });
				changed = true;
			}
		}
		if (changed) dt.style.refreshColumnWidth();
	}

	let queued = false;
	function scan() {
		queued = false;
		const tables = [window.frappe?.query_report?.datatable, window.cur_list?.datatable];
		for (const dt of tables) {
			try { fit(dt); } catch (e) { /* never break a report */ }
		}
	}
	function queue() {
		if (queued) return;
		queued = true;
		setTimeout(scan, 200);
	}
	new MutationObserver(queue).observe(document.documentElement, { childList: true, subtree: true });
	window.addEventListener("resize", queue);
})();
