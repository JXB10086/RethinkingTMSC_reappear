# -*- coding: utf-8 -*-
"""生成论文配图（中文标签）。"""
import os
import csv
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from sklearn.metrics import confusion_matrix

# 中文字体
for f in ("Microsoft YaHei", "SimHei", "SimSun", "DengXian"):
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "output")
FIG = os.path.join(ROOT, "analysis", "figures")
os.makedirs(FIG, exist_ok=True)

FAMILY = {
    "Bert": "文本", "ResNet": "ResNet", "ResBert": "ResNet", "ResBertTFN": "ResNet",
    "Res2Bert": "ResNet", "Bert2Res": "ResNet", "Res22Bert": "ResNet", "ResBertAtt": "ResNet",
    "Vit": "ViT", "VitBert": "ViT", "VitBertTFN": "ViT", "Vit2Bert": "ViT",
    "Bert2Vit": "ViT", "Vit22Bert": "ViT", "VitBertAtt": "ViT",
    "FasterRCNN": "Faster", "FasterBert": "Faster", "FasterBertTFN": "Faster",
    "Faster2Bert": "Faster", "Bert2Faster": "Faster", "Faster22Bert": "Faster",
    "FasterBertAtt": "Faster",
}
COLOR = {"文本": "#4C72B0", "ResNet": "#DD8452", "ViT": "#55A868", "Faster": "#C44E52"}
ORDER = ["Bert", "ResNet", "ResBert", "ResBertTFN", "Res2Bert", "Bert2Res", "Res22Bert", "ResBertAtt",
         "Vit", "VitBert", "VitBertTFN", "Vit2Bert", "Bert2Vit", "Vit22Bert", "VitBertAtt",
         "FasterRCNN", "FasterBert", "FasterBertTFN", "Faster2Bert", "Bert2Faster", "Faster22Bert", "FasterBertAtt"]

with open(os.path.join(ROOT, "analysis", "results_all.csv"), encoding="utf-8-sig") as f:
    all_rows = list(csv.DictReader(f))

summary = {}
for r in all_rows:
    key = (r["dataset"], r["model"])
    summary.setdefault(key, []).append(r)

SEEDS = ["0", "42", "199", "2022", "11122"]


def load_preds(ds, model, seed):
    with open(os.path.join(OUTPUT, ds, model, seed + "_output_test", "pred.txt")) as f:
        return [int(x.strip()) for x in f if x.strip()]


# ---- 图1: 每数据集 模型 F1 均值±标准差 ----
fig, axes = plt.subplots(1, 2, figsize=(15, 7.5), sharex=False)
for ax, ds in zip(axes, ("Twitter15", "Twitter17")):
    models = [m for m in ORDER if (ds, m) in summary]
    f1s = [np.mean([float(r["f1"]) for r in summary[(ds, m)]]) * 100 for m in models]
    f1std = [np.std([float(r["f1"]) for r in summary[(ds, m)]]) * 100 for m in models]
    colors = [COLOR[FAMILY[m]] for m in models]
    y = np.arange(len(models))[::-1]
    ax.barh(y, f1s, xerr=f1std, color=colors, height=0.7, capsize=2, error_kw=dict(lw=0.8))
    ax.set_yticks(y, models, fontsize=9)
    ax.set_xlabel("Macro-F1 (%)")
    ax.set_title(ds, fontsize=13)
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlim(25, 80)
from matplotlib.patches import Patch
legend = [Patch(color=COLOR[k], label=k) for k in ("文本", "ResNet", "ViT", "Faster")]
fig.legend(handles=legend, loc="lower center", ncol=4, frameon=False, fontsize=11)
fig.suptitle("各模型 5 种子的 Macro-F1 均值与标准差", fontsize=14)
fig.tight_layout(rect=[0, 0.04, 1, 0.96])
fig.savefig(os.path.join(FIG, "fig1_f1_by_model.png"), dpi=150)
plt.close(fig)

# ---- 图2: 文本基线 Bert 与最优多模态的混淆矩阵 ----
for ds, best in (("Twitter15", "Res22Bert"), ("Twitter17", "Bert2Res")):
    with open(os.path.join(OUTPUT, ds, "Bert", "0_output_test", "true.txt")) as f:
        y_true = [int(x.strip()) for x in f if x.strip()]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    for ax, (m, title) in zip(axes, (("Bert", "文本基线 BERT"), (best, f"多模态 {best}"))):
        yp = load_preds(ds, m, "0")
        cm = confusion_matrix(y_true, yp, labels=[0, 1, 2])
        cm_n = cm / cm.sum(axis=1, keepdims=True)
        im = ax.imshow(cm_n, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks([0, 1, 2], ["负面", "中性", "正面"])
        ax.set_yticks([0, 1, 2], ["负面", "中性", "正面"])
        ax.set_xlabel("预测")
        ax.set_ylabel("真实")
        ax.set_title(f"{title} (acc={np.mean([a==b for a,b in zip(y_true,yp)])*100:.1f}%)")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{cm[i,j]}\n({cm_n[i,j]*100:.0f}%)", ha="center", va="center",
                        fontsize=8, color="white" if cm_n[i, j] > 0.55 else "black")
    fig.colorbar(im, ax=axes, fraction=0.035)
    fig.suptitle(f"{ds} 混淆矩阵 (seed=0)", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"fig2_confusion_{ds}.png"), dpi=150)
    plt.close(fig)

