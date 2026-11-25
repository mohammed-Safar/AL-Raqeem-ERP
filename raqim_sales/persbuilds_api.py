# API for the PersBuilds website (~/PersBuilds-main), reached through its serve.py proxy.
# Clients: register / log in, read live prices + stock, save builds, send a build as a draft Sales Order.
# Admin (System Manager / Sales Manager): overview of web builds, orders, clients and stock.
import json
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, now_datetime, nowdate, validate_email_address

COMPANY = "PersBuilds"
PRICE_LIST = "Standard Selling"
USD_RATE = 6.5  # same as EXCHANGE_RATE in the site's config.js
ORDER_WAREHOUSE = "المخازن - PB"
WEB_PART = "PB-WEB-PART"
WEB_PART_GROUP = "قطع من طلبات الموقع"
ADMIN_ROLES = {"System Manager", "Sales Manager"}

# ERPNext item group -> site category (components.json keys)
GROUP_TO_CATEGORY = {
	"المعالجات": "cpus",
	"كروت الشاشة": "gpus",
	"اللوحات الأم": "motherboards",
	"الذاكرة": "ram",
	"وحدات التخزين": "storage",
	"صناديق الحاسوب": "cases",
	"مزودات الطاقة": "psus",
	"التبريد": "cooling",
	"الملحقات": "accessories",
	"الشاشات": "monitors",
	"الحواسيب المحمولة": "laptops",
	"أجهزة PersBuilds المجمّعة": "prebuilt",
}
CATEGORY_LABEL = {
	"cpus": "المعالج (CPU)",
	"gpus": "كرت الشاشة (GPU)",
	"motherboards": "اللوحة الأم (Motherboard)",
	"ram": "الذاكرة العشوائية (RAM)",
	"storage": "وحدة التخزين (Storage)",
	"psus": "مزود الطاقة (PSU)",
	"cases": "صندوق الحاسوب (Case)",
}


# ---------------------------------------------------------------- helpers
@contextmanager
def as_admin():
	"""Run ERPNext code as Administrator inside a website request WITHOUT touching the
	client's login: frappe.set_user() also overwrites session.sid/session.data, which would
	send the browser a broken sid cookie (client logged out) and drop its CSRF token."""
	sess = frappe.local.session
	saved = (sess.user, sess.sid, sess.data, frappe.local.form_dict)
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		sess.user, sess.sid, sess.data, frappe.local.form_dict = saved
		frappe.local.cache = {}
		frappe.local.role_permissions = {}
		frappe.local.user_perms = None


def _user():
	return frappe.session.user


def _require_login():
	if _user() == "Guest":
		frappe.throw(_("يرجى تسجيل الدخول أولاً"), frappe.AuthenticationError)


def _is_admin(user=None):
	return bool(ADMIN_ROLES & set(frappe.get_roles(user or _user())))


def _require_admin():
	_require_login()
	if not _is_admin():
		frappe.throw(_("هذه الصفحة للإدارة فقط"), frappe.PermissionError)


def _customer_of(user):
	return frappe.db.get_value("Portal User", {"user": user, "parenttype": "Customer"}, "parent")


def _warehouses():
	return frappe.get_all("Warehouse", filters={"company": COMPANY, "is_group": 0}, pluck="name")


