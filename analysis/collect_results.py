# -*- coding: utf-8 -*-
"""汇总 output/ 下所有 eval_results.txt，生成总表与按模型/数据集汇总统计。"""
import os
import csv
import statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "output")
ANALYSIS = os.path.join(ROOT, "analysis")
os.makedirs(ANALYSIS, exist_ok=True)

SEEDS = ["0", "42", "199", "2022", "11122"]


def parse_eval(path):
    d = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip()] = float(v.strip())
    return d


rows = []
for ds in ("Twitter15", "Twitter17"):
    ds_dir = os.path.join(OUTPUT, ds)
    for model in sorted(os.listdir(ds_dir)):
        for seed in SEEDS:
            run_dir = os.path.join(ds_dir, model, seed + "_output_test")
            eval_file = os.path.join(run_dir, "eval_results.txt")
            if not os.path.exists(eval_file):
                continue
            r = parse_eval(eval_file)
            rows.append({
                "dataset": ds,
                "model": model,
                "seed": seed,
                "accuracy": r.get("eval_accuracy"),
                "f1": r.get("f_score"),
                "precision": r.get("precision"),
                "recall": r.get("recall"),
                "eval_loss": r.get("eval_loss"),
                "global_step": r.get("global_step"),
            })

with open(os.path.join(ANALYSIS, "results_all.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# 汇总：数据集 x 模型 的 5 种子统计
summary = defaultdict(list)
for r in rows:
    summary[(r["dataset"], r["model"])].append(r)

with open(os.path.join(ANALYSIS, "results_summary.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["dataset", "model", "acc_mean", "acc_std", "acc_min", "acc_max",
                "f1_mean", "f1_std", "f1_min", "f1_max",
                "prec_mean", "rec_mean", "best_seed_acc", "best_seed_f1"])
    for (ds, model) in sorted(summary.keys()):
        rs = summary[(ds, model)]
        accs = [r["accuracy"] for r in rs]
        f1s = [r["f1"] for r in rs]
        precs = [r["precision"] for r in rs]
        recs = [r["recall"] for r in rs]
        best_acc = max(rs, key=lambda r: r["accuracy"])
        best_f1 = max(rs, key=lambda r: r["f1"])
        w.writerow([ds, model,
                    f"{st.mean(accs):.4f}", f"{st.stdev(accs):.4f}", f"{min(accs):.4f}", f"{max(accs):.4f}",
                    f"{st.mean(f1s):.4f}", f"{st.stdev(f1s):.4f}", f"{min(f1s):.4f}", f"{max(f1s):.4f}",
                    f"{st.mean(precs):.4f}", f"{st.mean(recs):.4f}",
                    best_acc["seed"] + f"({best_acc['accuracy']:.4f})",
                    best_f1["seed"] + f"({best_f1['f1']:.4f})"])

print(f"parsed {len(rows)} runs")
print(f"wrote {ANALYSIS}/results_all.csv and results_summary.csv")
