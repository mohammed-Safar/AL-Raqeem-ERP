# RAQEEM HR (Employee Affairs): rules for onboarding, exits and the end-of-service gratuity
# (raqeem_hr/lifecycle.py, raqeem_hr/gratuity.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class RaqeemLifecycleSettings(Document):
	def validate(self):
		if cint(self.month_days) <= 0:
			self.month_days = 30
		for r in self.slabs:
			if flt(r.to_year) and flt(r.to_year) <= flt(r.from_year):
				frappe.throw(_("Slab row {0}: To Year must be above From Year (or 0 for no limit)").format(r.idx))
			if flt(r.days_per_year) < 0:
				frappe.throw(_("Slab row {0}: days cannot be negative").format(r.idx))
		rows = sorted(self.slabs, key=lambda r: flt(r.from_year))
		for a, b in zip(rows, rows[1:]):
			if not flt(a.to_year) or flt(a.to_year) > flt(b.from_year):
				frappe.throw(_("The slabs overlap: {0}–{1} and {2}–").format(flt(a.from_year), flt(a.to_year) or "∞", flt(b.from_year)))
		for r in self.factors:
			if not 0 <= flt(r.percent) <= 100:
				frappe.throw(_("Share row {0}: the share must be between 0 and 100%").format(r.idx))
		for t in ("onboarding_template", "exit_template"):
			want = "Onboarding" if t == "onboarding_template" else "Exit"
			if self.get(t) and frappe.db.get_value("Raqeem Checklist Template", self.get(t), "kind") != want:
				frappe.throw(_("{0} must be a template for {1}").format(_(self.meta.get_label(t)), _(want)))
