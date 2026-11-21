import json, pathlib
d = pathlib.Path(__file__).parent
founders = json.loads((d / "founders.json").read_text())
def trim(o):
    if isinstance(o, float): return round(o, 6) if abs(o) > 1e-9 else 0
    if isinstance(o, list): return [trim(x) for x in o]
    if isinstance(o, dict): return {k: trim(v) for k, v in o.items()}
    return o
html = (d / "template.html").read_text(encoding="utf-8")
core = (d / "core.js").read_text(encoding="utf-8").replace('if (typeof module !== "undefined") module.exports = Core;', "")
html = html.replace("/*__FOUNDERS__*/", json.dumps(trim(founders), separators=(",", ":")))
html = html.replace("/*__CORE__*/", core).replace("/*__UI__*/", (d / "ui.js").read_text(encoding="utf-8"))
(d / "index.html").write_text(html, encoding="utf-8")
print("built", len(html), "bytes")
