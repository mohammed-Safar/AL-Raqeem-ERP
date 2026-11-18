"""Shared helpers for the Arabic audit: read/merge ar.csv safely, validate a translation."""
import csv, io, json, os, re
HERE=os.path.dirname(os.path.abspath(__file__))
ARCSV=os.path.join(HERE,'../../../raqim_sales/translations/ar.csv')
PH=re.compile(r'\{[^{}]*\}'); TAG=re.compile(r'</?([a-zA-Z0-9]+)')
def read_rows():
    with open(ARCSV, newline='', encoding='utf-8') as f: return [r for r in csv.reader(f)]
def write_rows(rows):
    buf=io.StringIO(); w=csv.writer(buf, lineterminator='\n')
    for r in rows: w.writerow(r)
    with open(ARCSV,'w',newline='',encoding='utf-8') as f: f.write(buf.getvalue())
def check(en, ar):
    """return list of problems for one pair"""
    p=[]
    if sorted(PH.findall(en))!=sorted(PH.findall(ar)): p.append('placeholders')
    if sorted(x.lower() for x in TAG.findall(en))!=sorted(x.lower() for x in TAG.findall(ar)): p.append('html')
    if en.count('%s')!=ar.count('%s'): p.append('%s')
    if (en[:1]==' ')!=(ar[:1]==' ') or (en[-1:]==' ')!=(ar[-1:]==' '): p.append('edge-space')
    if ('\n' in en)!=('\n' in ar): p.append('newline')
    if not re.search(r'[؀-ۿ]',ar): p.append('no-arabic')
    return p
def merge(pairs, label=''):
    """pairs: dict en->ar. Update existing rows in place, append new ones. Returns (updated, added)."""
    rows=read_rows(); idx={}
    for i,r in enumerate(rows):
        if len(r)==2 or (len(r)>2 and not r[2]): idx[r[0]]=i   # last wins, same as Frappe; context rows left alone
    up=ad=0
    for en,ar in pairs.items():
        if en in idx:
            if rows[idx[en]][1]!=ar: rows[idx[en]][1]=ar; up+=1
        else:
            rows.append([en,ar]); idx[en]=len(rows)-1; ad+=1
    write_rows(rows)
    print(f'{label}: updated {up}, added {ad}, total rows {len(rows)}')
    return up,ad
