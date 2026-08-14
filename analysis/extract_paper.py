# -*- coding: utf-8 -*-
"""把 ar5iv 的 RethinkingTMSC HTML 转成纯文本，便于转述。"""
import re
from html.parser import HTMLParser

SRC = r"F:\winoptimizeDir\Desktop\RethinkingTMSC\_ssh\original_paper.html"
OUT = r"F:\winoptimizeDir\Desktop\RethinkingTMSC\_ssh\original_paper.txt"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
        self.in_math = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "nav", "header", "footer"):
            self.skip += 1
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr", "figcaption", "section"):
            self.parts.append("\n")
        if tag == "td" or tag == "th":
            self.parts.append(" | ")
        if tag == "math":
            self.in_math = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "nav", "header", "footer"):
            self.skip = max(0, self.skip - 1)
        if tag == "math":
            self.in_math = False

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_math:
            self.parts.append(data.strip())
        else:
            self.parts.append(data)


html = open(SRC, encoding="utf-8").read()
p = TextExtractor()
p.feed(html)
text = "".join(p.parts)
text = re.sub(r"[ \t]+", " ", text)
text = re.sub(r"\n\s*\n+", "\n\n", text)
open(OUT, "w", encoding="utf-8").write(text)
print("saved", OUT, "chars:", len(text))

# 打印目录结构（标题行）
for line in text.splitlines():
    s = line.strip()
    if re.match(r"^\d+(\.\d+)*\s", s) and len(s) < 90:
        print("H:", s)
