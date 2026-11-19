"""Account names in two languages. The chart of accounts is stored in Arabic on Arabic sites
(renamed 2026-11-18), while our setup code names accounts in English. These helpers let every
lookup find an account by either name, and give new accounts the site's language."""

import frappe


def _ar(name):
	try:
		from frappe.translate import get_all_translations
		return get_all_translations("ar").get(name)
	except Exception:
		return None


def variants(name):
	"""[English name, Arabic name] (only the ones that exist)."""
	out = [name]
	ar = _ar(name)
	if ar and ar != name:
		out.append(ar)
	return out


def local_name(name):
	"""The name a NEW account should get: Arabic when the site's language is Arabic."""
	lang = (frappe.db.get_single_value("System Settings", "language") or "en").lower()
	return (_ar(name) or name) if lang.startswith("ar") else name


def find(company, name, is_group=None, **extra):
	"""The account called `name` (English or Arabic) in the company, or None."""
	filters = {"company": company, "account_name": ["in", variants(name)], **extra}
	if is_group is not None:
		filters["is_group"] = is_group
	return frappe.db.get_value("Account", filters, "name")
