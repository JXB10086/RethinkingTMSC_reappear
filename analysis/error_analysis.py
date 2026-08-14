# -*- coding: utf-8 -*-
"""基于作者提供 pred/true 输出做错误分析：
1) 混淆矩阵与逐类指标
2) 多模态 vs 文本基线 Bert 的纠正/恶化统计
3) 5 种子多数投票集成
4) 困难样本挖掘
"""
import os
import csv
import json
from collections import Counter, defaultdict

import numpy as np
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "output")
ANALYSIS = os.path.join(ROOT, "analysis")
SEEDS = ["0", "42", "199", "2022", "11122"]
LABELS = ["负面", "中性", "正面"]


def load_labels(path):
    with open(path) as f:
        return [int(x.strip()) for x in f if x.strip() != ""]


def load_preds(ds, model, seed):
    p = os.path.join(OUTPUT, ds, model, seed + "_output_test", "pred.txt")
    return load_labels(p)


def fmt_metric(d):
    return " / ".join(f"{v * 100:.1f}" for v in d)


report = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    report.append(s)


for ds in ("Twitter15", "Twitter17"):
    test_rows = []
    with open(os.path.join(ROOT, "data", ds, "test.tsv"), encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        for r in reader:
            if len(r) >= 5:
                test_rows.append({"label": int(r[1]), "img": r[2], "text": r[3], "target": r[4]})
    y_true = load_labels(os.path.join(OUTPUT, ds, "Bert", "0_output_test", "true.txt"))
    assert y_true == [r["label"] for r in test_rows]
    n = len(y_true)
    log("=" * 70)
    log(f"[{ds}] 测试样本数 = {n}, 真实标签分布 = {dict(sorted(Counter(y_true).items()))}")
    maj = Counter(y_true).most_common(1)[0][0]
    log(f"多数类基线: 全预测为 {LABELS[maj]} -> acc = {Counter(y_true)[maj] / n * 100:.2f}%")

    models = sorted({d for _, d in
                     [(r["model"], r["model"]) for r in
                      csv.DictReader(open(os.path.join(ANALYSIS, "results_all.csv"), encoding="utf-8-sig"))
                      if r["dataset"] == ds]})

    # ---- 种子 0 的代表性混淆矩阵 + 逐类指标 ----
    log(f"\n--- 种子 seed=0 的逐类指标 (P/R/F1 %) ---")
    rows_per_class = []
    for model in models:
        y_pred = load_preds(ds, model, "0")
        p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=[0, 1, 2], average=None)
        rows_per_class.append((model, p, r, f1))
        if model in ("Bert", "Res22Bert", "Faster22Bert", "Vit22Bert", "Bert2Vit", "VitBert", "ResBert"):
            log(f"{model:>14s} P[{fmt_metric(p)}] R[{fmt_metric(r)}] F1[{fmt_metric(f1)}]")

    # ---- 混淆矩阵: Bert vs 集成 vs 最优模型 ----
    def vote_preds(ds, model):
        preds = [load_preds(ds, model, s) for s in SEEDS]
        votes = []
        for i in range(n):
            c = Counter(preds[j][i] for j in range(len(preds)))
            votes.append(c.most_common(1)[0][0])
        return votes

    log(f"\n--- 5 种子多数投票 vs 单种子(seed=0) vs 最优单种子 ---")
    vote_rows = []
    for model in models:
        y_vote = vote_preds(ds, model)
        acc_vote = np.mean([a == b for a, b in zip(y_true, y_vote)])
        f1_vote = precision_recall_fscore_support(y_true, y_vote, average="macro")[2]
        y_s0 = load_preds(ds, model, "0")
        acc_s0 = np.mean([a == b for a, b in zip(y_true, y_s0)])
        f1_s0 = precision_recall_fscore_support(y_true, y_s0, average="macro")[2]
        vote_rows.append((model, acc_vote, f1_vote, acc_s0, f1_s0))
    vote_rows.sort(key=lambda x: -x[2])
    for model, av, fv, a0, f0 in vote_rows:
        log(f"{model:>14s} vote acc={av*100:.2f} f1={fv*100:.2f} | s0 acc={a0*100:.2f} f1={f0*100:.2f} | diff_f1={100*(fv-f0):+.2f}")

    # ---- 相对 Bert 的纠正/恶化 ----
    log(f"\n--- 相对文本基线 Bert(seed=0) 的纠正/恶化 (多模态模型, seed=0) ---")
    y_bert = load_preds(ds, "Bert", "0")
    corr_rows = []
    for model in models:
        if model == "Bert":
            continue
        y_m = load_preds(ds, model, "0")
        both_right = sum(1 for i in range(n) if y_bert[i] == y_true[i] == y_m[i])
        both_wrong = sum(1 for i in range(n) if y_bert[i] != y_true[i] and y_m[i] != y_true[i])
        correction = sum(1 for i in range(n) if y_bert[i] != y_true[i] and y_m[i] == y_true[i])
        degradation = sum(1 for i in range(n) if y_bert[i] == y_true[i] and y_m[i] != y_true[i])
        corr_rows.append((model, correction, degradation, correction - degradation, both_right, both_wrong))
    corr_rows.sort(key=lambda x: -x[3])
    for model, c, d, net, br, bw in corr_rows:
        log(f"{model:>14s} 纠正={c:4d} 恶化={d:4d} 净={net:+4d} 双对={br:4d} 双错={bw:4d}")

    # ---- 错误率与目标长度 / 共享图片 ----
    log(f"\n--- 错误率分层: 目标词数 (Bert seed=0) ---")
    tgt_len = [len(r["target"].split()) for r in test_rows]
    for lo, hi in ((1, 1), (2, 2), (3, 9)):
        idx = [i for i, l in enumerate(tgt_len) if lo <= l <= hi]
        err = sum(1 for i in idx if y_bert[i] != y_true[i])
        log(f"目标词数 {lo}-{hi}: n={len(idx)}, 错误率={err / max(len(idx),1) * 100:.1f}%")

    log(f"\n--- 困难样本: 投票集成也错 & 5 模型以上全错的样本 (前 8 条) ---")
    err_count = defaultdict(int)
    for model in models:
        yp = load_preds(ds, model, "0")
        for i in range(n):
            if yp[i] != y_true[i]:
                err_count[i] += 1
    hard = sorted(err_count.items(), key=lambda x: -x[1])[:8]
    for i, cnt in hard:
        r = test_rows[i]
        log(f"  n_models_err={cnt:2d} 真={LABELS[y_true[i]]:>2s} 文本={r['text'][:90]} | 目标={r['target']}")

    # 保存每模型 seed0 混淆矩阵为 csv 供论文
    with open(os.path.join(ANALYSIS, f"confusion_{ds}.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["model"] + [f"true_{a}_pred_{b}" for a in range(3) for b in range(3)])
        for model in models:
            yp = load_preds(ds, model, "0")
            cm = confusion_matrix(y_true, yp, labels=[0, 1, 2]).ravel()
            w.writerow([model] + list(cm))

with open(os.path.join(ANALYSIS, "error_analysis_summary.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("\nsaved error_analysis_summary.txt")
