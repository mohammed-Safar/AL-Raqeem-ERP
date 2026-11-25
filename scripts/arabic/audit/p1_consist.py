import json, re, collections
d=json.load(open('dict_ar.json'))
U=json.load(open('universe_code.json')); DB=json.load(open('universe_db.json'))
keys=set(DB)
for app,rows in U.items():
    if app=='insights': continue
    for p,m,c in rows:
        if isinstance(m,str): keys.add(m)
# term: (regex on English, preferred Arabic regex, list of "wrong" Arabic variants)
T={
 'Customer':(r'\bCustomers?\b',['زبون','زبائن']),
 'Warehouse':(r'\bWarehouses?\b',['مخزن','مخازن']),
 'Supplier':(r'\bSuppliers?\b',['مزود','مزوّد','بائع']),
 'Invoice':(r'\bInvoices?\b',['كمبيالة']),
 'Employee':(r'\bEmployees?\b',['عامل','العامل']),
 'Quotation':(r'\bQuotations?\b',['تسعيرة','عرض أسعار','اقتباس','عروض أسعار']),
 'Opportunity':(r'\bOpportunit(y|ies)\b',['فرصه']),
 'Item':(r'\bItems?\b(?! (Group|Lead))',['مادة','المادة','منتج','المنتج','بند']),
 'Submit':(r'\bSubmit(ted)?\b',['تقديم','قدم','إرسال','تأكيد','ترحيل']),
 'Cancel':(r'\bCancel(led)?\b',['إبطال']),
 'Amend':(r'\bAmend',['تعديل']),
 'Ledger':(r'\bLedger\b',['سجل']),
 'Journal Entry':(r'\bJournal Entr',['إدخال اليومية','قيد يومية','مدخل']),
 'Payment Entry':(r'\bPayment Entr',['إدخال الدفع','قيد الدفع','قيد دفع']),
 'Stock Entry':(r'\bStock Entr',['قيد المخزون','إدخال المخزون','قيد مخزون']),
 'Delivery Note':(r'\bDelivery Notes?\b',['مذكرة التسليم','إشعار التسليم','سند التسليم','ملاحظة التسليم']),
 'Purchase Receipt':(r'\bPurchase Receipts?\b',['إيصال الشراء','ايصال شراء','استلام المشتريات']),
 'Cost Center':(r'\bCost Cent(er|re)s?\b',['مركز التكاليف']),
 'Fiscal Year':(r'\bFiscal Years?\b',['سنة مالية','السنة المالية'],),
 'Salary Slip':(r'\bSalary Slips?\b',['قسيمة الراتب','إيصال الراتب']),
 'Attendance':(r'\bAttendance\b',['دوام']),
 'Leave Application':(r'\bLeave Applications?\b',['طلب أجازة','تطبيق الإجازة']),
 'Price List':(r'\bPrice Lists?\b',['لائحة الأسعار']),
 'UOM':(r'\bUOMs?\b',['UOM']),
 'Draft':(r'\bDraft\b',['مشروع']),
 'Territory':(r'\bTerritor(y|ies)\b',['إقليم','الإقليم','منطقة جغرافية']),
}
iss=collections.defaultdict(list)
for k in keys:
    t=d.get(k)
    if not t: continue
    for term,(rx,bad) in T.items():
        if re.search(rx,k):
            for b in bad:
                if re.search(r'(?:^|[^ء-ي])(?:و|ب|ل|ك|ف)?(?:ال)?'+re.escape(b.replace('ال','',1) if b.startswith('ال') else b)+r'(?:$|[^ء-ي])', t) and not (term=='Fiscal Year'):
                    iss[term+'~'+b].append((k,t))
for k,v in sorted(iss.items(), key=lambda x:-len(x[1])):
    print(len(v),k)
    for e,a in v[:6]: print('     ',e[:70].replace('\n',' '),'=>',a[:80].replace('\n',' '))
json.dump(iss,open('p1_consist.json','w'),ensure_ascii=False,indent=0)
