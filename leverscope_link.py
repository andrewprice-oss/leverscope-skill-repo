#!/usr/bin/env python3
"""Check a LeverScope model and print the link that opens it.

Usage:  python3 leverscope_link.py model.json        (or pipe the JSON in on stdin)
Prints warnings (if any) to stderr and the link to stdout. Exit code 1 if the model has errors.
The link carries the model after '#', which browsers never send to a server; LeverScope
(https://leverscope.com) reads it in the user's browser and simulates it there.
"""
import base64, json, re, sys, zlib

APP = "https://leverscope.com/app/"
FUNCS = set("""IF THEN ELSE AND OR NOT MIN MAX SMTH1 SMTH3 SMTHN DELAY DELAY1 DELAY3 DELAYN INIT PREVIOUS TREND FORCST NPV
EXPRND LOGNORMAL POISSON LOOKUP LOOKUPINT STEP RAMP PULSE SAFEDIV NOISE NORMAL RANDOM SQRT EXP LN LOG10 ABS ROUND INT
SIN COS TAN ARCTAN ARCSIN ARCCOS SUM MEAN MOD TIME DT STARTTIME STOPTIME PI""".split())
TYPES = {"stock": "stock", "flow": "flow", "converter": "aux", "aux": "aux", "constant": "aux", "variable": "aux"}


def clean(name):
    n = str(name or "").strip()
    for a, b in {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}.items():
        n = n.replace(a, b)
    n = re.sub(r"[\s\-./]+", "_", n)
    return re.sub(r"[^A-Za-z0-9_]", "", n)


def check(model):
    errors, warnings = [], []
    els = model.get("elements")
    if not isinstance(els, list) or not els:
        return ["The model needs a non-empty \"elements\" list."], warnings
    names = {}
    for i, e in enumerate(els):
        t = TYPES.get(str(e.get("type", "")).lower())
        if not t:
            errors.append(f"Element {i + 1}: unknown type {e.get('type')!r} (use stock, flow or converter).")
            continue
        n = clean(e.get("name"))
        if not n:
            errors.append(f"Element {i + 1}: missing name.")
            continue
        if n.lower() in names:
            errors.append(f"Two elements are called {n}.")
        names[n.lower()] = t
        if n != e.get("name"):
            warnings.append(f"{e.get('name')!r} will be called {n} (use that spelling in equations).")
    renamed = sorted(((str(e.get("name")), clean(e.get("name"))) for e in els if e.get("name") and clean(e.get("name")) != e.get("name")), key=lambda x: -len(x[0]))
    for e in els:
        n, t = clean(e.get("name")), TYPES.get(str(e.get("type", "")).lower())
        if t == "flow":
            for end in ("from", "to"):
                v = e.get(end)
                if v not in (None, "") and names.get(clean(v).lower()) != "stock":
                    errors.append(f"Flow {n}: {end} {v!r} is not a stock name (use null for outside the model).")
            if not e.get("from") and not e.get("to"):
                warnings.append(f"Flow {n} is not connected to any stock.")
        eq = str(e.get("eq", e.get("value", "")))
        for old, new in renamed:  # LeverScope rewrites names written with spaces or umlauts the same way
            eq = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])", new, eq, flags=re.I)
        for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", re.sub(r"\{[^}]*\}", "", eq)):
            if w.upper() not in FUNCS and w.lower() not in names:
                errors.append(f"{n}: equation uses {w!r}, which is not an element name.")
        s = e.get("slider")
        if s and t == "aux":
            try:
                float(eq)
            except ValueError:
                warnings.append(f"{n}: a slider needs a plain number as its value; LeverScope will drop the slider.")
    for k in (model.get("summary") or {}).get("kpis", []):
        if clean(k.get("name")).lower() not in names:
            errors.append(f"Key figure {k.get('name')!r} is not an element name.")
    for sc in model.get("scenarios", []) or []:
        for k in (sc.get("values") or {}):
            if clean(k).lower() not in names:
                errors.append(f"Scenario {sc.get('name')!r} sets {k!r}, which is not an element name.")
    for p in model.get("plots", []) or []:
        if clean(p).lower() not in names:
            warnings.append(f"Plot {p!r} is not an element name and will be skipped.")
    for e in els:
        eq = str(e.get("eq", ""))
        if re.search(r"\bIF\b", eq, re.I) and not re.search(r"\bELSE\b", eq, re.I):
            errors.append(f"{clean(e.get('name'))}: IF needs THEN and ELSE.")
        if eq.count("(") != eq.count(")"):
            errors.append(f"{clean(e.get('name'))}: brackets do not match.")
    sim = model.get("sim") or {}
    if sim and float(sim.get("dt", 0.25)) <= 0:
        errors.append("sim.dt must be positive.")
    return errors, warnings


def link(model):
    raw = json.dumps(model, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    c = zlib.compressobj(9, zlib.DEFLATED, -15)  # raw DEFLATE
    return APP + "#model=" + base64.urlsafe_b64encode(c.compress(raw) + c.flush()).decode().rstrip("=")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    text = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    model = json.loads(text)
    errors, warnings = check(model)
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    for e in errors:
        print("error:", e, file=sys.stderr)
    if errors:
        sys.exit(1)
    print(link(model))