# ---- 图3: 相对 Bert 的纠正/恶化净效应 ----
fig, axes = plt.subplots(1, 2, figsize=(15, 7))
for ax, ds in zip(axes, ("Twitter15", "Twitter17")):
    y_bert = load_preds(ds, "Bert", "0")
    with open(os.path.join(OUTPUT, ds, "Bert", "0_output_test", "true.txt")) as f:
        y_true = [int(x.strip()) for x in f if x.strip()]
    n = len(y_true)
    nets = []
    for m in ORDER:
        if m == "Bert":
            continue
        y_m = load_preds(ds, m, "0")
        corr = sum(1 for i in range(n) if y_bert[i] != y_true[i] and y_m[i] == y_true[i])
        degr = sum(1 for i in range(n) if y_bert[i] == y_true[i] and y_m[i] != y_true[i])
        nets.append((m, corr - degr))
    nets.sort(key=lambda x: x[1])
    models = [x[0] for x in nets]
    vals = [x[1] for x in nets]
    colors = [COLOR[FAMILY[m]] for m in models]
    ax.barh(np.arange(len(models)), vals, color=colors, height=0.7)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(np.arange(len(models)), models, fontsize=9)
    ax.set_xlabel("纠正数 - 恶化数 (相对 BERT, seed=0)")
    ax.set_title(ds, fontsize=13)
    ax.grid(axis="x", alpha=0.3)
fig.suptitle("多模态模型相对文本基线 BERT 的净纠正样本数", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(FIG, "fig3_correction_net.png"), dpi=150)
plt.close(fig)

# ---- 图4: 5 种子投票集成 vs 单种子 seed=0 ----
fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
for ax, ds in zip(axes, ("Twitter15", "Twitter17")):
    with open(os.path.join(OUTPUT, ds, "Bert", "0_output_test", "true.txt")) as f:
        y_true = [int(x.strip()) for x in f if x.strip()]
    x, y, labels = [], [], []
    for m in ORDER:
        if (ds, m) not in summary:
            continue
        preds = [load_preds(ds, m, s) for s in SEEDS]
        votes = [Counter(p[j] for p in preds).most_common(1)[0][0] for j in range(len(y_true))]
        from sklearn.metrics import precision_recall_fscore_support
        f1_vote = precision_recall_fscore_support(y_true, votes, average="macro")[2] * 100
        y0 = load_preds(ds, m, "0")
        f1_s0 = precision_recall_fscore_support(y_true, y0, average="macro")[2] * 100
        x.append(f1_s0); y.append(f1_vote); labels.append(m)
    ax.scatter(x, y, c=[COLOR[FAMILY[m]] for m in labels], s=38)
    for xi, yi, m in zip(x, y, labels):
        ax.annotate(m, (xi, yi), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
    lim = (min(x + y) - 2, max(x + y) + 2)
    ax.plot(lim, lim, "--", color="gray", lw=0.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("单种子 seed=0 的 Macro-F1 (%)")
    ax.set_ylabel("5 种子投票集成的 Macro-F1 (%)")
    ax.set_title(ds, fontsize=13)
    ax.grid(alpha=0.3)
fig.suptitle("种子集成收益（对角线以上代表集成更好）", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(FIG, "fig4_ensemble.png"), dpi=150)
plt.close(fig)

# ---- 图5: 数据标签分布与图片共享 ----
import csv as _csv
def load_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in _csv.reader(f, delimiter="\t"):
            if len(r) >= 5 and r[1] in ("0", "1", "2"):
                rows.append({"label": int(r[1]), "img": r[2]})
    return rows

fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
for ax, ds in zip(axes, ("Twitter15", "Twitter17")):
    splits = ("train", "dev", "test")
    data = [load_tsv(os.path.join(ROOT, "data", ds, s + ".tsv")) for s in splits]
    width = 0.26
    xs = np.arange(3)
    for lab, color in zip((0, 1, 2), ("#C44E52", "#8C8C8C", "#55A868")):
        fracs = [sum(1 for r in d if r["label"] == lab) / len(d) * 100 for d in data]
        ax.bar(xs + (lab - 1) * width, fracs, width, label=["负面", "中性", "正面"][lab], color=color)
    ax.set_xticks(xs, ["train", "dev", "test"])
    ax.set_ylabel("占比 (%)")
    ax.set_title(ds, fontsize=13)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
fig.suptitle("训练/开发/测试集标签分布", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(os.path.join(FIG, "fig5_label_dist.png"), dpi=150)
plt.close(fig)

print("figures saved to", FIG)
