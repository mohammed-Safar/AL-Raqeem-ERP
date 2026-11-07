import frappe

ACCENTS = ("mono", "orange", "gold", "yellow", "red", "purple", "blue", "green")  # mono = default


@frappe.whitelist()
def set_accent(accent: str):
	"""Save the user's theme colour (raqeem_accent.js)."""
	if accent not in ACCENTS:
		frappe.throw(frappe._("Invalid colour"))
	frappe.defaults.set_user_default("raqeem_accent", accent)
	return accent


LANGS = ("ar", "en")


@frappe.whitelist()
def set_language(lang: str):
	"""Switch the session user's desk language (raqeem_lang_switch.js)."""
	if lang not in LANGS:
		frappe.throw(frappe._("Invalid language"))
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
	doc = frappe.get_doc("User", user)
	if doc.language != lang:
		doc.language = lang
		doc.save(ignore_permissions=True)  # own record only; also applies locale defaults
	frappe.clear_cache(user=user)
	frappe.local.cookie_manager.set_cookie("preferred_language", lang)
	return lang
