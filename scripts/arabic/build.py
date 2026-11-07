"""Validate translated batches and build raqim_sales/translations/ar.csv"""
import json, glob, re, csv, collections, sys
SP = sys.argv[1]
OUT = "/home/mohammed/bench2/apps/raqim_sales/raqim_sales/translations/ar.csv"
items = {x['k']: x for x in json.load(open(f"{SP}/tr/items.json"))}

def unesc(t): return t.replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
PH = re.compile(r"\{[^{}]*\}|%\([a-z_]+\)s|%[sd]|<[^<>]+>|&[a-z]+;")
def sig(t): return collections.Counter(PH.findall(t))

rows, problems, seen = {}, [], set()
for path in sorted(glob.glob(f"{SP}/tr/out/*.tsv")):
    for ln, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if not line.strip(): continue
        if '\t' not in line:
            problems.append(f"{path.rsplit('/',1)[1]}:{ln} no tab"); continue
        k, ar = line.split('\t', 1)
        ar = unesc(ar).replace('‎', '').replace('‏', '').strip()
        if k not in items:
            problems.append(f"{k}: unknown key"); continue
        it = items[k]
        src = it['id']
        if sig(src) != sig(ar):
            problems.append(f"{k}: placeholders differ\n   EN: {src!r}\n   AR: {ar!r}")
            continue
        if not ar:
            problems.append(f"{k}: empty"); continue
        rows[(src, it.get('ctx', ''))] = ar
        seen.add(k)

# glossary overrides: exact source strings, every context
gl = {}
for line in open(f"{SP}/tr/glossary_overrides.tsv", encoding='utf-8'):
    if '\t' in line:
        en, ar = line.rstrip('\n').split('\t', 1)
        gl[en] = ar
ctxs = {}
for x in items.values():
    ctxs.setdefault(x['id'], set()).add(x.get('ctx', ''))
for en, ar in gl.items():
    for c in ctxs.get(en, {''}):
        rows[(en, c)] = ar
print(f"glossary overrides: {len(gl)}")
for p in problems: print("PROBLEM", p)
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    for (src, ctx), ar in sorted(rows.items()):
        w.writerow([src.replace('\n', '\\n'), ar.replace('\n', '\\n'), ctx] if ctx else [src.replace('\n', '\\n'), ar.replace('\n', '\\n')])
kinds = collections.Counter(k[0] for k in seen)
print(f"wrote {len(rows)} rows -> {OUT}  (new: {kinds['M']}, corrected: {kinds['R']}, problems: {len(problems)})")
