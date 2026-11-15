// RAQEEM HR: monthly attendance sheet (codes from the server, shown as coloured letters)
(function () {
	const ar = (frappe.boot.lang || "").startsWith("ar");
	const LOOK = {
		P: { t: ar ? "ح" : "P", c: "var(--green-600)", tip: "Present" },
		A: { t: ar ? "غ" : "A", c: "var(--red-600)", tip: "Absent" },
		HD: { t: ar ? "½" : "½", c: "var(--orange-600)", tip: "Half Day" },
		L: { t: ar ? "إ" : "L", c: "var(--blue-600)", tip: "On Leave" },
		M: { t: ar ? "ح؟" : "P?", c: "var(--yellow-700, #a16207)", tip: "Missing Fingerprint" },
		WO: { t: ar ? "ر" : "WO", c: "var(--gray-500)", tip: "Weekly Off" },
		H: { t: ar ? "ع" : "H", c: "var(--purple-600, #9333ea)", tip: "Holiday" },
		"-": { t: "·", c: "var(--gray-400)", tip: "" },
	};
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	frappe.query_reports["Raqeem Monthly Attendance"] = {
		filters: [
			{
				fieldname: "month", label: __("Month"), fieldtype: "Select", reqd: 1, default: String(today.getMonth() + 1),
				options: Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1), label: __(moment().month(i).format("MMMM")) })),
			},
			{ fieldname: "year", label: __("Year"), fieldtype: "Int", reqd: 1, default: today.getFullYear() },
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
			{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
			{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		],
		formatter(value, row, column, data, default_formatter) {
			if (column.fieldname && /^d\d+$/.test(column.fieldname)) {
				const l = LOOK[value];
				if (!l) return "";
				return `<span title="${__(l.tip)}" style="color:${l.c};font-weight:600">${l.t}</span>`;
			}
			value = default_formatter(value, row, column, data);
			if (column.fieldname === "absent" && data && flt(data.absent) > 0) value = `<span style="color: var(--red-600)">${value}</span>`;
			return value;
		},
	};
})();
