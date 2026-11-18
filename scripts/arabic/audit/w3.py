import json, re, csv
from w2 import sub_word
d=json.load(open('dict_ar.json'))
U=json.load(open('universe_code.json')); DB=json.load(open('universe_db.json'))
keys=set(DB)
for app in ['frappe','erpnext','raqim_sales','print_designer','crm','hrms']:
    for p,m,c in U[app]:
        if isinstance(m,str): keys.add(m)
ours={r[0] for r in csv.reader(open('../../../raqim_sales/translations/ar.csv')) if len(r)>1}
done=set(json.load(open('final_fix.json')))|set(json.load(open('final_missing.json')))
R=[
('Template', r'\bTemplates?\b', r'قالب|قوالب'),
('Subcontract', r'[Ss]ubcontract', r'تصنيع خارجي|التصنيع الخارجي|تصنيع وارد|التصنيع الوارد|مصنّع|مصنِّع|مصنَّع'),
('Bank', r'\bBank(s|ing)?\b', r'بنك|بنوك'),
('Voucher', r'\bVouchers?\b', r'سند|سندات|قيد إقفال|قيود'),
('Finished Good', r'\bFinished Goods?\b', r'نهائي'),
('Repost', r'\bRepost', r'ترحيل'),
('Posting Date', r'\bPosting Date\b', r'تاريخ الترحيل|تاريخ ترحيل'),
('Purchase Invoice', r'\bPurchase Invoices?\b', r'مشتريات'),
('Sales Invoice', r'\bSales Invoices?\b', r'فاتورة مبيعات|فاتورة المبيعات|فواتير المبيعات|فواتير مبيعات'),
('Stock Reconciliation', r'\bStock Reconciliations?\b', r'تسوية'),
('Landed Cost', r'\bLanded Cost\b', r'واصلة'),
('Party', r'\bPart(y|ies)\b', r'طرف|أطراف|جهات خارجية|الجهات الخارجية'),
('Closing', r'\b(Period Closing|Stock Closing|Closing Balance|Closing Account|Closing Stock|Closing Entry)\b', r'إقفال|ختامي|إغلاق نقطة البيع'),
('Opening Stock', r'\bOpening (Stock|Balance|Entry|Invoice|Accumulated)\b', r'افتتاح|فتح نقطة البيع'),
('Scrap', r'\bScrap', r'خرد|خردة|تخريد'),
('Ledger', r'\bLedgers?\b', r'دفتر|دفاتر'),
('Raw Material', r'\bRaw Materials?\b', r'خام'),
('Pick List', r'\bPick Lists?\b', r'قائمة الالتقاط|قوائم الالتقاط|قائمة التقاط'),
('Packing Slip', r'\bPacking Slips?\b', r'قائمة التعبئة|قوائم التعبئة|قائمة تعبئة'),
('Job Card', r'\bJob Cards?\b', r'بطاقة عمل|بطاقة العمل|بطاقات العمل|بطاقات عمل'),
('Quality Inspection', r'\bQuality Inspections?\b', r'فحص الجودة|فحوص الجودة|فحوصات الجودة|فحص جودة'),
('Production Plan', r'\bProduction Plans?\b', r'خطة الإنتاج|خطط الإنتاج|خطة إنتاج'),
('Workstation', r'\bWorkstations?\b', r'محطة العمل|محطات العمل|محطة عمل'),
('Sales Partner', r'\bSales Partners?\b', r'شريك المبيعات|شركاء المبيعات|شريك مبيعات'),
('Exchange Rate', r'\bExchange Rates?\b', r'سعر الصرف|أسعار الصرف|سعر صرف'),
('Payment Request', r'\bPayment Requests?\b', r'طلب دفع|طلب الدفع|طلبات الدفع|طلبات دفع'),
('Supplier Quotation', r'\bSupplier Quotations?\b', r'عرض سعر مورد|عرض سعر المورد|عروض أسعار الموردين|عرض أسعار'),
('Request for Quotation', r'\bRequest for Quotations?\b', r'طلب عرض سعر|طلب عرض السعر|طلبات عروض الأسعار|طلب عروض'),
('Credit Limit', r'\bCredit Limits?\b', r'الحد الائتماني|حد الائتمان|حد ائتمان|حدود الائتمان'),
('Write Off', r'\bWrite[ -]?[Oo]ff\b', r'شطب'),
('Budget', r'\bBudgets?\b', r'ميزانية|ميزانيات'),
('Subscription', r'\bSubscriptions?\b', r'اشتراك'),
('Loyalty', r'\bLoyalty\b', r'ولاء'),
('Shareholder', r'\bShareholders?\b', r'مساهم'),
('Maintenance', r'\bMaintenance\b', r'صيان'),
('Warranty', r'\bWarranty\b', r'ضمان'),
('Appointment', r'\bAppointments?\b', r'موعد|مواعيد'),
('Dunning', r'\bDunning\b', r'مطالبة'),
('Accounting Dimension', r'\bAccounting Dimensions?\b', r'البعد المحاسبي|الأبعاد المحاسبية|بعد محاسبي|أبعاد محاسبية'),
('Customer', r'\bCustomers?\b', r'عميل|عملاء'),
('Receivable', r'\bReceivables?\b', r'مدين|القبض|التحصيل'),
('Payable', r'\bPayables?\b', r'دائن|الدفع|مستحق'),
('Routing', r'\bRoutings?\b', r'التوجيه|توجيه|مسار تصنيع'),
('Operation', r'\bOperations?\b', r'عملي'),
('Variant', r'\bVariants?\b', r'متغير'),
('Tax Withholding', r'\bWithholding\b', r'استقطاع|الاستقطاع'),
('Advance', r'\bAdvances?\b', r'مقدم|سلف|سلفة'),
('Holiday List', r'\bHoliday Lists?\b', r'قائمة العطلات|قوائم العطلات'),
('Reorder', r'\bRe-?[Oo]rder\b', r'إعادة الطلب|إعادة طلب'),
('Safety Stock', r'\bSafety Stock\b', r'مخزون الأمان'),
('Putaway', r'\bPutaway\b', r'تخزين'),
('Sales Person', r'\bSales ?[Pp]ersons?\b', r'مندوب'),
('Blanket Order', r'\bBlanket Orders?\b', r'أمر شامل|الأمر الشامل|أوامر شاملة|الأوامر الشاملة'),
('Installation Note', r'\bInstallation Notes?\b', r'مذكرة تركيب|مذكرة التركيب|مذكرات التركيب'),
]
ar=re.compile(r'[؀-ۿ]')
def auto(k,t,names):
    if 'Template' in names:
        for o,n in [('نماذج','قوالب'),('نموذج','قالب'),('نمودج','قالب')]: t=sub_word(t,o,n)
    if 'Subcontract' in names:
        t=re.sub(r'(ال)?متعاقد(ًا|اً)? عليه(ا)? من الباطن','مصنَّع خارجياً',t)
        t=t.replace('التعاقد من الباطن','التصنيع الخارجي').replace('تعاقد من الباطن','تصنيع خارجي').replace('المقاول من الباطن','المصنِّع الخارجي').replace('مقاول من الباطن','مصنِّع خارجي').replace('للتعاقد من الباطن','للتصنيع الخارجي')
    if 'Bank' in names:
        for o,n in [('مصرفية','بنكية'),('مصرفي','بنكي'),('مصارف','بنوك'),('مصرف','بنك')]: t=sub_word(t,o,n)
    if 'Voucher' in names:
        for o,n in [('قسائم','سندات'),('قسيمة','سند')]: t=sub_word(t,o,n)
    if 'Finished Good' in names:
        t=re.sub(r'(المنتجات|البضائع|السلع) (التامة الصنع|التامة|تامة الصنع|الجاهزة)','المنتجات النهائية',t); t=re.sub(r'(المنتج|الصنف) (التام الصنع|التام)','المنتج النهائي',t); t=re.sub(r'منتج تام( الصنع)?','منتج نهائي',t); t=re.sub(r'(منتجات|بضائع|سلع) تامة( الصنع)?','منتجات نهائية',t)
    if 'Repost' in names: t=t.replace('إعادة النشر','إعادة الترحيل').replace('إعادة نشر','إعادة ترحيل').replace('المعاد نشرها','المعاد ترحيلها')
    if 'Posting Date' in names: t=t.replace('تاريخ النشر','تاريخ الترحيل').replace('تاريخ القيد','تاريخ الترحيل').replace('تاريخ التسجيل','تاريخ الترحيل')
    if 'Purchase Invoice' in names:
        t=re.sub(r'فواتير (الشراء|شراء)','فواتير المشتريات',t); t=t.replace('فاتورة الشراء','فاتورة المشتريات').replace('فاتورة شراء','فاتورة مشتريات')
    if 'Stock Reconciliation' in names: t=re.sub(r'(جرد|مطابقة) المخزون','تسوية المخزون',t); t=re.sub(r'(جرد|مطابقة) مخزون','تسوية مخزون',t)
    if 'Party' in names: t=sub_word(t,'حزب','طرف')
    if 'Closing' in names: t=t.replace('إغلاق الفترة','إقفال الفترة').replace('إغلاق المخزون','إقفال المخزون').replace('رصيد الإغلاق','الرصيد الختامي').replace('حساب الإغلاق','حساب الإقفال').replace('قيد إغلاق','قيد إقفال').replace('قيد الإغلاق','قيد الإقفال')
    if 'Opening Stock' in names: t=t.replace('مخزون أول المدة','المخزون الافتتاحي').replace('رصيد أول المدة','الرصيد الافتتاحي').replace('قيد فتح','قيد افتتاحي').replace('قيد الفتح','القيد الافتتاحي')
    if 'Pick List' in names: t=re.sub(r'قائمة (الاختيار|الانتقاء|الانتقاءات|الالتقاطات)','قائمة الالتقاط',t)
    if 'Customer' in names:
        for o,n in [('زبائن','عملاء'),('زبون','عميل')]: t=sub_word(t,o,n)
    return t
if __name__=='__main__':
    flag={}
    for k in keys:
        if k in done: continue
        t=d.get(k)
        if not t or not ar.search(t): continue
        for name,en,acc in R:
            if re.search(en,k) and not re.search(acc,t): flag.setdefault(k,set()).add(name)
    items=[]
    for k in sorted(flag):
        t=d[k]; cand=auto(k,t,flag[k])
        still=[n for n,en,acc in R if n in flag[k] and not re.search(acc,cand)]
        items.append({'en':k,'old':t,'cand':cand,'flags':sorted(flag[k]),'still':still,'ours':k in ours})
    json.dump(items,open('work_fix2.json','w'),ensure_ascii=False,indent=0)
    import collections
    c=collections.Counter(n for x in items for n in x['flags'])
    print(len(items),'auto-changed',sum(1 for x in items if x['cand']!=x['old']),'still',sum(1 for x in items if x['still']),'ours',sum(1 for x in items if x['ours']))
    print(c.most_common())