def _catalog_rows():
	groups = list(GROUP_TO_CATEGORY)
	items = frappe.get_all(
		"Item",
		filters={"disabled": 0, "item_group": ["in", groups], "has_variants": 0},
		fields=["name", "item_name", "item_group", "is_stock_item", "standard_rate"],
	)
	if not items:
		return []
	codes = [i.name for i in items]
	prices = dict(
		frappe.get_all(
			"Item Price",
			filters={"price_list": PRICE_LIST, "item_code": ["in", codes]},
			fields=["item_code", "price_list_rate"],
			as_list=True,
		)
	)
	stock = {}
	whs = _warehouses()
	if whs:
		for code, qty in frappe.db.sql(
			"""select item_code, sum(actual_qty - reserved_qty) from `tabBin`
			where item_code in %(codes)s and warehouse in %(whs)s group by item_code""",
			{"codes": codes, "whs": whs},
		):
			stock[code] = flt(qty)
	rows = []
	for i in items:
		rate = flt(prices.get(i.name) or i.standard_rate)
		rows.append(
			{
				"code": i.name,
				"name": i.item_name,
				"category": GROUP_TO_CATEGORY[i.item_group],
				"group": i.item_group,
				"price_lyd": rate,
				"price_usd": round(rate / USD_RATE, 2),
				"stock": max(stock.get(i.name, 0), 0) if i.is_stock_item else None,
			}
		)
	rows.sort(key=lambda r: (r["category"], r["price_lyd"]))
	return rows


def _by_name():
	return {r["name"].strip().lower(): r for r in _catalog_rows()}


def _clean_parts(parts):
	"""parts from the site: [{category, label, name, price_usd}] -> priced from AlRaqeem when the name matches."""
	if isinstance(parts, str):
		parts = json.loads(parts or "[]")
	if not isinstance(parts, list) or not parts or len(parts) > 20:
		frappe.throw(_("قائمة القطع غير صحيحة"))
	erp = _by_name()
	out = []
	for p in parts:
		name = (p.get("name") or "").strip()[:140]
		if not name:
			continue
		hit = erp.get(name.lower())
		price_usd = flt(p.get("price_usd"))
		if price_usd < 0 or price_usd > 100000:
			frappe.throw(_("سعر غير صحيح"))
		out.append(
			{
				"category": (p.get("category") or "")[:30],
				"label": (p.get("label") or CATEGORY_LABEL.get(p.get("category"), ""))[:60],
				"name": name,
				"item_code": hit["code"] if hit else None,
				"price_lyd": hit["price_lyd"] if hit else round(price_usd * USD_RATE, 2),
				"from_erp": bool(hit),
			}
		)
	if not out:
		frappe.throw(_("قائمة القطع فارغة"))
	return out


def _build_dict(b):
	return {
		"id": b.name,
		"title": b.build_title,
		"usage": b.usage,
		"total_lyd": flt(b.total_lyd),
		"total_usd": flt(b.total_usd),
		"wattage": cint(b.wattage),
		"parts": json.loads(b.parts_json or "[]"),
		"sales_order": b.sales_order,
		"order_status": frappe.db.get_value("Sales Order", b.sales_order, "status") if b.sales_order else None,
		"customer": b.customer,
		"created": str(b.creation)[:16],
		"order_total": flt(frappe.db.get_value("Sales Order", b.sales_order, "grand_total")) if b.sales_order else None,
		"payment": _last_payment(b.name),
	}


def _last_payment(build):
	"""latest payment attempt of a build, the one that matters for the client"""
	rows = frappe.get_all(
		"PersBuilds Web Payment",
		filters={"web_build": build},
		fields=["name", "status", "method", "amount", "is_deposit", "demo", "transaction_id"],
		order_by="creation desc",
		limit=5,
	)
	if not rows:
		return None
	# a finished/pending one wins over a later failed retry
	for r in rows:
		if r.status in ("Paid", "Awaiting Check", "Pay On Delivery"):
			return r
	return rows[0]


# ---------------------------------------------------------------- public
@frappe.whitelist(allow_guest=True)
def session_info():
	user = _user()
	if user == "Guest":
		return {"user": "Guest"}
	return {
		"user": user,
		"full_name": frappe.db.get_value("User", user, "full_name") or user,
		"is_admin": _is_admin(),
		"customer": _customer_of(user),
		"csrf_token": frappe.sessions.get_csrf_token(),
	}


