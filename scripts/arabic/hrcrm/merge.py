"""Merge finished HR/CRM batches (out/*.tsv) into raqim_sales/translations/ar.csv.

Run:  python3 -I merge.py        (from anywhere; paths are absolute)
Safe to re-run: rows are upserted by (English, context). RAQEEM's own strings in
../app_strings.tsv still win. A backup of ar.csv is written to ar.csv.bak first.
"""
import csv, glob, json, os, re, collections, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "../../../raqim_sales/translations/ar.csv")
APP = os.path.join(HERE, "../app_strings.tsv")
items = json.load(open(os.path.join(HERE, "items.json"), encoding="utf-8"))

def unesc(t):
    return re.sub(r"\\(\\|n|t)", lambda m: {"\\": "\\", "n": "\n", "t": "\t"}[m.group(1)], t)
PH = re.compile(r"\{[^{}]*\}|%\([a-z_]+\)s|%[sd]|<[^<>]+>|&[a-z]+;")
sig = lambda t: collections.Counter(PH.findall(t))

rows = {}
for r in csv.reader(open(OUT, encoding="utf-8")):
    if r: rows[(r[0].replace("\\n", "\n"), r[2] if len(r) > 2 else "")] = r[1].replace("\\n", "\n")

added = changed = 0; problems = []
for path in sorted(glob.glob(os.path.join(HERE, "out/*.tsv"))):
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip(): continue
        k, _, ar = line.partition("\t")
        it = items.get(k)
        ar = unesc(ar).replace("‎", "").replace("‏", "").strip()
        if not it: problems.append(f"{k}: unknown key"); continue
        if not ar: problems.append(f"{k}: empty"); continue
        if sig(it["id"]) != sig(ar): problems.append(f"{k}: placeholders differ: {it['id']!r} | {ar!r}"); continue
        key = (it["id"], it["ctx"])
        if key not in rows: added += 1
        elif rows[key] != ar: changed += 1
        rows[key] = ar

for line in open(APP, encoding="utf-8"):
    if line.strip() and not line.startswith("#"):
        en, ar = line.rstrip("\n").split("\t")
        rows[(en, "")] = ar

shutil.copy(OUT, OUT + ".bak")
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for (src, ctx), ar in sorted(rows.items()):
        s, a = src.replace("\n", "\\n"), ar.replace("\n", "\\n")
        w.writerow([s, a, ctx] if ctx else [s, a])
for p in problems: print("PROBLEM", p)
print(f"ar.csv: {len(rows)} rows (added {added}, changed {changed}, problems {len(problems)})")
