# Payments for the PersBuilds website: every common Libyan way to pay.
#
#   Online, through the Plutu gateway (https://docs.plutu.ly):
#     sadad          Sadad wallet       mobile + birth year -> 6-digit SMS code
#     edfali         Edfali             mobile -> 4-digit SMS code
#     localbankcards Libyan bank cards  redirect to Plutu checkout
#     tlync          T-Lync             Tadawul, MobiCash, Moamalat, Sadad, Edfali (redirect, needs a public site URL)
#     mpgs           Visa / Mastercard  redirect, charged in US dollars
#   Offline:
#     transfer       bank transfer      client uploads the receipt, staff check it
#     cod            cash on delivery / at the showroom
#     cheque         certified cheque on delivery
#
# Live Plutu needs these keys in site_config.json:
#     plutu_api_key, plutu_access_token, plutu_secret_key
#     persbuilds_site_url  (public address of the site, for return/callback links; optional)
# Without the keys the online methods run in TEST MODE: nothing is charged, the published
# Plutu sandbox codes are accepted (Sadad 111111, Edfali 1111) and card checkouts open a local
# test page. Test payments are flagged demo=1 and never create Payment Entries.
import base64
import hashlib
import hmac
import json
import re
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, now_datetime, nowdate

from raqim_sales import persbuilds_api as pba

PLUTU = "https://api.plutus.ly/api/v1/transaction"
DEPOSIT = 0.30
USD_RATE = pba.USD_RATE

METHODS = [
	# code, label, group, online
	("sadad", "سداد", "online", True),
	("edfali", "ادفع لي", "online", True),
	("localbankcards", "البطاقات المصرفية المحلية", "online", True),
	("tlync", "تداول / موبي كاش / معاملات (T-Lync)", "online", True),
	("mpgs", "فيزا / ماستركارد", "online", True),
	("transfer", "حوالة مصرفية", "transfer", False),
	("cod", "نقداً عند الاستلام", "delivery", False),
	("cheque", "صك مصدّق عند الاستلام", "delivery", False),
]
LABEL = {m[0]: m[1] for m in METHODS}
ONLINE = {m[0] for m in METHODS if m[3]}
# AlRaqeem Mode of Payment used for the draft Payment Entry
MODE = {"transfer": "Wire Transfer", "cod": "Cash", "cheque": "Cheque"}
CARD_MODE = "Credit Card"  # online gateway money settles to the bank behind this mode
HASH_FIELDS = {
	"localbankcards": ["gateway", "approved", "canceled", "invoice_no", "amount", "transaction_id"],
	"mpgs": ["gateway", "approved", "canceled", "amount", "currency", "invoice_no", "transaction_id"],
	"tlync": ["gateway", "approved", "invoice_no", "amount", "transaction_id", "payment_method"],
	"tlync_return": ["approved", "invoice_no"],
}


# ---------------------------------------------------------------- config
def _keys():
	c = frappe.conf
	return c.get("plutu_api_key"), c.get("plutu_access_token"), c.get("plutu_secret_key")


def _live():
	return all(_keys())


def _site_base():
	url = (frappe.conf.get("persbuilds_site_url") or "").rstrip("/")
	if url:
		return url
	req = getattr(frappe.local, "request", None)
	host = req.headers.get("Host") if req else None
	return f"http://{host}" if host else "http://localhost:8080"


def _public_site():
	base = _site_base()
	return not re.search(r"//(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", base)


# ---------------------------------------------------------------- plutu
def _plutu(gateway, action, data):
	import requests

	api_key, token, _secret = _keys()
	try:
		r = requests.post(
			f"{PLUTU}/{gateway}/{action}",
			data={k: v for k, v in data.items() if v not in (None, "")},
			headers={"Accept": "application/json", "X-API-KEY": api_key, "Authorization": f"Bearer {token}"},
			timeout=60,
		)
		body = r.json()
	except Exception:
		frappe.log_error(title="Plutu request failed")
		frappe.throw(_("تعذر الاتصال ببوابة الدفع، حاول بعد قليل"))
	if r.status_code != 200 or body.get("status") != 200:
		err = body.get("error") or {}
		frappe.throw(_plutu_error(err.get("code"), err.get("message")))
	return body.get("result") or {}


