"""Pass 3 (2026-11-24): apply the reviewed (Sonnet-flagged, Opus-checked) fixes."""
import csv, json, lib
rows={}
for i in range(1,5):
    for r in csv.reader(open(f'p3/review{i}.tsv'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if len(r)>=4: rows[r[0]]=r
REJECT=set('1-25 1-26 1-426 1-559 1-644 2-237 2-719 2-720 3-180 3-311 3-403 3-510 3-587 3-605 3-607 3-718 3-722 4-18 4-19 4-21 4-22 4-175 4-648 4-192 4-236 4-278 4-692'.split())
OVERRIDE={'2-554':'ترك العمل','1-540':'الكمية في أوامر الشراء','1-111':'تاريخ رفع الإيقاف',
 '1-796':'مستودع الأصناف المقبولة','2-36':'تعيين مستودع الأصناف المقبولة','2-127':'قيد تحويل',
 '1-364':'آخر مستودع تم مسحه ضوئيًا','4-260':'قائمة المهام','2-131':'استبعاد الأصول'}
d=json.load(open('dict_ar.json'))
fix={}
for id_,r in rows.items():
    if id_ in REJECT: continue
    en, new = r[1], OVERRIDE.get(id_, r[3]).strip()
    if '…' in new or not new: print('SKIP truncated', id_); continue
    p=set(lib.check(en,new))-set(lib.check(en,d.get(en,new)))-{'edge-space'}
    if p: print('REJECT check', id_, p, en[:60]); continue
    fix[en]=new
json.dump(fix,open('p3_fixes.json','w'),ensure_ascii=False,indent=0)
print(len(rows),'flagged,',len(fix),'applied')
lib.merge(fix,'pass3')
