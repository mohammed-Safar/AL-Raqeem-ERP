// RAQEEM ERPNext Tools — CRM Form Script on CRM Deal (installed by raqim_sales/crm_integration.py
// on every migrate; edit this file, not the CRM Form Script record).
// Adds an "ERPNext" button to the deal's header:
//   • Customer & payments: linked customer, balance due, invoices, orders, payments, purchase history
//     (or, with no customer yet, the matching ERPNext customers to link)
//   • Stock: the deal's products with the quantity in stock per warehouse
class CRMDeal {
	onLoad() {
		if (this.doc.__newDocument) return
		const t = this.rqText()
		this.actions.push({
			group: t.erp,
			buttonLabel: t.erp,
			items: [
				{ label: t.customer, icon: 'users', onClick: () => this.rqCustomer() },
				{ label: t.stock, icon: 'package', onClick: () => this.rqStock() },
				{ label: t.report, icon: 'bar-chart-2', onClick: () => this.rqReport() },
			],
		})
	}

	rqText() {
		const ar = (document.documentElement.getAttribute('lang') || '').startsWith('ar')
		return ar
			? {
					ar, erp: 'ERPNext', customer: 'العميل والمدفوعات', stock: 'المخزون',
					no_customer: 'لا يوجد عميل في ERPNext لهذه الصفقة بعد. سيُنشأ تلقائياً عند ربح الصفقة.',
					matches: 'عملاء موجودون مشابهون — اربط واحداً منهم لتجنّب التكرار:',
					no_matches: 'لا يوجد عميل مشابه في ERPNext.',
					strong: 'نفس البريد أو الهاتف', name: 'نفس الاسم', link: 'ربط', linked: 'تم ربط العميل',
					due: 'المستحق', overdue: 'متأخر السداد', year: 'مشتريات هذه السنة', total: 'إجمالي المشتريات',
					count: 'عدد الفواتير', last: 'آخر شراء',
					invoices: 'الفواتير', orders: 'أوامر البيع', payments: 'المدفوعات', items: 'الأكثر شراءً',
					no: 'الرقم', date: 'التاريخ', amount: 'المبلغ', outstanding: 'المتبقي', status: 'الحالة',
					delivered: 'مُسلّم', billed: 'مُفوتر', mode: 'طريقة الدفع', item: 'الصنف', qty: 'الكمية',
					none: 'لا يوجد', open: 'فتح العميل', product: 'المنتج', needed: 'المطلوب', in_stock: 'المتوفر',
					projected: 'المتوقع', enough: 'متوفر', short: 'غير كافٍ', not_item: 'غير مرتبط بصنف في ERPNext',
					service: 'خدمة (بدون مخزون)', no_products: 'لا توجد منتجات في هذه الصفقة.', close: 'إغلاق',
					no_perm: 'ليست لديك صلاحية لعرض الأصناف.', report: 'تحليل الصفقات', cust: 'العميل', email: 'البريد', phone: 'الهاتف',
				}
			: {
					ar, erp: 'ERPNext', customer: 'Customer & payments', stock: 'Stock',
					no_customer: 'This deal has no ERPNext customer yet. One is created automatically when the deal is won.',
					matches: 'Existing customers that look the same — link one to avoid a duplicate:',
					no_matches: 'No matching customer in ERPNext.',
					strong: 'same email or phone', name: 'same name', link: 'Link', linked: 'Customer linked',
					due: 'Balance due', overdue: 'Overdue', year: 'Bought this year', total: 'Total bought',
					count: 'Invoices', last: 'Last purchase',
					invoices: 'Invoices', orders: 'Sales orders', payments: 'Payments', items: 'Most bought',
					no: 'No.', date: 'Date', amount: 'Amount', outstanding: 'Outstanding', status: 'Status',
					delivered: 'Delivered', billed: 'Billed', mode: 'Mode', item: 'Item', qty: 'Qty',
					none: 'None', open: 'Open customer', product: 'Product', needed: 'Needed', in_stock: 'In stock',
					projected: 'Projected', enough: 'Enough', short: 'Short', not_item: 'Not linked to an ERPNext item',
					service: 'Service (no stock)', no_products: 'This deal has no products.', close: 'Close',
					no_perm: 'You are not allowed to see items.', report: 'Deal analysis', cust: 'Customer', email: 'Email', phone: 'Phone',
				}
	}