def _plutu_error(code, message=None):
	msgs = {
		"INVLIAD_OTP": "رمز التحقق غير صحيح",
		"INVALID_OTP": "رمز التحقق غير صحيح",
		"OTP_EXPIRED": "انتهت صلاحية رمز التحقق، اطلب رمزاً جديداً",
		"INVALID_MOBILE_NUMBER_OR_BIRTH_YEAR": "رقم الهاتف أو سنة الميلاد غير صحيحة",
		"NOT_SUBSCRIBED": "هذا الرقم غير مشترك في الخدمة",
		"CHECK_BANK_ACCOUNT": "تحقق من رصيد حسابك المصرفي",
		"NOT_ALLOWED_AMOUNT": "المبلغ غير مسموح لهذه الخدمة",
		"AMOUNT_EXCEEDED_MAXIMUM": "المبلغ أكبر من الحد المسموح للعملية الواحدة",
		"ALLOWED_ATTEMPTS_EXCEEDED": "تجاوزت عدد المحاولات المسموح، حاول لاحقاً",
		"OTP_WAIT_BEFORE_RESNED": "انتظر قليلاً قبل طلب رمز جديد",
		"SERVICE_NOT_AVAILABLE": "الخدمة غير متاحة حالياً، جرّب طريقة دفع أخرى",
		"INVALID_PROCESS_ID": "انتهت العملية، ابدأ الدفع من جديد",
		"CURRENCY_NOT_SUPPORTED": "الدفع بالدولار غير مفعّل لدى المتجر",
	}
	return msgs.get(code) or message or _("تعذر إتمام الدفع")


def _hash_ok(params, fields):
	"""Plutu callback check, same as the official PHP SDK: whitelisted params in received order,
	http_build_query, HMAC-SHA256 with the secret key, upper-case hex."""
	secret = _keys()[2]
	got = params.get("hashed") or ""
	if not secret or not got:
		return False
	data = urlencode([(k, v) for k, v in params.items() if k in fields])
	mine = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest().upper()
	return hmac.compare_digest(mine, got)


def _demo_sig(name):
	return hmac.new(frappe.local.conf.get("encryption_key", "pb").encode(), name.encode(), hashlib.sha256).hexdigest()[:24]


# ---------------------------------------------------------------- helpers
def _pay_doc(name):
	pba._require_login()
	doc = frappe.get_doc("PersBuilds Web Payment", name)
	if doc.user != frappe.session.user and not pba._is_admin():
		frappe.throw(_("لا يمكنك الوصول لهذه العملية"), frappe.PermissionError)
	return doc


def _log(doc, text):
	doc.db_set("log", ((doc.log or "") + f"{now_datetime():%Y-%m-%d %H:%M:%S} {text}\n")[-6000:], update_modified=False)


def _pay_dict(doc):
	return {
		"id": doc.name,
		"status": doc.status,
		"method": doc.method,
		"method_label": LABEL.get(doc.method),
		"amount": flt(doc.amount),
		"is_deposit": cint(doc.is_deposit),
		"demo": cint(doc.demo),
		"sales_order": doc.sales_order,
		"transaction_id": doc.transaction_id,
		"receipt": bool(doc.receipt),
		"build": doc.web_build,
	}


def _mark_paid(doc, transaction_id=None, extra=""):
	if doc.status == "Paid":
		return
	doc.db_set({"status": "Paid", "transaction_id": str(transaction_id or doc.transaction_id or ""), "paid_on": now_datetime()})
	_log(doc, f"paid {transaction_id or ''} {extra}")
	frappe.get_doc("Sales Order", doc.sales_order).add_comment(
		"Comment",
		f"دفع إلكتروني من موقع PersBuilds: {LABEL.get(doc.method)}، {flt(doc.amount):,.2f} د.ل"
		+ (" (عربون)" if doc.is_deposit else "")
		+ (f"، رقم العملية {transaction_id}" if transaction_id else "")
		+ (" — وضع تجريبي، لم تُحصّل أموال" if doc.demo else ""),
	)
	if not doc.demo:
		_draft_payment_entry(doc, CARD_MODE)


def _draft_payment_entry(doc, mode):
	"""Draft (not submitted) receipt in AlRaqeem; accounts staff check and submit it."""
	try:
		with pba.as_admin():
			_make_pe(doc, mode)
	except Exception:
		frappe.log_error(title=f"PersBuilds payment entry for {doc.name}")


