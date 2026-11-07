"""Write ~/raqeem_icon_preview.html: ERPNext's dock icons next to style options."""
import re, os
APPS = "/home/mohammed/bench2/apps"
orig_svg = open(f"{APPS}/erpnext/erpnext/public/icons/module-icons.svg", encoding="utf-8").read()
mine_svg = open(f"{APPS}/raqim_sales/raqim_sales/public/icons/raqeem-sidebar.svg", encoding="utf-8").read()

MODS = [  # dock icon, label, tile gradient for option A
    ("sliders-soft", "Setup / الإعداد", "#94a3b8", "#475569"),
    ("calculator-soft", "Accounts / الحسابات", "#34d399", "#059669"),
    ("storefront-soft", "Selling / المبيعات", "#fb923c", "#ea580c"),
    ("shopping-cart-soft", "Buying / المشتريات", "#38bdf8", "#0284c7"),
    ("shelf-rack-soft", "Stock / المخزون", "#fbbf24", "#d97706"),
    ("factory-soft", "Manufacturing / التصنيع", "#a8a29e", "#57534e"),
    ("gantt-chart-soft", "Projects / المشاريع", "#a78bfa", "#7c3aed"),
    ("asset-hand-soft", "Assets / الأصول", "#2dd4bf", "#0d9488"),
    ("quality-seal-soft", "Quality / الجودة", "#a3e635", "#65a30d"),
    ("handshake-soft", "CRM / إدارة العملاء", "#f472b6", "#db2777"),
    ("headset-soft", "Support / الدعم", "#818cf8", "#4f46e5"),
    ("portal-user-soft", "Portal / البوابة", "#22d3ee", "#0891b2"),
]
def symbol(svg, sid):
    m = re.search(r'<symbol[^>]*id="%s"[^>]*>.*?</symbol>' % re.escape(sid), svg, re.S)
    return m.group(0) if m else ""
defs = []
for name, *_ in MODS:
    defs.append(symbol(orig_svg, "icon-" + name).replace('id="icon-', 'id="orig-'))
    defs.append(symbol(mine_svg, "rq-" + name))
use = lambda sid: f'<svg viewBox="0 0 24 24"><use href="#{sid}"/></svg>'

rows = []
for name, label, c1, c2 in MODS:
    rows.append(f"""<tr><th>{label}</th>
<td><span class="t orig">{use('orig-'+name)}</span></td>
<td><span class="t cur">{use('rq-'+name)}</span></td>
<td><span class="t a" style="--c1:{c1};--c2:{c2}">{use('rq-'+name)}</span></td>
<td><span class="t b">{use('rq-'+name)}</span></td>
<td><span class="t c">{use('rq-'+name)}</span></td></tr>""")

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Raqeem dock icons</title>
<style>
body{{margin:0;padding:32px;background:#0e1014;color:#e8eaed;font:15px 'IBM Plex Sans Arabic','Cairo',system-ui,sans-serif}}
h1{{font-size:22px;margin:0 0 6px}} p{{color:#9ba2ad;margin:0 0 22px}}
table{{border-collapse:separate;border-spacing:0 6px}}
th{{text-align:start;font-weight:600;color:#b4bac4;padding-inline-end:22px;white-space:nowrap}}
thead th{{color:#fff;font-size:14px;text-align:center;padding:0 10px 10px}}
thead small{{display:block;color:#8a919c;font-weight:400}}
td{{padding:0 18px;text-align:center}}
.t{{display:inline-grid;place-items:center;width:46px;height:46px;border-radius:14px}}
.t svg{{width:26px;height:26px;overflow:visible}}
/* ERPNext original (Frappe's soft-icon look) */
.orig{{color:#b4bac4}}
.soft-icon{{fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}}
.soft-body,.soft-layer{{fill:currentColor;fill-opacity:.1}} .soft-layer,.soft-accent{{stroke:none}}
.soft-accent{{fill:currentColor;fill-opacity:.5}} .soft-accent-line{{stroke-opacity:.5}}
/* current Raqeem duotone */
.cur{{color:#b4bac4;--rq-icon-fill:#f97316;--rq-icon-fill-opacity:.2}}
/* A: colourful app tiles */
.a{{background:linear-gradient(145deg,var(--c1),var(--c2));color:#fff;--rq-icon-fill:#fff;--rq-icon-fill-opacity:.28;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 6px 14px rgba(0,0,0,.35)}}
/* B: carbon tiles, orange glyph */
.b{{background:linear-gradient(160deg,#232833,#15181e);color:#fb923c;--rq-icon-fill:#f97316;--rq-icon-fill-opacity:.35;
    box-shadow:inset 0 0 0 1px rgba(249,115,22,.35),0 6px 14px rgba(0,0,0,.35)}}
/* C: orange gradient tiles, dark glyph */
.c{{background:linear-gradient(145deg,#fb923c,#ea580c);color:#1a0d03;--rq-icon-fill:#1a0d03;--rq-icon-fill-opacity:.18;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.3),0 6px 14px rgba(249,115,22,.25)}}
</style></head><body>
<svg style="display:none" xmlns="http://www.w3.org/2000/svg">{''.join(defs)}</svg>
<h1>Dock icon styles — أنماط أيقونات الشريط</h1>
<p>Same size as your dock (46px tiles). Pick a column and tell Claude its letter.</p>
<table><thead><tr><th></th>
<th>ERPNext<small>original</small></th><th>Now<small>current Raqeem</small></th>
<th>A<small>colourful app tiles</small></th><th>B<small>carbon tiles, orange icons</small></th><th>C<small>all-orange tiles</small></th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</body></html>"""
out = os.path.expanduser("/home/mohammed/raqeem_icon_preview.html")
open(out, "w", encoding="utf-8").write(html)
print("wrote", out, len(html))
