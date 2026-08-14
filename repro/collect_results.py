#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在服务器上汇总复现结果。
用法: python repro/collect_results.py [输出根目录, 默认 Code/output]
生成 <根目录>/results_all.csv 与 results_summary.csv，可拷回本仓库 output/ 后
复用 analysis/ 下的统计与作图脚本。
"""
import os
import sys
import csv
import statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "Code", "output")
SEEDS = ["0", "42", "199", "2022", "11122"]


def parse_eval(path):
    d = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                d[k.strip()] = float(v.strip())
    return d


rows = []
for ds in sorted(os.listdir(OUTPUT)):
    ds_dir = os.path.join(OUTPUT, ds)
    if not os.path.isdir(ds_dir):
        continue
    for model in sorted(os.listdir(ds_dir)):
        for seed in SEEDS:
            ef = os.path.join(ds_dir, model, seed + "_output_test", "eval_results.txt")
            if not os.path.exists(ef):
                continue
            r = parse_eval(ef)
            rows.append({"dataset": ds, "model": model, "seed": seed,
                         "accuracy": r.get("eval_accuracy"), "f1": r.get("f_score"),
                         "precision": r.get("precision"), "recall": r.get("recall")})

with open(os.path.join(OUTPUT, "results_all.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "model", "seed", "accuracy", "f1", "precision", "recall"])
    w.writeheader()
    w.writerows(rows)

summary = defaultdict(list)
for r in rows:
    summary[(r["dataset"], r["model"])].append(r)
with open(os.path.join(OUTPUT, "results_summary.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["dataset", "model", "acc_mean", "acc_std", "f1_mean", "f1_std", "n_seeds"])
    for (ds, model) in sorted(summary):
        rs = summary[(ds, model)]
        w.writerow([ds, model,
                    f"{st.mean(r['accuracy'] for r in rs):.4f}", f"{st.stdev(r['accuracy'] for r in rs):.4f}",
                    f"{st.mean(r['f1'] for r in rs):.4f}", f"{st.stdev(r['f1'] for r in rs):.4f}",
                    len(rs)])
print(f"汇总 {len(rows)} 次运行 -> {OUTPUT}/results_all.csv")
