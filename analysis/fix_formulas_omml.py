# -*- coding: utf-8 -*-
"""把《论文复现_完整版.docx》中的 7 个公式替换为 Word 原生公式（OMML）。
仅改动公式段落，保留分节、页眉、表格与其他内容。
"""
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn

P = r"F:\winoptimizeDir\Desktop\复现\论文复现_完整版.docx"
MNS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def mel(tag):
    return parse_xml(f'<m:{tag} xmlns:m="{MNS}"/>')


def mr(text):
    r = mel("r")
    t = mel("t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def ssub(base, sub):
    el = mel("sSub")
    e = mel("e"); e.append(mr(base))
    s = mel("sub"); s.append(mr(sub))
    el.append(e); el.append(s)
    return el


def ssup(base, sup):
    el = mel("sSup")
    e = mel("e"); e.append(mr(base))
    s = mel("sup"); s.append(mr(sup))
    el.append(e); el.append(s)
    return el


def ssubsup(base, sub, sup):
    el = mel("sSubSup")
    e = mel("e"); e.append(mr(base))
    s = mel("sub"); s.append(mr(sub))
    p = mel("sup"); p.append(mr(sup))
    el.append(e); el.append(s); el.append(p)
    return el


# 7 个公式：("text", ...) / ("sub", base, sub) / ("sup", base, sup) / ("subsup", base, sub, sup)
FORMULAS = {
    1: [("text", "I = ["), ("sub", "v", "1"), ("text", ", "), ("sub", "v", "2"),
        ("text", ", …, "), ("sub", "v", "49"), ("text", "], "), ("sub", "v", "i"),
        ("text", " ∈ "), ("sup", "R", "2048")],
    2: [("text", "I = ["), ("sub", "v", "cls"), ("text", ", "), ("sub", "v", "1"),
        ("text", ", "), ("sub", "v", "2"), ("text", ", …, "), ("sub", "v", "196"),
        ("text", "], "), ("sub", "v", "i"), ("text", " ∈ "), ("sup", "R", "768")],
    3: [("text", "I = ["), ("sub", "v", "1"), ("text", ", "), ("sub", "v", "2"),
        ("text", ", …, "), ("sub", "v", "36"), ("text", "], "), ("sub", "v", "i"),
        ("text", " ∈ "), ("sup", "R", "2048")],
    4: [("text", "H = "), ("subsup", "H", "p", "I"), ("text", " ⊕ "),
        ("subsup", "H", "p", "T"), ("text", ",  H ∈ "), ("sup", "R", "768+768")],
    5: [("text", "H = "), ("subsup", "H", "p", "I"), ("text", " ⊗ "),
        ("subsup", "H", "p", "T"), ("text", ",  H ∈ "), ("sup", "R", "768×768")],
    6: [("text", "H = SelfAttn(["), ("sup", "H", "T"), ("text", "; "),
        ("sup", "H", "I"), ("text", "]) ∈ "), ("sup", "R", "768")],
    7: [("text", "H = ["), ("sup", "H", "I→T"), ("text", "; "), ("sup", "H", "T→I"),
        ("text", "] ∈ "), ("sup", "R", "768+768")],
}


def build_math(segs):
    om = mel("oMath")
    for seg in segs:
        if seg[0] == "text":
            om.append(mr(seg[1]))
        elif seg[0] == "sub":
            om.append(ssub(seg[1], seg[2]))
        elif seg[0] == "sup":
            om.append(ssup(seg[1], seg[2]))
        elif seg[0] == "subsup":
            om.append(ssubsup(seg[1], seg[2], seg[3]))
    return om


def make_run(text, size_half=24):
    r = parse_xml(
        f'<w:r xmlns:w="{W[1:-1]}">'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        f'w:eastAsia="NSimSun"/><w:sz w:val="{size_half}"/><w:szCs w:val="{size_half}"/></w:rPr>'
        f'<w:t xml:space="preserve">{text}</w:t></w:r>')
    return r


doc = Document(P)
body = doc.element.body
bm_names = {b.get(qn("w:name")): b for b in body.iter(qn("w:bookmarkStart"))}

import re
converted = 0
for num in range(1, 8):
    bm = bm_names.get(f"eq{num}")
    if bm is None:
        print(f"公式 {num}: 未找到书签，跳过")
        continue
    p_el = bm.getparent()
    while p_el is not None and p_el.tag != W + "p":
        p_el = p_el.getparent()
    if p_el is None:
        print(f"公式 {num}: 找不到段落，跳过")
        continue
    # 清空段落（保留 pPr）
    for child in list(p_el):
        if child.tag != qn("w:pPr"):
            p_el.remove(child)
    # 公式本体
    p_el.append(build_math(FORMULAS[num]))
    # 制表位
    p_el.append(make_run("\t"))
    # (n) 编号 + 书签
    bid = 5000 + num
    bs = parse_xml(f'<w:bookmarkStart xmlns:w="{W[1:-1]}" w:id="{bid}" w:name="eq{num}"/>')
    be = parse_xml(f'<w:bookmarkEnd xmlns:w="{W[1:-1]}" w:id="{bid}"/>')
    p_el.append(bs)
    p_el.append(make_run(f"({num})"))
    p_el.append(be)
    converted += 1
    print(f"公式 {num}: 已替换为 OMML")

try:
    doc.save(P)
    print("已保存:", P)
except PermissionError:
    P2 = P.replace(".docx", "_公式版.docx")
    print("原文件被占用，另存为:", P2)
    doc.save(P2)
print("完成，替换公式数:", converted)
