"""Every element id app.js touches must exist in index.html (and vice versa for handlers)."""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
html = (root / "static" / "index.html").read_text(encoding="utf-8")
js = (root / "static" / "js" / "app.js").read_text(encoding="utf-8")

html_ids = set(re.findall(r'id="([^"]+)"', html))
js_ids = set(re.findall(r'\$\("([^"]+)"\)', js))

missing = sorted(js_ids - html_ids)
unused = sorted(html_ids - js_ids)

print(f"ids in html: {len(html_ids)} | ids used by js: {len(js_ids)}")
print("MISSING in html (js would crash):", missing or "none")
print("in html but never used by js:", unused or "none")

# css classes the js toggles should exist in the stylesheet
css = (root / "static" / "css" / "styles.css").read_text(encoding="utf-8")
for cls in ["post-card", "violation-chip", "overlay", "alarm", "result-actions",
            "linkish", "tags", "done-note", "rules", "topbar", "posts"]:
    assert "." + cls in css, f"missing css class .{cls}"
print("css classes present: ok")

assert not missing, "app.js references ids that do not exist"
print("\nDOM CHECK PASSED")
