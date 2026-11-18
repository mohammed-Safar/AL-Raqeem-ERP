import json, re, csv
import importlib.util, sys
d=json.load(open('dict_ar.json'))
G=json.load(open('glossary_viol.json')); Q=json.load(open('quality.json'))
ours={r[0] for r in csv.reader(open('../../../raqim_sales/translations/ar.csv')) if len(r)>1}
flag={}
for name,v in G.items():
    for app,k,t,o in v: flag.setdefault(k,set()).add(name)
for cat in ['placeholder','html','percent','newline','quote','space','colon']:
    for k,t in Q.get(cat,[]): flag.setdefault(k,set()).add('#'+cat)
PFX=r'(?<![؀-ۿ])((?:و|ف)?(?:ب|ك|ل)?)'
def sub_word(t, old, new):
    # old/new are bare nouns (no ال); handles ال / لل and prefixes
    t=re.sub(PFX+'ال'+old+r'(?![؀-ۿ])', lambda m:m.group(1)+'ال'+new, t)
    t=re.sub(r'(?<![؀-ۿ])((?:و|ف)?)لل'+old+r'(?![؀-ۿ])', lambda m:m.group(1)+'لل'+new, t)
    t=re.sub(PFX+old+r'(?![؀-ۿ])', lambda m:m.group(1)+new, t)
    return t
def phrase(t, olds, new_def, new_indef):
    for o in olds:
        t=t.replace(o, new_def if ('ال' in o.split()[0][:3] or ' ال' in o) else new_indef)
    return t
