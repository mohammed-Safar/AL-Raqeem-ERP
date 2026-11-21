"""Build raqeem_skin_<name>.css from raqeem_skin_<name>.src.css.
@S in the source = html[data-skin="<name>"]; @font-face / @media are left alone.
Run from apps/raqim_sales:  python3 scripts/build_skin.py ufuq"""
import re, sys, pathlib
name = sys.argv[1] if len(sys.argv) > 1 else "ufuq"
css = pathlib.Path(__file__).resolve().parent.parent / "raqim_sales/public/css"
src = (css / f"raqeem_skin_{name}.src.css").read_text()
out = re.sub(r'@S(?=[\s\[:,{.])', f'html[data-skin="{name}"]', src)
out = f"/* GENERATED from raqeem_skin_{name}.src.css by scripts/build_skin.py — do not edit */\n" + out
(css / f"raqeem_skin_{name}.css").write_text(out)
print("ok", out.count(f'html[data-skin="{name}"]'), "selectors")
