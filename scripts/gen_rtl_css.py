"""Right-to-left mirror for Frappe CRM (/crm) and the HR app (/hrms, /hr/roster).

Both are built with Tailwind utilities that are PHYSICAL (ml-2 = margin-left, right-0, border-r,
rounded-l ...), so when the page is switched to dir="rtl" for Arabic the text flips but every gap,
offset and border stays on the wrong side (e.g. sidebar icons glued to their labels).

This reads the apps' compiled CSS and writes, for every class rule that uses a left/right property,
a mirrored rule scoped to html.<scope>[dir="rtl"]:
  * a low-priority reset of the original side:       [dir=rtl] .ml-2            { margin-left: 0 }
  * a high-priority value on the mirrored side:      [dir=rtl] .ml-2:not(#rq-rtl) { margin-right: .5rem }
so an element with both ml-2 and mr-4 still ends up right (the values always beat the resets).
Media queries are kept. Centring (left-1/2 + translate) and symmetric utilities are left alone.

Output: public/css/raqeem_crm_rtl.css and raqeem_hrms_rtl.css (loaded by web_inject.py).
Re-run after updating CRM or HRMS:  python3 -I apps/raqim_sales/scripts/gen_rtl_css.py
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.abspath(os.path.join(HERE, "../.."))
CSS_OUT = os.path.join(HERE, "../raqim_sales/public/css")
TARGETS = [
	("rq-crm", [f"{APPS}/crm/crm/public/frontend/assets/*.css"], "raqeem_crm_rtl.css"),
	("rq-hrms", [f"{APPS}/hrms/hrms/public/frontend/assets/*.css", f"{APPS}/hrms/hrms/public/roster/assets/*.css"],
	 "raqeem_hrms_rtl.css"),
]

SWAP = {
	"margin-left": "margin-right", "margin-right": "margin-left",
	"padding-left": "padding-right", "padding-right": "padding-left",
	"left": "right", "right": "left",
	"border-left": "border-right", "border-right": "border-left",
	"border-left-width": "border-right-width", "border-right-width": "border-left-width",
	"border-left-color": "border-right-color", "border-right-color": "border-left-color",
	"border-left-style": "border-right-style", "border-right-style": "border-left-style",
	"border-top-left-radius": "border-top-right-radius", "border-top-right-radius": "border-top-left-radius",
	"border-bottom-left-radius": "border-bottom-right-radius", "border-bottom-right-radius": "border-bottom-left-radius",
	"scroll-margin-left": "scroll-margin-right", "scroll-margin-right": "scroll-margin-left",
	"scroll-padding-left": "scroll-padding-right", "scroll-padding-right": "scroll-padding-left",
}
# value that "removes" a property again (the reset rule)
RESET = {"margin": "0", "padding": "0", "left": "auto", "right": "auto", "border": "0", "radius": "0", "scroll": "0"}


def reset_for(prop):
	if prop in ("left", "right"):
		return "auto"
	if "radius" in prop:
		return "0"
	if prop.startswith("border") and prop.endswith("color"):
		return "initial"
	if prop.startswith("border") and prop.endswith("style"):
		return "none"
	if prop.startswith("border"):
		return "0"
	return "0"


def parse(css):
	"""-> list of (prelude, body) where body is a str (declarations) or a nested list (@media)."""
	out, i, n = [], 0, len(css)
	while i < n:
		j = css.find("{", i)
		if j == -1:
			break
		prelude = css[i:j].strip()
		depth, k = 1, j + 1
		while k < n and depth:
			if css[k] == "{":
				depth += 1
			elif css[k] == "}":
				depth -= 1
			k += 1
		inner = css[j + 1:k - 1]
		if prelude.startswith(("@media", "@supports", "@layer", "@container")):
			out.append((prelude, parse(inner)))
		elif prelude.startswith("@"):
			pass  # @keyframes, @font-face, @property ...
		else:
			out.append((prelude, inner))
		i = k
	return out


def split_selectors(sel):
	parts, depth, cur = [], 0, ""
	for ch in sel:
		if ch in "([":
			depth += 1
		elif ch in ")]":
			depth -= 1
		if ch == "," and depth == 0:
			parts.append(cur.strip())
			cur = ""
		else:
			cur += ch
	if cur.strip():
		parts.append(cur.strip())
	return parts


def decls(body):
	res = []
	for d in body.split(";"):
		if ":" not in d:
			continue
		p, v = d.split(":", 1)
		res.append((p.strip(), v.strip()))
	return res


def mirror_rule(sel, body, scope):
	ds = decls(body)
	resets, values = [], []
	if any(p == "--tw-space-x-reverse" for p, _ in ds):
		# Tailwind space-x-*: its own switch does the mirroring, nothing else to change
		ds = [("--tw-space-x-reverse", "0")]
	for p, v in ds:
		if p == "--tw-space-x-reverse" and v.strip() == "0":
			values.append(("--tw-space-x-reverse", "1"))
			continue
		if p == "text-align" and v in ("left", "right"):
			values.append(("text-align", "right" if v == "left" else "left"))
			continue
		if p == "float" and v in ("left", "right"):
			values.append(("float", "right" if v == "left" else "left"))
			continue
		if p not in SWAP:
			continue
		if p in ("left", "right") and v.replace(" ", "") in ("50%", "calc(50%)"):
			return None  # centring with translate: leave the whole rule alone
		q = SWAP[p]
		resets.append((p, reset_for(p)))
		values.append((q, v))
	if not values:
		return None
	# symmetric rule (e.g. mx-*, px-*, inset-x-*): both sides set to the same value -> nothing to do
	have = dict(ds)
	if all(have.get(SWAP.get(p, ""), None) == v for p, v in ds if p in SWAP) and not any(
		p in ("--tw-space-x-reverse", "text-align", "float") for p, _ in values):
		return None
	sels = []
	for s in split_selectors(sel):
		if "." not in s or s.startswith((":root", "html", "body", "*")):
			continue
		sels.append(s)
	if not sels:
		return None
	pre = f'html.{scope}[dir="rtl"] '
	out = []
	if resets:
		out.append(",".join(pre + s for s in sels) + "{" + ";".join(f"{p}:{v}" for p, v in resets) + "}")
	out.append(",".join(pre + add_id(s) for s in sels) + "{" + ";".join(f"{p}:{v}" for p, v in values) + "}")
	return "".join(out)


def add_id(sel):
	"""raise priority: put :not(#rq-rtl) on the element the rule styles (before any pseudo-element)."""
	m = re.search(r"(::?(?:before|after|placeholder|marker|selection|file-selector-button))$", sel)
	if m:
		return sel[: m.start()] + ":not(#rq-rtl)" + m.group(1)
	return sel + ":not(#rq-rtl)"


def walk(nodes, scope):
	out = []
	for prelude, body in nodes:
		if isinstance(body, list):
			inner = walk(body, scope)
			if inner:
				out.append(prelude + "{" + "".join(inner) + "}")
		else:
			r = mirror_rule(prelude, body, scope)
			if r:
				out.append(r)
	return out


for scope, patterns, name in TARGETS:
	files = sorted(f for p in patterns for f in glob.glob(p))
	seen, rules = set(), []
	for f in files:
		for r in walk(parse(open(f, encoding="utf-8").read()), scope):
			if r not in seen:
				seen.add(r)
				rules.append(r)
	text = (f"/* generated by scripts/gen_rtl_css.py from {len(files)} compiled CSS files — do not edit.\n"
			f"   Right-to-left mirror of the physical left/right utilities, for html.{scope}[dir=rtl]. */\n"
			+ "\n".join(rules) + "\n")
	open(os.path.join(CSS_OUT, name), "w", encoding="utf-8").write(text)
	print(f"{name}: {len(rules)} mirrored rules from {len(files)} files ({len(text)//1024} KB)")