@frappe.whitelist(allow_guest=True)
def catalog():
	return {"usd_rate": USD_RATE, "items": _catalog_rows()}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def register(full_name, email, password, phone=None):
	full_name = (full_name or "").strip()[:100]
	email = (email or "").strip().lower()
	if len(full_name) < 3:
		frappe.throw(_("يرجى كتابة الاسم الكامل"))
	if not validate_email_address(email):
		frappe.throw(_("البريد الإلكتروني غير صحيح"))
	if len(password or "") < 8:
		frappe.throw(_("كلمة المرور يجب أن تكون 8 أحرف على الأقل"))
	if frappe.db.exists("User", email):
		frappe.throw(_("هذا البريد مسجل مسبقاً، يرجى تسجيل الدخول"))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"mobile_no": (phone or "").strip()[:20] or None,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"enabled": 1,
		}
	)
	user.flags.ignore_permissions = True
	user.insert()
	user.add_roles("Customer")
	from frappe.utils.password import update_password

	update_password(email, password)

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": full_name,
			"customer_type": "Individual",
			"customer_group": "Individual",
			"territory": "Libya",
			"default_currency": "LYD",
			"mobile_no": (phone or "").strip()[:20] or None,
			"email_id": email,
			"portal_users": [{"user": email}],
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()
	frappe.db.commit()

	frappe.local.login_manager.login_as(email)
	return session_info()


# ---------------------------------------------------------------- client
@frappe.whitelist()
def my_builds():
	_require_login()
	rows = frappe.get_all(
		"PersBuilds Web Build", filters={"user": _user()}, fields=["*"], order_by="creation desc", limit=100
	)
	return [_build_dict(b) for b in rows]


@frappe.whitelist(methods=["POST"])
def save_build(title, parts, usage=None, wattage=0):
	_require_login()
	clean = _clean_parts(parts)
	total_lyd = round(sum(p["price_lyd"] for p in clean), 2)
	doc = frappe.get_doc(
		{
			"doctype": "PersBuilds Web Build",
			"build_title": (title or "").strip()[:100] or _("تجميعة مخصصة"),
			"usage": (usage or "")[:60],
			"user": _user(),
			"customer": _customer_of(_user()),
			"wattage": cint(wattage),
			"total_lyd": total_lyd,
			"total_usd": round(total_lyd / USD_RATE, 2),
			"parts_json": json.dumps(clean, ensure_ascii=False, indent=1),
		}
	)
	doc.insert(ignore_permissions=True)
	return _build_dict(doc)


def _own_build(name):
	_require_login()
	doc = frappe.get_doc("PersBuilds Web Build", name)
	if doc.user != _user() and not _is_admin():
		frappe.throw(_("لا يمكنك الوصول لهذه التجميعة"), frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["POST"])
def delete_build(name):
	doc = _own_build(name)
	if doc.sales_order:
		frappe.throw(_("تم إرسال هذه التجميعة كطلب ولا يمكن حذفها"))
	frappe.delete_doc("PersBuilds Web Build", doc.name, ignore_permissions=True)
	return True