	rqEsc(v) {
		return String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
	}
	rqMoney(v, cur) {
		const n = Number(v || 0)
		try {
			return new Intl.NumberFormat(this.rqText().ar ? 'ar-u-nu-latn' : 'en', cur ? { style: 'currency', currency: cur } : { maximumFractionDigits: 2 }).format(n)
		} catch (e) {
			return n.toFixed(2) + (cur ? ' ' + cur : '')
		}
	}
	rqNum(v) {
		return new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(Number(v || 0))
	}
	rqLink(url, text) {
		// inside the RAQEEM desk the link opens in the desk; on its own, in a new tab
		const embedded = document.documentElement.classList.contains('rq-embed')
		return `<a href="${this.rqEsc(url)}"${embedded ? '' : ' target="_blank" rel="noopener"'} style="text-decoration:underline;text-underline-offset:2px">${this.rqEsc(text)}</a>`
	}
	rqTable(head, rows) {
		const t = this.rqText()
		if (!rows.length) return `<p style="opacity:.6;margin:4px 0 14px">${t.none}</p>`
		const th = head.map((h) => `<th style="text-align:start;font-weight:600;padding:6px 8px;opacity:.7;white-space:nowrap">${h}</th>`).join('')
		const tr = rows.map((r) => `<tr style="border-top:1px solid rgba(127,127,127,.18)">${r.map((c) => `<td style="padding:6px 8px;white-space:nowrap">${c}</td>`).join('')}</tr>`).join('')
		return `<div style="overflow-x:auto;margin:0 0 14px"><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`
	}
	rqTitle(text) {
		return `<h4 style="font-weight:600;font-size:14px;margin:10px 0 4px">${text}</h4>`
	}
	rqTiles(tiles) {
		return `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin:4px 0 12px">${tiles
			.map(([label, value, warn]) => `<div style="border:1px solid rgba(127,127,127,.22);border-radius:10px;padding:8px 10px"><div style="font-size:12px;opacity:.65">${label}</div><div style="font-size:16px;font-weight:600;margin-top:2px${warn ? ';color:#dc2626' : ''}">${value}</div></div>`)
			.join('')}</div>`
	}

	async rqCustomer() {
		const t = this.rqText()
		let d
		try {
			d = await call('raqim_sales.crm_integration.deal_erp_summary', { crm_deal: this.doc.name })
		} catch (e) {
			return toast.error(e.messages?.[0] || e.message || String(e))
		}
		if (!d.customer) return this.rqNoCustomer(d)

		const cur = d.currency
		let html = `<p style="margin:0 0 8px">${this.rqLink(d.customer.url, d.customer.customer_name)}</p>`
		if (d.totals) {
			const s = d.totals
			html += this.rqTiles([
				[t.due, this.rqMoney(s.outstanding, cur), s.outstanding > 0],
				[t.overdue, this.rqMoney(s.overdue, cur), s.overdue > 0],
				[t.year, this.rqMoney(s.billed_year, cur)],
				[t.total, this.rqMoney(s.billed, cur)],
				[t.count, this.rqNum(s.invoices)],
				[t.last, this.rqEsc(s.last_purchase || t.none)],
			])
		}
		if (d.invoices) {
			html += this.rqTitle(t.invoices) + this.rqTable(
				[t.no, t.date, t.amount, t.outstanding, t.status],
				d.invoices.map((r) => [this.rqLink(r.url, r.name), this.rqEsc(r.posting_date), this.rqMoney(r.grand_total, r.currency),
					r.outstanding_amount > 0 ? `<b style="color:#dc2626">${this.rqMoney(r.outstanding_amount, r.currency)}</b>` : this.rqMoney(0, r.currency),
					this.rqEsc(__(r.status))]),
			)
		}
		if (d.orders) {
			html += this.rqTitle(t.orders) + this.rqTable(
				[t.no, t.date, t.amount, t.delivered, t.billed, t.status],
				d.orders.map((r) => [this.rqLink(r.url, r.name), this.rqEsc(r.transaction_date), this.rqMoney(r.grand_total, r.currency),
					this.rqNum(r.per_delivered) + '%', this.rqNum(r.per_billed) + '%', this.rqEsc(__(r.status))]),
			)
		}
		if (d.payments) {
			html += this.rqTitle(t.payments) + this.rqTable(
				[t.no, t.date, t.amount, t.mode],
				d.payments.map((r) => [this.rqLink(r.url, r.name), this.rqEsc(r.posting_date), this.rqMoney(r.paid_amount, r.currency), this.rqEsc(r.mode_of_payment || '')]),
			)
		}
		if (d.top_items) {
			html += this.rqTitle(t.items) + this.rqTable(
				[t.item, t.qty, t.amount, t.last],
				d.top_items.map((r) => [this.rqEsc(r.item_name || r.item_code), this.rqNum(r.qty), this.rqMoney(r.amount, cur), this.rqEsc(r.last_date)]),
			)
		}
		createDialog({
			title: t.customer,
			size: '4xl',
			html,
			actions: [{ label: t.close, variant: 'subtle', onClick: (ctx) => (ctx.close ? ctx.close() : ctx()) }],
		})
	}