def auto(k,t,names):
    t=re.sub(r'\s*(\\n|\n)?\s*<br>\s*(\\n|\n)?\s*[A-Za-z\'"{#].*$','',t,flags=re.S) if ('<br>' in t and '<br>' not in k) else t
    if 'Item' in names:
        for o,n in [('عنصرًا','صنفًا'),('عنصراً','صنفاً'),('عنصر','صنف'),('عناصر','أصناف'),('بند','صنف'),('بنود','أصناف')]: t=sub_word(t,o,n)
    if 'Delivery Note' in names:
        t=re.sub(r'(ملاحظة|ملاحظه|مذكرة|إشعار|اشعار|إيصال|ايصال) التسليم','إذن التسليم',t); t=re.sub(r'(ملاحظة|ملاحظه|مذكرة|إشعار|اشعار|إيصال|ايصال) تسليم','إذن تسليم',t); t=re.sub(r'(إشعارات|مذكرات|ملاحظات|إيصالات) التسليم','أذون التسليم',t)
    if 'Sales Order' in names:
        t=re.sub(r'(طلبات|أوامر) (المبيعات|البيع)','أوامر البيع',t); t=re.sub(r'(طلب|أمر|ترتيب) (المبيعات|البيع|التوريد)','أمر البيع',t); t=re.sub(r'(طلب|أمر) (مبيعات|بيع)','أمر بيع',t)
    if 'Purchase Order' in names:
        t=re.sub(r'(طلبات|أوامر) (المشتريات|الشراء)','أوامر الشراء',t); t=re.sub(r'(طلب|أمر) (المشتريات|الشراء)','أمر الشراء',t); t=re.sub(r'(طلب|أمر) (مشتريات|شراء)','أمر شراء',t)
    if 'Purchase Receipt' in names:
        t=re.sub(r'(إيصالات|ايصالات) (الشراء|المشتريات)','إيصالات الاستلام',t); t=re.sub(r'(إيصال|ايصال|استلام|وصل) (الشراء|المشتريات)','إيصال الاستلام',t); t=re.sub(r'(إيصال|ايصال|استلام) (شراء|مشتريات)','إيصال استلام',t)
    if 'Stock Entry' in names:
        t=re.sub(r'(إدخالات|قيود|مدخلات|ادخالات) (المخزون|المخزن)','حركات المخزون',t); t=re.sub(r'(إدخال|قيد|مدخل|ادخال) (المخزون|المخزن)','حركة المخزون',t); t=re.sub(r'(إدخال|قيد|مدخل|ادخال) (مخزون|مخزن)','حركة مخزون',t); t=t.replace('الحركة المخزنية','حركة المخزون')
    if 'Payment Entry' in names:
        t=re.sub(r'(إدخالات|قيود|مدخلات) (الدفع|المدفوعات)','سندات الدفع',t); t=re.sub(r'(إدخال|قيد|مدخل|تدوين) (الدفع|المدفوعات)','سند الدفع',t); t=re.sub(r'(إدخال|قيد|مدخل|تدوين) (دفع|مدفوعات)','سند دفع',t)
    if 'Journal Entry' in names:
        t=re.sub(r'(إدخال|قيد|مدخل) دفتر اليومية','قيد اليومية',t); t=re.sub(r'(إدخالات|مدخلات) (دفتر )?اليومية','قيود اليومية',t); t=t.replace('مدخل قيد اليومية','قيد اليومية')
    if 'Stock' in names:
        t=sub_word(t,'أسهم','مخزون'); t=sub_word(t,'سهم','مخزون')
    if 'Depreciation' in names:
        for o,n in [('استهلاكات','إهلاكات'),('استهلاك','إهلاك'),('إستهلاك','إهلاك'),('اهلاك','إهلاك')]: t=sub_word(t,o,n)
    if 'Permission' in names:
        for o,n in [('أذونات','صلاحيات'),('إذن','صلاحية'),('أذون','صلاحيات'),('تصاريح','صلاحيات'),('تصريح','صلاحية')]: t=sub_word(t,o,n)
    if 'DocType' in names:
        t=re.sub(r'\b(DocTypes|DOCTYPES)\b','أنواع المستندات',t); t=re.sub(r'\b(DocType|DOCTYPE|Doctype|doctype)\b','نوع المستند',t)
    if 'BOM' in names:
        t=re.sub(r'(فاتورة|قائمة مكونات|قائمة مكوّنات) (المواد|الموارد|الصنف)','قائمة المواد',t); t=re.sub(r'\bBOMs?\b','قائمة المواد',t); t=t.replace('قائمة المكونات','قائمة المواد').replace('قائمة مكونات','قائمة مواد')
    if 'Valuation Rate' in names: t=t.replace('معدل التقييم','سعر التقييم').replace('معدل تقييم','سعر تقييم')
    if 'Timesheet' in names:
        t=re.sub(r'(جداول الدوام|الجداول الزمنية|أوراق الوقت|سجلات الدوام)','سجلات الوقت',t); t=re.sub(r'(جدول الدوام|الجدول الزمني|ورقة الوقت|سجل الدوام)','سجل الوقت',t); t=re.sub(r'(جدول دوام|جدول زمني)','سجل وقت',t)
    if 'Serial No' in names:
        t=re.sub(r'(الرقم المتسلسل|رقم المسلسل|الرقم المسلسل|الرقم التسلسلى)','الرقم التسلسلي',t); t=re.sub(r'(?<![؀-ۿ])المسلسل(?![؀-ۿ])','الرقم التسلسلي',t)
    if 'Dashboard' in names: t=re.sub(r'لوحة (القيادة|التحكم|البيانات)','لوحة المعلومات',t)
    if 'Work Order' in names: t=re.sub(r'(أمر|طلب) (التشغيل|الشغل)','أمر العمل',t); t=t.replace('طلب العمل','أمر العمل')
    if 'UOM' in names: t=re.sub(r'\bUOM\b','وحدة القياس',t)
    if 'Grand Total' in names: t=re.sub(r'(المجموع الكلي|المجموع الإجمالي|الإجمالي العام|المجموع العام|المبلغ الإجمالي)','الإجمالي الكلي',t)
    return t
if __name__=='__main__':
    sys.path.insert(0,'.')
    import c2