def _make_pe(doc, mode):
	account = frappe.db.get_value("Mode of Payment Account", {"parent": mode, "company": pba.COMPANY}, "default_account")
	if not account:
		return
	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": pba.COMPANY,
			"mode_of_payment": mode,
			"party_type": "Customer",
			"party": doc.customer,
			"posting_date": nowdate(),
			"paid_to": account,
			"paid_amount": flt(doc.amount),
			"received_amount": flt(doc.amount),
			"reference_no": doc.transaction_id or doc.name,
			"reference_date": nowdate(),
			"remarks": f"PersBuilds website {LABEL.get(doc.method)} {doc.name} for {doc.sales_order}",
		}
	)
	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.flags.ignore_permissions = True
	pe.insert()
	doc.db_set("payment_entry", pe.name)


def _bank_accounts():
	rows = frappe.get_all(
		"Bank Account",
		filters={"company": pba.COMPANY, "is_company_account": 1, "disabled": 0},
		fields=["bank", "account_name", "bank_account_no", "iban"],
	)
	return [{"bank": r.bank, "name": r.account_name or pba.COMPANY, "number": r.bank_account_no, "iban": r.iban} for r in rows]


# ---------------------------------------------------------------- client API
@frappe.whitelist()
def options(build):
	"""what the checkout page needs: order total, methods, bank accounts, test-mode flag"""
	b = pba._own_build(build)
	total = flt(frappe.db.get_value("Sales Order", b.sales_order, "grand_total")) if b.sales_order else flt(b.total_lyd)
	live = _live()
	methods = []
	for code, label, group, online in METHODS:
		ok, why = True, ""
		if code == "tlync" and live and not _public_site():
			ok, why = False, "يحتاج الموقع لعنوان عام على الإنترنت"
		methods.append({"code": code, "label": label, "group": group, "online": online, "enabled": ok, "note": why})
	return {
		"build": pba._build_dict(b),
		"total": total,
		"deposit_pct": int(DEPOSIT * 100),
		"usd_rate": USD_RATE,
		"test_mode": not live,
		"methods": methods,
		"banks": _bank_accounts(),
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=60 * 10)
def start(build, method, part="full", mobile=None, birth_year=None):
	if method not in LABEL:
		frappe.throw(_("طريقة دفع غير معروفة"))
	b = pba._own_build(build)
	if not b.sales_order:
		pba.send_order(b.name)
		b.reload()
	paid = frappe.db.exists("PersBuilds Web Payment", {"web_build": b.name, "status": ["in", ["Paid", "Awaiting Check", "Pay On Delivery"]]})
	if paid:
		frappe.throw(_("تم اختيار طريقة الدفع لهذا الطلب مسبقاً"))

	total = flt(frappe.db.get_value("Sales Order", b.sales_order, "grand_total"))
	deposit = part == "deposit" and method not in ("cod", "cheque")
	amount = round(total * DEPOSIT, 2) if deposit else round(total, 2)
	if amount <= 0:
		frappe.throw(_("قيمة الطلب غير صحيحة"))
	mobile = re.sub(r"\D", "", mobile or "")
	if mobile.startswith("218"):
		mobile = "0" + mobile[3:]
	if method in ("sadad", "edfali", "tlync") and not re.fullmatch(r"09[1-6]\d{7}", mobile):
		frappe.throw(_("اكتب رقم الهاتف بالشكل 09XXXXXXXX"))
	if method == "sadad":
		if not re.fullmatch(r"09[13]\d{7}", mobile):
			frappe.throw(_("سداد يعمل مع أرقام 091 و093 فقط"))
		y = cint(birth_year)
		if y < 1940 or y > now_datetime().year - 12:
			frappe.throw(_("سنة الميلاد غير صحيحة"))

	doc = frappe.get_doc(
		{
			"doctype": "PersBuilds Web Payment",
			"web_build": b.name,
			"sales_order": b.sales_order,
			"customer": b.customer,
			"user": b.user,
			"method": method,
			"amount": amount,
			"is_deposit": 1 if deposit else 0,
			"demo": 0 if (method not in ONLINE or _live()) else 1,
			"payer_mobile": mobile or None,
			"status": "Pending",
		}
	)
	doc.insert(ignore_permissions=True)
	doc.db_set("invoice_no", f"{doc.name}-{frappe.generate_hash(length=6)}")
	out = {"payment": None, "next": None}

	if method in ("cod", "cheque"):
		doc.db_set("status", "Pay On Delivery")
		_log(doc, "pay on delivery")
		out["next"] = "done"
	elif method == "transfer":
		doc.db_set("status", "Awaiting Receipt")
		out["next"] = "receipt"
		out["banks"] = _bank_accounts()
	elif method in ("sadad", "edfali"):
		if doc.demo:
			doc.db_set("process_id", "TEST-" + frappe.generate_hash(length=8))
		else:
			gw = "sadadapi" if method == "sadad" else "edfali"
			data = {"mobile_number": mobile, "amount": f"{amount:.2f}"}
			if method == "sadad":
				data["birth_year"] = str(cint(birth_year))
			res = _plutu(gw, "verify", data)
			doc.db_set("process_id", str(res.get("process_id")))
		_log(doc, f"otp sent to {mobile}")
		out["next"] = "otp"
		out["code_length"] = 6 if method == "sadad" else 4
	else:  # redirect methods
		base = _site_base()
		return_url = f"{base}/api/method/raqim_sales.persbuilds_pay.plutu_return?p={doc.name}"
		if doc.demo:
			url = f"{base}/PayTest.html?" + urlencode({"p": doc.name, "s": _demo_sig(doc.name), "m": method, "a": f"{amount:.2f}"})
		else:
			data = {"amount": f"{amount:.2f}", "invoice_no": doc.invoice_no, "return_url": return_url, "lang": "ar",
				"customer_ip": frappe.local.request_ip}
			if method == "mpgs":
				data["amount"] = f"{amount / USD_RATE:.2f}"
			if method == "tlync":
				data.update({"mobile_number": mobile, "callback_url": f"{base}/api/method/raqim_sales.persbuilds_pay.plutu_callback",
					"email": frappe.session.user})
			res = _plutu(method, "confirm", data)
			url = res.get("redirect_url")
			if not url:
				frappe.throw(_("لم تُرجع بوابة الدفع رابط الدفع"))
		_log(doc, f"redirect {method}")
		out["next"] = "redirect"
		out["redirect_url"] = url
	doc.reload()
	out["payment"] = _pay_dict(doc)
	return out


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=12, seconds=60 * 10)
def confirm_otp(payment, code):
	doc = _pay_doc(payment)
	if doc.status != "Pending" or doc.method not in ("sadad", "edfali"):
		frappe.throw(_("هذه العملية لا تنتظر رمز تحقق"))
	code = re.sub(r"\D", "", code or "")
	need = 6 if doc.method == "sadad" else 4
	if len(code) != need:
		frappe.throw(_("رمز التحقق يتكون من {0} أرقام").format(need))
	if doc.demo:
		if code != ("111111" if doc.method == "sadad" else "1111"):
			_log(doc, "test: wrong code")
			frappe.throw(_("رمز التحقق غير صحيح (في الوضع التجريبي استخدم {0})").format("111111" if doc.method == "sadad" else "1111"))
		_mark_paid(doc, "TEST-" + frappe.generate_hash(length=10), "test mode")
	else:
		gw = "sadadapi" if doc.method == "sadad" else "edfali"
		try:
			res = _plutu(gw, "confirm", {"process_id": doc.process_id, "code": code, "amount": f"{flt(doc.amount):.2f}",
				"invoice_no": doc.invoice_no, "customer_ip": frappe.local.request_ip})
		except frappe.ValidationError as e:
			_log(doc, f"confirm failed: {e}")
			raise
		_mark_paid(doc, res.get("transaction_id"))
	doc.reload()
	return _pay_dict(doc)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60 * 10)