	rqNoCustomer(d) {
		const t = this.rqText()
		let html = `<p style="margin:0 0 10px">${t.no_customer}</p>`
		const matches = d.matches || []
		if (matches.length) {
			html += `<p style="margin:0 0 6px;font-weight:600">${t.matches}</p>` + this.rqTable(
				[t.cust, t.email, t.phone, ''],
				matches.map((m) => [this.rqLink(`/desk/customer/${encodeURIComponent(m.name)}`, m.customer_name || m.name), this.rqEsc(m.email_id || ''),
					this.rqEsc(m.mobile_no || ''), `<span style="opacity:.7">${m.strength === 'strong' ? t.strong : t.name}</span>`]),
			)
		} else {
			html += `<p style="opacity:.7">${t.no_matches}</p>`
		}
		const actions = d.can_link
			? matches.slice(0, 3).map((m) => ({
					label: `${t.link}: ${m.customer_name || m.name}`,
					variant: 'solid',
					onClick: async (ctx) => {
						try {
							await call('raqim_sales.crm_integration.link_deal_customer', { crm_deal: this.doc.name, customer: m.name })
							toast.success(t.linked)
							ctx.close ? ctx.close() : ctx()
							this.doc.erpnext_customer = m.name
						} catch (e) {
							toast.error(e.messages?.[0] || e.message || String(e))
						}
					},
				}))
			: []
		actions.push({ label: t.close, variant: 'subtle', onClick: (ctx) => (ctx.close ? ctx.close() : ctx()) })
		createDialog({ title: t.customer, size: '3xl', html, actions })
	}

	rqReport() {
		const url = '/desk/query-report/RAQEEM%20Deal%20Analysis'
		if (document.documentElement.classList.contains('rq-embed')) {
			try { return window.parent.rqCrm.toDesk(url) } catch (e) {}
		}
		window.open(url, '_blank', 'noopener')
	}

	async rqStock() {
		const t = this.rqText()
		let d
		try {
			d = await call('raqim_sales.crm_integration.deal_stock', { crm_deal: this.doc.name })
		} catch (e) {
			return toast.error(e.messages?.[0] || e.message || String(e))
		}
		let html
		if (d.no_permission) html = `<p>${t.no_perm}</p>`
		else if (!d.rows.length) html = `<p>${t.no_products}</p>`
		else {
			html = this.rqTable(
				[t.product, t.needed, t.in_stock, t.projected, ''],
				d.rows.map((r) => {
					const name = r.url ? this.rqLink(r.url, r.product) : this.rqEsc(r.product)
					if (!r.item_code) return [name, this.rqNum(r.qty), '', '', `<span style="opacity:.6">${t.not_item}</span>`]
					if (!r.is_stock_item) return [name, this.rqNum(r.qty), '', '', `<span style="opacity:.6">${t.service}</span>`]
					const ok = (r.actual || 0) >= r.qty
					const where = (r.warehouses || []).map((w) => `${this.rqEsc(w.warehouse)}: ${this.rqNum(w.actual_qty)}`).join('<br>')
					return [
						name + (where ? `<div style="font-size:11px;opacity:.6;margin-top:2px">${where}</div>` : ''),
						`${this.rqNum(r.qty)} ${this.rqEsc(r.uom || '')}`,
						this.rqNum(r.actual),
						this.rqNum(r.projected),
						`<b style="color:${ok ? '#16a34a' : '#dc2626'}">${ok ? t.enough : t.short}</b>`,
					]
				}),
			)
		}
		createDialog({
			title: t.stock,
			size: '3xl',
			html,
			actions: [{ label: t.close, variant: 'subtle', onClick: (ctx) => (ctx.close ? ctx.close() : ctx()) }],
		})
	}
}
