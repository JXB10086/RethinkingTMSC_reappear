# -*- coding: utf-8 -*-
"""对 Twitter15 / Twitter17 的原始 tsv 数据进行统计分析。"""
import os
import csv
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)  # skip header
        for r in reader:
            if len(r) >= 5:
                rows.append({
                    "label": int(r[1]),
                    "img": r[2],
                    "text": r[3],
                    "target": r[4],
                })
    return rows


def words(s):
    return [w for w in s.split() if w]


for ds in ("Twitter15", "Twitter17"):
    print("=" * 30, ds, "=" * 30)
    stats = {}
    for split in ("train", "dev", "test"):
        rows = load_tsv(os.path.join(ROOT, "data", ds, split + ".tsv"))
        stats[split] = rows
        label_dist = Counter(r["label"] for r in rows)
        print(f"\n[{split}] n={len(rows)}  label分布={dict(sorted(label_dist.items()))}")
        pct = {k: f"{v / len(rows) * 100:.1f}%" for k, v in sorted(label_dist.items())}
        print("   label占比:", pct)

    all_rows = stats["train"] + stats["dev"] + stats["test"]
    imgs = Counter(r["img"] for r in all_rows)
    per_img = defaultdict(list)
    for r in all_rows:
        per_img[r["img"]].append(r)
    n_imgs = len(imgs)
    share = Counter(len(v) for v in per_img.values())
    print(f"\n[全部样本] 样本数={len(all_rows)}, 去重图片数={n_imgs}, 平均每图样本={len(all_rows) / n_imgs:.2f}")
    print("   每图样本数分布:", dict(sorted(share.items())))

    # 目标与文本长度
    for split in ("train", "dev", "test"):
        rows = stats[split]
        tgt_lens = [len(words(r["target"])) for r in rows]
        tgt_chars = [len(r["target"]) for r in rows]
        txt_lens = [len(words(r["text"])) for r in rows]
        import statistics as st
        print(f"\n[{split}] 目标词数: 均值{st.mean(tgt_lens):.2f} 中位{st.median(tgt_lens)} 最大{max(tgt_lens)}")
        print(f"   目标字符: 均值{st.mean(tgt_chars):.2f} 中位{st.median(tgt_chars)} 最大{max(tgt_chars)}")
        print(f"   文本词数: 均值{st.mean(txt_lens):.2f} 中位{st.median(txt_lens)} 最大{max(txt_lens)}")

    # 目标出现次数（全样本）
    tgt_count = Counter(r["target"] for r in all_rows)
    print("\n[全样本] 不同目标数:", len(tgt_count), " 出现最多的目标:", tgt_count.most_common(10))
    # 文本中是否含 $T$ 占位符
    placeholder_ok = sum(1 for r in all_rows if "$T$" in r["text"])
    print(f"   含 $T$ 占位符的样本: {placeholder_ok}/{len(all_rows)}")
