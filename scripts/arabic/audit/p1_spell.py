"""Pass 1 (2026-11-24): spelling / punctuation scan over every Arabic translation actually used."""
import json, re, csv, collections
d=json.load(open('dict_ar.json'))
U=json.load(open('universe_code.json')); DB=json.load(open('universe_db.json'))
keys=set(DB)
for app,rows in U.items():
    if app=='insights': continue
    for p,m,c in rows:
        if isinstance(m,str): keys.add(m)
ours={r[0] for r in csv.reader(open('../../../raqim_sales/translations/ar.csv')) if len(r)>1}
AR='؀-ۿ'
words = {  # wrong -> right (whole word, optional ال/و/ب/ل/ف prefix)
 'اضافة':'إضافة','الغاء':'إلغاء','انشاء':'إنشاء','اعدادات':'إعدادات','ادخال':'إدخال','ارسال':'إرسال',
 'اجمالي':'إجمالي','اظهار':'إظهار','اخفاء':'إخفاء','اعادة':'إعادة','امكانية':'إمكانية','الى':'إلى',
 'انتاج':'إنتاج','اذن':'إذن','اشعار':'إشعار','اجازة':'إجازة','اقفال':'إقفال','ايصال':'إيصال','اصدار':'إصدار',
 'اكمال':'إكمال','ادارة':'إدارة','اذا':'إذا','او':'أو','هذة':'هذه','اسماء':'أسماء','اصل':'أصل','اصول':'أصول',
 'امر':'أمر','اوامر':'أوامر','اول':'أول','اخرى':'أخرى','اكثر':'أكثر','اقل':'أقل','ايام':'أيام','اسبوع':'أسبوع',
 'اسعار':'أسعار','ارباح':'أرباح','اجور':'أجور','انواع':'أنواع','اقسام':'أقسام','ارقام':'أرقام','اعمدة':'أعمدة',
 'اساسي':'أساسي','ايضا':'أيضًا','اي':'أي','ان':None,'لان':'لأن','مسئول':'مسؤول','شئون':'شؤون','ابريل':'أبريل',
 'اغسطس':'أغسطس','اكتوبر':'أكتوبر','الاف':'آلاف','امين':'أمين','انت':'أنت','انه':'أنه','اثناء':'أثناء',
 'اخر':'آخر','الان':'الآن','اليا':'آليًا','تلقائيا':'تلقائيًا','حاليا':'حاليًا','يدويا':'يدويًا','مسبقا':'مسبقًا',
 'جديده':'جديدة','الفاتوره':'الفاتورة','فاتوره':'فاتورة','الشركه':'الشركة','شركه':'شركة','القيمه':'القيمة',
 'المده':'المدة','الصفحه':'الصفحة','الضريبه':'الضريبة','مدينه':'مدينة','الحاله':'الحالة','حاله':'حالة',
}
pre=r'(?:^|(?<=[^'+AR+r']))((?:و|ف|ب|ل|ك)?(?:ال)?)'
iss=collections.defaultdict(list)
def add(kind,k,t): iss[kind].append((k,t,k in ours))
for k in sorted(keys):
    t=d.get(k)
    if not t or not re.search('['+AR+']',t): continue
    s=re.sub(r'\{[^{}]*\}|<[^>]+>|&\w+;|https?://\S+','',t)
    for w,r in words.items():
        if r is None: continue
        if re.search(r'(?:^|[^'+AR+r'])(?:و|ف|ب|ل)?(?:ال)?'+w+r'(?:$|[^'+AR+r'])', s): add('spell:'+w+'>'+r,k,t)
    if re.search(r'(?:^|\s)و\s+['+AR+']', s): add('detached-waw',k,t)
    if re.search(r'  ', t.strip()): add('double-space',k,t)
    if re.search(r'\s[،؛:,.!؟?)]', s) and not re.search(r'\s[:.]\s*\d', s): add('space-before-punct',k,t)
    if re.search('['+AR+r'],\s*['+AR+']', s): add('latin-comma',k,t)
    if re.search('['+AR+r']\s*;', s): add('latin-semicolon',k,t)
    if re.search('['+AR+r'][\s\)]*\?', s): add('latin-question',k,t)
    m=re.search(r'(?:^|\s)(['+AR+r']{2,})\s+\1(?:\s|$)', s)
    if m: add('doubled-word:'+m.group(1),k,t)
    if 'ـ' in re.sub(r'لـ|بـ|كـ|الـ|وـ','',s): add('tatweel',k,t)
    if re.search(r'[ً-ْ]{3,}', s): add('diacritics-pile',k,t)
    if re.search('[ﻻ-ﻼﺀ-ﻼ]', s): add('presentation-forms',k,t)
    if re.search(r'\bة|ة['+AR+']', s) and not re.search('ة['+'ً-ْ'+']',s): add('taa-marbuta-mid',k,t)
out={k:v for k,v in iss.items()}
json.dump(out,open('p1_spell.json','w'),ensure_ascii=False,indent=0)
for k,v in sorted(out.items(), key=lambda x:-len(x[1])): print(len(v), 'ours:',sum(1 for x in v if x[2]), k)
