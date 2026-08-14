# -*- coding: utf-8 -*-
from pypdf import PdfReader

p = r"F:\winoptimizeDir\Desktop\RethinkingTMSC\analysis\_qa\final3.pdf"
r = PdfReader(p, strict=False)
for i in (2, 3):
    t = r.pages[i].extract_text() or ""
    print(f"=== 页{i+1} 包含公式的行 ===")
    for ln in t.splitlines():
        if any(k in ln for k in ("I =", "H =", "SelfAttn", "∈", "R")):
            print(" |", ln[:90])
