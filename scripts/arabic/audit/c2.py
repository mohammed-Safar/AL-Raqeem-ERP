import json, re, csv, collections, sys
d=json.load(open('dict_ar.json'))
U=json.load(open('universe_code.json')); DB=json.load(open('universe_db.json'))
ours={r[0] for r in csv.reader(open('../../../raqim_sales/translations/ar.csv')) if len(r)>1}
app_of={}
for app in ['frappe','erpnext','raqim_sales','print_designer','crm','hrms']:
    for p,m,c in U[app]:
        if isinstance(m,str): app_of.setdefault(m,app)
for k in DB: app_of.setdefault(k,'db')
R=[ # (name, english regex, acceptable arabic regex, apps or None)
('Item', r'\bItems?\b', r'صنف|أصناف|اصناف', ('erpnext',)),
('Submit', r'\b[Ss]ubmit(ted|ting|s)?\b', r'اعتم|معتمد|يُعتمد|تُعتمد', None),
('Delivery Note', r'\bDelivery Notes?\b', r'إذن تسليم|إذن التسليم|أذون التسليم|أذونات التسليم|أذون تسليم', None),
('Sales Order', r'\bSales Orders?\b', r'أمر بيع|أمر البيع|أوامر البيع|أوامر بيع', None),
('Purchase Order', r'\bPurchase Orders?\b', r'أمر شراء|أمر الشراء|أوامر الشراء|أوامر شراء', None),
('Purchase Receipt', r'\bPurchase Receipts?\b', r'إيصال استلام|إيصال الاستلام|إيصالات الاستلام|إيصالات استلام', None),
('Payment Entry', r'\bPayment Entr(y|ies)\b', r'سند دفع|سند الدفع|سندات الدفع|سندات دفع', None),
('Journal Entry', r'\bJournal Entr(y|ies)\b', r'قيد يومية|قيد اليومية|قيود اليومية|قيود يومية', None),
('Stock Entry', r'\bStock Entr(y|ies)\b', r'حركة مخزون|حركة المخزون|حركات المخزون|حركات مخزون', None),
('Stock', r'\bStock\b', r'مخزون|مخزن|مخزني', None),
('Warehouse', r'\bWarehouses?\b', r'مستودع', None),
('BOM', r'\bBOMs?\b', r'قائمة المواد|قوائم المواد|قائمة مواد', None),
('Quotation', r'\bQuotations?\b', r'عرض سعر|عرض السعر|عروض الأسعار|عروض أسعار|عروض السعر|عرض أسعار', None),
('Customer', r'\bCustomers?\b', r'عميل|عملاء', None),
('Supplier', r'\bSuppliers?\b', r'مورد|مورّد|مورِّد', None),
('Invoice', r'\bInvoices?\b', r'فاتورة|فواتير|فوترة', None),
('Draft', r'\bDrafts?\b', r'مسودة|مسودات', None),
('UOM', r'\bUOMs?\b', r'وحدة القياس|وحدات القياس|وحدة قياس|وحدات قياس', None),
('Cost Center', r'\bCost Cent(er|re)s?\b', r'مركز التكلفة|مراكز التكلفة|مركز تكلفة', None),
('Dashboard', r'\bDashboards?\b', r'لوحة المعلومات|لوحات المعلومات|لوحة معلومات', None),
('Work Order', r'\bWork Orders?\b', r'أمر عمل|أمر العمل|أوامر العمل|أوامر عمل', None),
('Material Request', r'\bMaterial Requests?\b', r'طلب مواد|طلب المواد|طلبات المواد|طلبات مواد', None),
('Serial No', r'\bSerial (No|Number)s?\b', r'تسلسلي', None),
('Batch', r'\bBatch(es)?\b', r'دفعة|دفعات', ('erpnext',)),
('Depreciation', r'\bDepreciat', r'إهلاك|اهلاك|يُهلك|مهلك|مُهلك', None),
('Asset', r'\bAssets?\b', r'أصل|أصول|الأصل', ('erpnext',)),
('Employee', r'\bEmployees?\b', r'موظف', None),
('Workspace', r'\bWorkspaces?\b', r'مساحة العمل|مساحات العمل|مساحة عمل', None),
('Role', r'\bRoles?\b', r'دور|أدوار', None),
('Permission', r'\bPermissions?\b', r'صلاحي', None),
('Tax', r'\bTax(es)?\b', r'ضريب|ضرائب', None),
('Pricing Rule', r'\bPricing Rules?\b', r'قاعدة التسعير|قواعد التسعير|قاعدة تسعير', None),
('Price List', r'\bPrice Lists?\b', r'قائمة الأسعار|قوائم الأسعار|قائمة أسعار', None),
('Valuation Rate', r'\bValuation Rate\b', r'سعر التقييم', None),
('Fiscal Year', r'\bFiscal Years?\b', r'سنة مالية|السنة المالية|سنوات مالية|السنوات المالية', None),
('Mode of Payment', r'\bModes? of Payment\b', r'طريقة الدفع|طرق الدفع|طريقة دفع', None),
('Timesheet', r'\bTimesheets?\b', r'سجل الوقت|سجلات الوقت|سجل وقت', None),
('Attendance', r'\bAttendance\b', r'حضور', None),
('DocType', r'\bDoc[Tt]ypes?\b', r'نوع المستند|أنواع المستندات|نوع مستند|أنواع مستندات|نوع المستندات', None),
('Print Format', r'\bPrint Formats?\b', r'تنسيق الطباعة|تنسيقات الطباعة|تنسيق طباعة', None),
('Letter Head', r'\bLetter ?[Hh]eads?\b', r'ترويس', None),
('Naming Series', r'\bNaming Series\b', r'سلسلة التسمية|سلاسل التسمية|سلسلة تسمية', None),
('Opportunity', r'\bOpportunit(y|ies)\b', r'فرصة|فرص', None),
('Territory', r'\bTerritor(y|ies)\b', r'منطقة|مناطق', None),
('Sales Person', r'\bSales Persons?\b', r'مندوب|مندوبي|مندوبو', None),
('Credit Note', r'\bCredit Notes?\b', r'إشعار دائن|إشعارات دائنة|الإشعار الدائن|إشعار الدائن|الإشعارات الدائنة', None),
('Debit Note', r'\bDebit Notes?\b', r'إشعار مدين|إشعارات مدينة|الإشعار المدين|الإشعارات المدينة', None),
('Grand Total', r'\bGrand Total\b', r'الإجمالي الكلي|إجمالي كلي', None),
('Shift', r'\bShifts?\b', r'وردية|ورديات|الوردي', None),
('Holiday', r'\bHolidays?\b', r'عطلة|عطلات|العطل', None),
('Lead', r'\bLeads?\b', r'عميل محتمل|عملاء محتمل|العملاء المحتمل|العميل المحتمل', ('erpnext','crm')),
('Leave', r'\bLeaves?\b', r'إجاز', ('hrms','raqim_sales')),
('Payment Terms', r'\bPayment Terms?\b', r'شروط الدفع|شرط الدفع', None),
('Outstanding', r'\bOutstanding\b', r'مستحق', None),
('Account', r'\bAccounts?\b', r'حساب', ('erpnext',)),
('Company', r'\bCompan(y|ies)\b', r'شرك', None),
('Project', r'\bProjects?\b', r'مشروع|مشاريع', None),
('Report', r'\bReports?\b', r'تقرير|تقارير', None),
('Discount', r'\bDiscounts?\b', r'خصم|خصوم', None),
('Cancel', r'\bCancel(led|s|ling)?\b', r'إلغاء|ملغ|ألغ|يلغ|تلغ|يُلغ|تُلغ|لغي|الغاء', None),
]
ar=re.compile(r'[؀-ۿ]')
out=collections.defaultdict(list)
for k,app in app_of.items():
    t=d.get(k)
    if not t or not ar.search(t): continue
    for name,en,acc,apps in R:
        if apps and app not in apps: continue
        if re.search(en,k) and not re.search(acc,t):
            out[name].append((app,k,t,k in ours))
tot=0
for name,v in sorted(out.items(), key=lambda x:-len(x[1])):
    print(name,len(v),'ours:',sum(1 for x in v if x[3])); tot+=len(v)
print('total',tot, 'unique', len({x[1] for v in out.values() for x in v}))
json.dump(out,open('glossary_viol.json','w'),ensure_ascii=False,indent=0)
