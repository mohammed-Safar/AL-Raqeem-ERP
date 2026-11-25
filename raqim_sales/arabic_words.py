"""Amount in words, written the way Arabic invoices and receipts write it (2026-11-24).

Frappe's money_in_words gives «د.ل ألف و خمسمائة فقط.»: the currency code first and «و» cut off
from the next word. Printed documents in Arabic use this instead:
	فقط ألف وخمسمائة دينار ليبي لا غير
	فقط مائة واثنان وثلاثون ألفًا وأربعمائة وتسعون دينار ليبي و250 -> «... ومئتان وخمسون درهم لا غير»
The currency name stays in its plain form, as is usual on Libyan invoices.
Used by the RAQEEM print templates through the Jinja method `raqeem_amount_in_words`.
"""

import math
import re

import frappe
from frappe.utils import flt

# currency -> (main unit, fraction unit); others fall back to the translated currency name
NAMES = {
	"LYD": ("دينار ليبي", "درهم"),
	"USD": ("دولار أمريكي", "سنت"),
	"EUR": ("يورو", "سنت"),
	"GBP": ("جنيه إسترليني", "بنس"),
	"TND": ("دينار تونسي", "مليم"),
	"EGP": ("جنيه مصري", "قرش"),
	"SAR": ("ريال سعودي", "هللة"),
	"AED": ("درهم إماراتي", "فلس"),
	"TRY": ("ليرة تركية", "قرش"),
	"CNY": ("يوان صيني", "فين"),
}


def _words(n):
	from num2words import num2words

	try:
		w = num2words(int(n), lang="ar")
	except Exception:
		return str(int(n))
	w = re.sub(r"\s+و\s+", " و", w)  # «ألف و خمسمائة» -> «ألف وخمسمائة»
	return w.replace("ألفاً", "ألفًا").strip()


def raqeem_amount_in_words(amount, currency=None):
	amount = abs(flt(amount))
	currency = currency or frappe.db.get_default("currency") or "LYD"
	main_name, frac_name = NAMES.get(currency) or (frappe._(currency, context="Currency"), "")
	units = frappe.db.get_value("Currency", currency, "fraction_units", cache=True) or 0
	digits = math.ceil(math.log10(units)) if units and units > 1 else 0
	main = int(amount)
	frac = int(round((amount - main) * (10**digits))) if digits else 0
	if frac >= 10**digits and digits:
		main, frac = main + 1, 0
	if not main and not frac:
		return f"فقط صفر {main_name} لا غير"
	parts = []
	if main:
		parts.append(f"{_words(main)} {main_name}")
	if frac and frac_name:
		parts.append(f"{_words(frac)} {frac_name}")
	return "فقط " + " و".join(parts) + " لا غير"