def upload_receipt(payment, filename, data):
	doc = _pay_doc(payment)
	if doc.method != "transfer" or doc.status not in ("Awaiting Receipt", "Awaiting Check"):
		frappe.throw(_("هذه العملية لا تحتاج إيصالاً"))
	ext = (filename or "").rsplit(".", 1)[-1].lower()
	if ext not in ("jpg", "jpeg", "png", "webp", "pdf"):
		frappe.throw(_("أرسل صورة (JPG أو PNG) أو ملف PDF"))
	raw = base64.b64decode((data or "").split(",")[-1], validate=False)
	if not raw or len(raw) > 6 * 1024 * 1024:
		frappe.throw(_("حجم الملف يجب ألا يتجاوز 6 ميغابايت"))
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"receipt-{doc.name}.{ext}",
			"content": raw,
			"is_private": 1,
			"attached_to_doctype": "PersBuilds Web Payment",
			"attached_to_name": doc.name,
			"attached_to_field": "receipt",
		}
	)
	f.flags.ignore_permissions = True
	f.insert()
	doc.db_set({"receipt": f.file_url, "status": "Awaiting Check"})
	_log(doc, "receipt uploaded")
	frappe.get_doc("Sales Order", doc.sales_order).add_comment(
		"Comment", f"العميل رفع إيصال حوالة مصرفية بقيمة {flt(doc.amount):,.2f} د.ل ({doc.name}). يرجى التحقق وتسجيل الدفعة."
	)
	_draft_payment_entry(doc, MODE["transfer"])
	doc.reload()
	return _pay_dict(doc)