def _ensure_web_part():
	if frappe.db.exists("Item", WEB_PART):
		return
	if not frappe.db.exists("Item Group", WEB_PART_GROUP):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": WEB_PART_GROUP, "parent_item_group": "All Item Groups"}
		).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": WEB_PART,
			"item_name": "قطعة من طلب الموقع (تُستبدل بالصنف الفعلي)",
			"item_group": WEB_PART_GROUP,
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
			"description": "قطعة طلبها عميل من موقع PersBuilds وليست مسجلة كصنف بعد. استبدلها بالصنف الفعلي قبل الاعتماد.",
		}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def send_order(name):
	doc = _own_build(name)
	if doc.sales_order:
		return _build_dict(doc)
	customer = doc.customer or _customer_of(doc.user)
	if not customer:
		frappe.throw(_("حسابك غير مرتبط بعميل في النظام، يرجى التواصل معنا"))
	parts = json.loads(doc.parts_json or "[]")
	# re-price matched parts with today's AlRaqeem price
	erp = {r["code"]: r for r in _catalog_rows()}
	if any(not p.get("item_code") for p in parts):
		_ensure_web_part()
	delivery = add_days(nowdate(), 3)
	items = []
	for p in parts:
		code = p.get("item_code") if p.get("item_code") in erp else None
		rate = erp[code]["price_lyd"] if code else flt(p.get("price_lyd"))
		row = {
			"item_code": code or WEB_PART,
			"qty": 1,
			"rate": rate,
			"delivery_date": delivery,
			"description": f"{p.get('label') or ''}: {p['name']}"
			+ ("" if code else " (سعر تقديري من الموقع - غير مسجلة كصنف)"),
		}
		if not code:
			row["item_name"] = p["name"][:140]
		items.append(row)
	with as_admin():  # ERPNext item/price lookups inside SO.validate check permissions
		so = _make_sales_order(doc, customer, delivery, items)
	doc.db_set({"sales_order": so.name, "sent_on": now_datetime(), "customer": customer})
	return _build_dict(doc)


def _make_sales_order(doc, customer, delivery, items):
	so = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"company": COMPANY,
			"customer": customer,
			"order_type": "Sales",
			"transaction_date": nowdate(),
			"delivery_date": delivery,
			"currency": "LYD",
			"selling_price_list": PRICE_LIST,
			"set_warehouse": ORDER_WAREHOUSE,
			"po_no": doc.name,
			"items": items,
		}
	)
	so.flags.ignore_permissions = True
	so.insert()
	so.add_comment("Comment", f"طلب من موقع PersBuilds — التجميعة «{doc.build_title}» ({doc.name})")
	return so


# ---------------------------------------------------------------- admin
@frappe.whitelist()
def admin_overview():
	_require_admin()
	builds = frappe.get_all("PersBuilds Web Build", fields=["*"], order_by="creation desc", limit=200)
	so_names = [b.sales_order for b in builds if b.sales_order]
	so_info = {}
	if so_names:
		for r in frappe.get_all(
			"Sales Order",
			filters={"name": ["in", so_names]},
			fields=["name", "status", "docstatus", "grand_total", "per_delivered", "per_billed"],
		):
			so_info[r.name] = r
	out_builds = []
	for b in builds:
		d = _build_dict(b)
		d["customer_name"] = frappe.db.get_value("Customer", b.customer, "customer_name") if b.customer else None
		d["user"] = b.user
		s = so_info.get(b.sales_order)
		if s:
			d["order_status"] = s.status
			d["order_total"] = flt(s.grand_total)
		out_builds.append(d)

	clients = frappe.db.sql(
		"""select c.name as customer, c.customer_name, pu.user, u.mobile_no, u.creation,
			u.last_login, u.enabled
		from `tabPortal User` pu
		join `tabCustomer` c on c.name = pu.parent and pu.parenttype = 'Customer'
		join `tabUser` u on u.name = pu.user
		order by u.creation desc limit 200""",
		as_dict=True,
	)
	for c in clients:
		c["builds"] = sum(1 for b in builds if b.user == c.user)
		c["orders"] = sum(1 for b in builds if b.user == c.user and b.sales_order)
		c["creation"] = str(c["creation"])[:16]
		c["last_login"] = str(c["last_login"] or "")[:16]

	catalog_rows = _catalog_rows()
	return {
		"builds": out_builds,
		"clients": clients,
		"catalog": catalog_rows,
		"stats": {
			"clients": len(clients),
			"builds": len(builds),
			"orders": len(so_names),
			"orders_open": sum(1 for s in so_info.values() if s.status not in ("Completed", "Closed", "Cancelled")),
			"low_stock": sum(1 for r in catalog_rows if r["stock"] is not None and r["stock"] <= 2),
		},
	}
