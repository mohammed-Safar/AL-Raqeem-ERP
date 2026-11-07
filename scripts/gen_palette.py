import re, sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(HERE, "../../frappe/frappe/public/css/espresso/")
out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "../raqim_sales/public/css/raqeem_palette.css")

def blocks(path):
    """yield (selector, {var: value}) for each top-level block"""
    txt = open(path).read()
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", txt):
        sel = " ".join(m.group(1).split())
        d = {}
        for vm in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(2)):
            d[vm.group(1)] = vm.group(2).strip()
        yield sel, d

light, dark = {}, {}
for f in ["colors.css", "legacy.css", "effects.css"]:
    for sel, d in blocks(base + f):
        if "dark" in sel:
            dark.update(d)
        elif ":root" in sel or 'data-theme="light"' in sel:
            light.update(d)

def resolve(val, depth=0):
    if depth > 12: return val
    def rep(m):
        name, fb = m.group(1), m.group(2)
        v = dark.get(name, light.get(name))
        if v is None:
            return fb.strip(", ") if fb else m.group(0)
        return resolve(v, depth + 1)
    return re.sub(r"var\((--[\w-]+)(\s*,[^()]*)?\)", rep, val)

COLORS = "red|green|blue|amber|orange|yellow|teal|cyan|violet|purple|pink"
keep = re.compile(
    rf"^--(({COLORS})-(alpha-)?\d+"                       # raw coloured palette
    rf"|(surface|ink|outline)-({COLORS})-\d+"            # semantic coloured
    rf"|(surface|ink|outline)-alert-[\w-]+"
    rf"|(bg|text-on)-[\w-]+"                              # legacy bg/text-on
    rf"|alert-[\w-]+|ink-blue-link"
    rf"|surface-alpha-[\w-]+|outline-alpha-[\w-]+|gray-alpha-\d+"
    rf"|surface-gray-(5|6|7|8|9|10)|outline-gray-[4-9]|outline-base|outline-elevation-\d"
    rf"|shadow[\w-]*|focus-[\w-]+)$")
# never touch tokens the theme sets itself
skip = {"--text-on-gray", "--bg-color"}

lines = []
for name in sorted(set(dark) | set(light)):
    if keep.match(name) and name not in skip:
        lines.append(f"    {name}: {resolve(dark.get(name, light.get(name)))} !important;")

with open(out_path, "w") as o:
    o.write("""/* ==========================================================================
   ALRAQEEM — DARK STATUS PALETTE
   Generated from Frappe's own dark-mode tokens (espresso/colors.css, legacy.css,
   effects.css), resolved to literal values and applied in dark mode only
   (light mode keeps Frappe's own light palette), so badges, alerts, indicators and charts match the carbon theme.
   Regenerate after a Frappe upgrade: python3 apps/raqim_sales/scripts/gen_palette.py
   ========================================================================== */
html[data-theme="dark"] {
""")
    o.write("\n".join(lines))
    o.write("\n}\n")
print(len(lines), "tokens")
