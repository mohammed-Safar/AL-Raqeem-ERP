# Copyright (c) 2026, raqeem and contributors
# For license information, please see license.txt
"""RAQEEM cheque management (شيكات): received and issued cheques, from the day they change
hands until the bank pays them, bounces them or they are handed back.

Every step that moves money posts a submitted Journal Entry, so invoices, party balances,
the General Ledger, Accounts Receivable/Payable and Bank Reconciliation all stay correct
without any special handling elsewhere.

Postings (H = the company's cheques account, P = the party's receivable/payable account,
B = the company bank account):

	Received cheque                       Issued cheque
	receive    Dr H  / Cr P (customer)    issue      Dr P (supplier) / Cr H
	deposit    no entry, records the bank clear      Dr H / Cr B   (Bank Entry)
	clear      Dr B  / Cr H (Bank Entry)  bounce     Dr H / Cr P   (supplier owed again)
	bounce     Dr P  / Cr H (customer     return     Dr H / Cr P   (cheque taken back)
	           owes again)                represent  Dr P / Cr H
	return     Dr P  / Cr H, or no entry
	           when it had already bounced
	represent  Dr H  / Cr P

The party rows of a bounce or return copy the invoice links of the entry they reverse, as the
entry stands now (Payment Reconciliation may have linked it to invoices since). The invoices
therefore become unpaid again.

ROLLBACK: remove the Raqeem Cheque doctypes and the `raqeem cheques` lines in hooks.py.
The journal entries already posted are ordinary journal entries and stay valid.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, formatdate, getdate, nowdate

INVOICE_FOR = {("Received", "Customer"): "Sales Invoice", ("Issued", "Supplier"): "Purchase Invoice"}

PARTY_NAME_FIELD = {
	"Customer": "customer_name",
	"Supplier": "supplier_name",
	"Employee": "employee_name",
	"Shareholder": "title",
}

# (cheque type, action) -> (statuses it may start from, status it ends in)
TRANSITIONS = {
	("Received", "deposit"): (("In Hand",), "Deposited"),
	("Received", "clear"): (("In Hand", "Deposited"), "Cleared"),
	("Received", "bounce"): (("Deposited",), "Bounced"),
	("Received", "return"): (("In Hand", "Bounced"), "Returned"),
	("Received", "represent"): (("Bounced",), "Deposited"),
	("Issued", "clear"): (("Issued",), "Cleared"),
	("Issued", "bounce"): (("Issued",), "Bounced"),
	("Issued", "return"): (("Issued", "Bounced"), "Returned"),
	("Issued", "represent"): (("Bounced",), "Issued"),
}

ACTION_LABELS = {
	"receive": "Received",
	"issue": "Issued",
	"deposit": "Deposited",
	"clear": "Cleared",
	"bounce": "Bounced",
	"return": "Returned",
	"represent": "Re-presented",
}

# Fields an action fills, cleared again when that action is undone.
ACTION_FIELDS = {
	"deposit": ("deposit_date",),
	"clear": ("clearance_date",),
	"bounce": ("bounce_date", "bounce_reason"),
	"return": ("return_date",),
}

OPEN_STATUSES = ("In Hand", "Deposited", "Issued")


class RaqeemCheque(Document):
	# ------------------------------------------------------------------ validation
	def _validate_links(self):
		# the invoice type follows from cheque type + party type; Frappe checks links before
		# `validate`, so it is set here for documents made through the API or an import
		self.reference_doctype = INVOICE_FOR.get((self.cheque_type, self.party_type)) or ""
		if not self.reference_doctype:
			self.reference_name = None
		super()._validate_links()

	def validate(self):
		if self.docstatus == 0:
			self.status = "Draft"
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero."))
		self.cheque_no = (self.cheque_no or "").strip()
		self.set_party_details()
		self.set_accounts()
		self.validate_invoice()
		self.validate_duplicate()

	def set_party_details(self):
		if self.party_type not in PARTY_NAME_FIELD:
			frappe.throw(_("Party Type must be one of {0}.").format(", ".join(PARTY_NAME_FIELD)))
		if not frappe.db.exists(self.party_type, self.party):
			frappe.throw(_("{0} {1} does not exist.").format(_(self.party_type), self.party))
		self.party_name = frappe.db.get_value(self.party_type, self.party, PARTY_NAME_FIELD[self.party_type]) or self.party
		self.reference_doctype = INVOICE_FOR.get((self.cheque_type, self.party_type)) or ""
		if not self.reference_doctype:
			self.reference_name = None

	def set_accounts(self):
		from erpnext.accounts.party import get_party_account

		from raqim_sales.cheques_setup import get_holding_account

		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.currency = company_currency
		if self.docstatus == 0:
			self.party_account = get_party_account(self.party_type, self.party, self.company)
		if not self.party_account:
			frappe.throw(_("Set a default receivable/payable account for {0} {1} or company {2}.").format(
				_(self.party_type), self.party, self.company))
		self.holding_account = self.holding_account or get_holding_account(self.company, self.cheque_type)

		for field in ("party_account", "holding_account", "bank_account"):
			account = self.get(field)
			if not account:
				continue
			company, currency, is_group = frappe.get_cached_value("Account", account, ["company", "account_currency", "is_group"])
			label = _(self.meta.get_label(field))
			if company != self.company:
				frappe.throw(_("{0} {1} does not belong to company {2}.").format(label, account, self.company))
			if is_group:
				frappe.throw(_("{0} {1} is a group account.").format(label, account))
			if currency and currency != company_currency:
				frappe.throw(_("{0} {1} is in {2}. Cheques are recorded in the company currency ({3}) only.").format(
					label, account, currency, company_currency))
		if self.bank_account and frappe.get_cached_value("Account", self.bank_account, "account_type") not in ("Bank", "Cash"):
			frappe.throw(_("Company Bank Account must be an account of type Bank."))
		if self.cheque_type == "Issued" and not self.bank_account:
			frappe.throw(_("Select the Company Bank Account this cheque is drawn on."))

	def validate_invoice(self):
		self.invoice_outstanding = 0
		if not self.reference_name:
			return
		dt = self.reference_doctype
		party_field, account_field = ("customer", "debit_to") if dt == "Sales Invoice" else ("supplier", "credit_to")
		inv = frappe.db.get_value(dt, self.reference_name,
			["docstatus", "company", party_field, account_field, "outstanding_amount"], as_dict=True)
		if not inv or inv.docstatus != 1:
			frappe.throw(_("{0} {1} is not submitted.").format(_(dt), self.reference_name))
		if inv.company != self.company or inv.get(party_field) != self.party:
			frappe.throw(_("{0} {1} belongs to another party or company.").format(_(dt), self.reference_name))
		self.party_account = inv.get(account_field)
		self.invoice_outstanding = flt(inv.outstanding_amount)
		if self.docstatus == 0 and flt(self.amount) > flt(inv.outstanding_amount) + 0.001:
			frappe.throw(_("The cheque amount {0} is more than the outstanding amount {1} of {2}. Clear the invoice field to record it on the party's account instead.").format(
				frappe.format_value(self.amount, {"fieldtype": "Currency", "options": self.currency}),
				frappe.format_value(inv.outstanding_amount, {"fieldtype": "Currency", "options": self.currency}),
				self.reference_name))

	def validate_duplicate(self):
		filters = {"name": ["!=", self.name], "docstatus": ["<", 2], "cheque_no": self.cheque_no, "cheque_type": self.cheque_type}
		if self.cheque_type == "Issued":
			filters["bank_account"] = self.bank_account
		else:
			filters.update({"party_type": self.party_type, "party": self.party, "drawn_on_bank": self.drawn_on_bank or ""})
		other = frappe.db.get_value("Raqeem Cheque", filters)
		if other:
			frappe.throw(_("Cheque No {0} is already recorded in {1}.").format(self.cheque_no, frappe.utils.get_link_to_form("Raqeem Cheque", other)))

	# ------------------------------------------------------------------ submit / cancel
	def before_submit(self):
		self.status = "In Hand" if self.cheque_type == "Received" else "Issued"

	def on_submit(self):
		key = "receive" if self.cheque_type == "Received" else "issue"
		refs = [(self.reference_doctype, self.reference_name, flt(self.amount))] if self.reference_name else []
		je = self.make_journal_entry(key, self.posting_date, self.party_rows("settle", refs, strict=True))
		self.add_log(key, self.posting_date, "Draft", self.status, je, "settle", self.remarks)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry", "Journal Entry")
		for row in reversed(self.history):
			if row.journal_entry and not row.undone:
				cancel_journal_entry(row.journal_entry)
		self.db_set("status", "Cancelled")

	# ------------------------------------------------------------------ actions
	@frappe.whitelist()
	def run_action(self, action, date=None, bank_account=None, reason=None):
		self.check_permission("submit")
		if self.docstatus != 1:
			frappe.throw(_("Submit the cheque first."))
		if (self.cheque_type, action) not in TRANSITIONS:
			frappe.throw(_("Unknown action."))
		allowed, to_status = TRANSITIONS[(self.cheque_type, action)]
		# lock the row so two people cannot act on the same cheque at once
		from_status = frappe.db.get_value(self.doctype, self.name, "status", for_update=True)
		if from_status not in allowed:
			frappe.throw(_("A cheque that is {0} cannot be marked {1}.").format(_(from_status), _(ACTION_LABELS[action])))
		date = getdate(date or nowdate())
		self.validate_action_date(date)

		if bank_account:
			self.bank_account = bank_account
		if action in ("deposit", "clear", "represent") and self.cheque_type == "Received" and not self.bank_account:
			frappe.throw(_("Select the Company Bank Account."))
		if bank_account:
			self.set_accounts()

		posting, rows = None, None
		if action == "clear":
			posting, rows = "bank", self.bank_rows()
		elif action == "bounce" or (action == "return" and from_status != "Bounced"):
			posting, rows = "unsettle", self.party_rows("unsettle", self.refs_of_last("settle"))
		elif action == "represent":
			posting, rows = "settle", self.party_rows("settle", self.refs_of_last("unsettle"))

		je = self.make_journal_entry(action, date, rows) if rows else None

		updates = {"status": to_status, "bank_account": self.bank_account}
		if action in ("deposit", "represent"):
			updates["deposit_date"] = date
		elif action == "clear":
			updates["clearance_date"] = date
		elif action == "bounce":
			updates.update(bounce_date=date, bounce_reason=reason)
		elif action == "return":
			updates["return_date"] = date
			if reason:
				updates["bounce_reason"] = reason
		self.db_set(updates)
		self.add_log(action, date, from_status, to_status, je, posting, reason)
		self.notify_update()
		return to_status

	@frappe.whitelist()
	def undo_last(self):
		"""Reverse the latest step (its journal entry is cancelled). The first step, receiving or
		issuing the cheque, is reversed by cancelling the cheque itself."""
		self.check_permission("cancel")
		frappe.db.get_value(self.doctype, self.name, "status", for_update=True)
		live = [row for row in self.history if not row.undone]
		if len(live) < 2:
			frappe.throw(_("Nothing to undo. To reverse receiving or issuing the cheque, cancel it."))
		row = live[-1]
		if row.journal_entry:
			cancel_journal_entry(row.journal_entry)
		updates = {"status": row.from_status}
		for field in ACTION_FIELDS.get(row.action_key, ()):
			updates[field] = None
		self.db_set(updates)
		row.db_set("undone", 1)
		self.add_comment("Info", _("Undid: {0} ({1})").format(_(row.action), formatdate(row.date)))
		self.notify_update()
		return row.from_status

	def validate_action_date(self, date):
		if date > getdate(nowdate()):
			frappe.throw(_("The date cannot be in the future."))
		last = max([getdate(r.date) for r in self.history if not r.undone] or [getdate(self.posting_date)])
		if date < last:
			frappe.throw(_("The date cannot be before {0}, the date of the previous step.").format(formatdate(last)))

	# ------------------------------------------------------------------ postings
	def party_rows(self, direction, refs, strict=False):
		"""Holding-account row plus party rows for `direction` ("settle" = the cheque pays the
		party's balance, "unsettle" = it no longer does). `refs` are (doctype, name, amount)
		invoice links; whatever they do not cover is posted on account."""
		received = self.cheque_type == "Received"
		settle_side = "credit" if received else "debit"
		other = {"credit": "debit", "debit": "credit"}
		party_side = settle_side if direction == "settle" else other[settle_side]
		total = flt(self.amount)

		rows, left = [], total
		for dt, name, amount in refs:
			amount = min(flt(amount), left)
			if direction == "settle":
				outstanding = flt(frappe.db.get_value(dt, name, "outstanding_amount"))
				if strict and amount > outstanding + 0.001:
					frappe.throw(_("{0} {1} has only {2} outstanding.").format(_(dt), name, outstanding))
				amount = min(amount, max(outstanding, 0))
			if amount <= 0:
				continue
			rows.append(self.party_row(party_side, amount, dt, name))
			left -= amount
		if flt(left, 2) > 0:
			row = self.party_row(party_side, left)
			if party_side == settle_side and self.party_type in ("Customer", "Supplier"):
				row["is_advance"] = "Yes"
			rows.append(row)
		rows.append({"account": self.holding_account, other[party_side] + "_in_account_currency": total})
		return rows

	def party_row(self, side, amount, reference_type=None, reference_name=None):
		return {
			"account": self.party_account,
			"party_type": self.party_type,
			"party": self.party,
			side + "_in_account_currency": amount,
			"reference_type": reference_type,
			"reference_name": reference_name,
		}

	def bank_rows(self):
		if not self.bank_account:
			frappe.throw(_("Select the Company Bank Account."))
		amount = flt(self.amount)
		bank, holding = ("debit", "credit") if self.cheque_type == "Received" else ("credit", "debit")
		return [
			{"account": self.bank_account, bank + "_in_account_currency": amount},
			{"account": self.holding_account, holding + "_in_account_currency": amount},
		]

	def refs_of_last(self, posting):
		"""Invoice links of the latest live entry of kind `posting`, as that entry stands now."""
		row = next((r for r in reversed(self.history) if r.posting == posting and not r.undone and r.journal_entry), None)
		if not row:
			return []
		side = "credit" if (self.cheque_type == "Received") == (posting == "settle") else "debit"
		lines = frappe.get_all(
			"Journal Entry Account",
			filters={"parent": row.journal_entry, "account": self.party_account, "party": self.party,
				"reference_type": ["in", ["Sales Invoice", "Purchase Invoice"]]},
			fields=["reference_type", "reference_name", f"{side}_in_account_currency as amount"],
			order_by="idx",
		)
		return [(d.reference_type, d.reference_name, d.amount) for d in lines if flt(d.amount) > 0]

	def make_journal_entry(self, action, date, rows):
		je = frappe.new_doc("Journal Entry")
		je.update({
			"voucher_type": "Bank Entry" if any(r["account"] == self.bank_account for r in rows) else "Journal Entry",
			"company": self.company,
			"posting_date": date,
			"cheque_no": self.cheque_no,
			"cheque_date": self.cheque_date,
			"raqeem_cheque": self.name,
			"user_remark": _("Cheque {0} ({1}) {2} - {3}").format(
				self.cheque_no, self.name, _(ACTION_LABELS[action]).lower(), self.party_name),
		})
		for row in rows:
			je.append("accounts", row)
		je.flags.ignore_permissions = True
		frappe.flags.raqeem_cheque_action = True
		try:
			je.insert()
			je.submit()
		finally:
			frappe.flags.raqeem_cheque_action = False
		if action == "clear":
			# the bank has paid: mark the entry cleared for Bank Reconciliation
			je.db_set("clearance_date", date)
		return je.name

	def add_log(self, action, date, from_status, to_status, journal_entry, posting, remarks=None):
		row = self.append("history", {
			"date": date,
			"action": ACTION_LABELS[action],
			"action_key": action,
			"from_status": from_status,
			"to_status": to_status,
			"journal_entry": journal_entry,
			"posting": posting or "",
			"user": frappe.session.user,
			"remarks": remarks,
		})
		row.db_insert()


def cancel_journal_entry(name):
	je = frappe.get_doc("Journal Entry", name)
	if je.docstatus != 1:
		return
	je.flags.ignore_permissions = True
	frappe.flags.raqeem_cheque_action = True
	try:
		je.cancel()
	finally:
		frappe.flags.raqeem_cheque_action = False


# ---------------------------------------------------------------------- hooks
def guard_journal_entry_cancel(doc, method=None):
	"""Journal Entry before_cancel: an entry made by a cheque is reversed from the cheque."""
	if doc.get("raqeem_cheque") and not frappe.flags.raqeem_cheque_action:
		frappe.throw(_("This entry was made by cheque {0}. Use Undo Last Step or Cancel on the cheque instead.").format(
			frappe.utils.get_link_to_form("Raqeem Cheque", doc.raqeem_cheque)))


@frappe.whitelist()
def get_party_details(party_type, party, company):
	from erpnext.accounts.party import get_party_account

	frappe.has_permission("Raqeem Cheque", "read", throw=True)
	if party_type not in PARTY_NAME_FIELD or not party:
		return {}
	return {
		"party_name": frappe.db.get_value(party_type, party, PARTY_NAME_FIELD[party_type]),
		"party_account": get_party_account(party_type, party, company) if company else None,
	}


def send_due_reminders():
	"""Daily: remind accounts users of open cheques due in 3 days and due today."""
	from frappe.desk.doctype.notification_log.notification_log import make_notification_logs

	today = getdate(nowdate())
	cheques = frappe.get_all(
		"Raqeem Cheque",
		filters={"docstatus": 1, "status": ["in", OPEN_STATUSES], "cheque_date": ["in", [today, add_days(today, 3)]]},
		fields=["name", "cheque_type", "cheque_no", "cheque_date", "party_name", "amount", "currency", "status", "company"],
	)
	if not cheques:
		return
	users = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["Accounts Manager", "Accounts User"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	users = [u for u in users if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")]
	if not users:
		return
	for c in cheques:
		amount = frappe.format_value(c.amount, {"fieldtype": "Currency", "options": c.currency})
		when = _("today") if getdate(c.cheque_date) == today else _("in 3 days")
		if c.cheque_type == "Received":
			subject = _("Cheque {0} from {1} ({2}) is due {3}.").format(c.cheque_no, c.party_name, amount, when)
			if c.status == "In Hand":
				subject += " " + _("It has not been deposited yet.")
		else:
			subject = _("Cheque {0} issued to {1} ({2}) is due {3}. Make sure the bank account has enough funds.").format(
				c.cheque_no, c.party_name, amount, when)
		make_notification_logs(
			{"type": "Alert", "document_type": "Raqeem Cheque", "document_name": c.name, "subject": subject, "from_user": "Administrator"},
			users,
		)