@frappe.whitelist()
def payment_status(payment):
	return _pay_dict(_pay_doc(payment))


@frappe.whitelist(methods=["POST"])
def test_complete(payment, sig, ok=1):
	"""TEST MODE only: the local test checkout page reports Pay / Cancel."""
	doc = _pay_doc(payment)
	if not doc.demo or not hmac.compare_digest(sig or "", _demo_sig(doc.name)):
		frappe.throw(_("غير مسموح"), frappe.PermissionError)
	if doc.status == "Pending":
		if cint(ok):
			_mark_paid(doc, "TEST-" + frappe.generate_hash(length=10), "test mode")
		else:
			doc.db_set("status", "Cancelled")
			_log(doc, "test: cancelled")
	doc.reload()
	return _pay_dict(doc)


# ---------------------------------------------------------------- Plutu redirects / callbacks
def _by_invoice(invoice_no, fallback=None):
	name = frappe.db.get_value("PersBuilds Web Payment", {"invoice_no": invoice_no}) if invoice_no else None
	return frappe.get_doc("PersBuilds Web Payment", name or fallback) if (name or fallback) else None


def _apply_result(doc, params):
	if doc.status != "Pending":
		return
	if str(params.get("approved")) == "1":
		_mark_paid(doc, params.get("transaction_id"), params.get("payment_method") or params.get("gateway") or "")
	elif params.get("canceled") is not None or str(params.get("approved")) == "0":
		doc.db_set("status", "Cancelled")
		_log(doc, "cancelled at checkout")


@frappe.whitelist(allow_guest=True, methods=["GET"])
def plutu_return(**kw):
	"""customer comes back from the Plutu checkout (local bank cards, MPGS, T-Lync)"""
	params = dict(frappe.request.args.items(multi=False))
	doc = _by_invoice(params.get("invoice_no"))
	ok = False
	if doc and doc.status == "Pending" and doc.name == params.get("p"):
		fields = HASH_FIELDS["tlync_return"] if doc.method == "tlync" else HASH_FIELDS.get(doc.method, [])
		clean = {k: v for k, v in params.items() if k != "p"}
		if _hash_ok(clean, fields):
			ok = True
			if doc.method != "tlync":  # T-Lync money is confirmed by the server callback only
				with pba.as_admin():
					_apply_result(doc, clean)
		else:
			_log(doc, "return hash check FAILED " + json.dumps(params)[:400])
	frappe.db.commit()
	name = doc.name if doc else (params.get("p") or "")
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"{_site_base()}/Checkout.html?payment={name}" + ("" if ok else "&check=1")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def plutu_callback(**kw):
	"""server-to-server T-Lync result (JSON POST)"""
	params = frappe.request.get_json(silent=True) or dict(frappe.form_dict)
	params = {k: ("" if v is None else str(v)) for k, v in params.items() if k != "cmd"}
	doc = _by_invoice(params.get("invoice_no"))
	if not doc:
		return {"ok": False}
	if not _hash_ok(params, HASH_FIELDS["tlync"]):
		_log(doc, "callback hash check FAILED " + json.dumps(params)[:400])
		frappe.db.commit()
		return {"ok": False}
	with pba.as_admin():
		_apply_result(doc, params)
	frappe.db.commit()
	return {"ok": True}
