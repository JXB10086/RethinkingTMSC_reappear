# -*- coding: utf-8 -*-
"""代码可运行性冒烟测试（CPU，无需下载权重/图片）。

验证链路：TSV 读取 -> 数据增强特征构造(MMInputFeatures) -> BERT 前向/反向 ->
优化器更新 -> 多模态模型前向。使用随机初始化的微型 BERT 与随机图像特征，
不构成任何性能复现，仅验证代码路径可执行。
"""
import os
import sys
import re
import random

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import Code.training.run_data_analysis as rda
import Code.training.mm_modeling as mmm
from Code.training.tokenization import BertTokenizer

random.seed(0)
np.random.seed(0)
torch.manual_seed(0)

ANALYSIS = os.path.join(ROOT, "analysis")
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


# ---------- 1. 构造微型词表 ----------
vocab_path = os.path.join(ANALYSIS, "_smoke_vocab.txt")
processor = rda.AbmsaProcessor()
dev_examples = processor.get_dev_examples(os.path.join(ROOT, "data", "Twitter15"))[:8]
words = set()
for e in dev_examples:
    for w in re.split(r"\W+", (e.text_a + " " + e.text_b).lower()):
        if w:
            words.add(w)
vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + sorted(words)
with open(vocab_path, "w", encoding="utf-8") as f:
    f.write("\n".join(vocab))
log(f"[1] 微型词表大小 = {len(vocab)} -> {vocab_path}")

# ---------- 2. 数据读取与特征构造（图像用随机张量代替） ----------
def fake_image_process(image_path, transform, encoder="resnet", num_box=36):
    if encoder == "faster":
        return torch.rand(num_box, 2048)
    return torch.rand(3, 224, 224)

rda.image_process = fake_image_process

tokenizer = BertTokenizer(vocab_file=vocab_path, do_lower_case=True)
features = rda.convert_mm_examples_to_features(
    dev_examples, processor.get_labels(), max_seq_length=32, max_entity_length=8,
    tokenizer=tokenizer, crop_size=224, path_img="<dummy>", encoder="resnet")
log(f"[2] 特征构造完成: {len(features)} 条, 每条含 "
    f"input_ids({len(features[0].input_ids)}) / img_feat({tuple(features[0].img_feat.shape)})")

def tensors(feats):
    return dict(
        input_ids=torch.tensor([f.input_ids for f in feats], dtype=torch.long),
        input_mask=torch.tensor([f.input_mask for f in feats], dtype=torch.long),
        added_mask=torch.tensor([f.added_input_mask for f in feats], dtype=torch.long),
        segment_ids=torch.tensor([f.segment_ids for f in feats], dtype=torch.long),
        s2_ids=torch.tensor([f.s2_input_ids for f in feats], dtype=torch.long),
        s2_mask=torch.tensor([f.s2_input_mask for f in feats], dtype=torch.long),
        s2_seg=torch.tensor([f.s2_segment_ids for f in feats], dtype=torch.long),
        img=torch.stack([f.img_feat for f in feats]),
        labels=torch.tensor([f.label_id for f in feats], dtype=torch.long),
    )

t = tensors(features)

# ---------- 3. 微型 BERT 训练两步 ----------
config = mmm.BertConfig(len(vocab), hidden_size=64, num_hidden_layers=2,
                        num_attention_heads=4, intermediate_size=256,
                        max_position_embeddings=64, type_vocab_size=2)
model = mmm.BertForSequenceClassification(config, num_labels=3)
optimizer = rda.BertAdam(list(model.parameters()), lr=2e-5, warmup=0.1, t_total=8)

bs = 4
losses = []
model.train()
for step in range(2):
    sl = slice(step * bs, (step + 1) * bs)
    loss = model(t["input_ids"][sl], t["s2_ids"][sl], t["img"][sl],
                 t["segment_ids"][sl], t["s2_seg"][sl], t["input_mask"][sl],
                 t["s2_mask"][sl], t["added_mask"][sl], t["labels"][sl])
    losses.append(float(loss))
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
log(f"[3] BERT 训练两步完成, loss = {[f'{x:.4f}' for x in losses]}, "
    f"梯度正常 = {any(p.grad is not None for p in model.parameters())}")

# ---------- 4. 推理前向 ----------
model.eval()
with torch.no_grad():
    logits = model(t["input_ids"][:bs], t["s2_ids"][:bs], t["img"][:bs],
                   t["segment_ids"][:bs], t["s2_seg"][:bs], t["input_mask"][:bs],
                   t["s2_mask"][:bs], t["added_mask"][:bs])
log(f"[4] BERT 推理 logits 形状 = {tuple(logits.shape)}, 类别分布 = "
    f"{torch.unique(logits.argmax(-1), return_counts=True)[1].tolist()}")

# ---------- 5. 多模态模型 Res22Bert 前向/反向 ----------
mm = mmm.Res22BertForMMSequenceClassification(config, num_labels=3)
visual = torch.rand(bs, 2048 * 49)
loss_mm = mm(t["input_ids"][:bs], t["s2_ids"][:bs], visual,
             t["segment_ids"][:bs], t["s2_seg"][:bs], t["input_mask"][:bs],
             t["s2_mask"][:bs], t["added_mask"][:bs], t["labels"][:bs])
log(f"[5] Res22Bert(文本+图像交叉注意力) 前向/反向 loss = {float(loss_mm):.4f}")

# ---------- 6. 真实图片加载验证（resnet 路径） ----------
from torchvision import transforms
real_transform = transforms.Compose([
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))])
for ds, fname in (("Twitter15", "1860693.jpg"), ("Twitter17", "17_06_10389.jpg")):
    p = os.path.join(ROOT, "data", ds, "images", fname)
    img = rda.image_process(p, real_transform, "resnet")
    log(f"[6] 真实图片加载 {ds}/{fname}: 形状 {tuple(img.shape)}, "
        f"数值范围 [{float(img.min()):.2f}, {float(img.max()):.2f}]")

with open(os.path.join(ANALYSIS, "smoke_test_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
log("冒烟测试全部通过 -> analysis/smoke_test_log.txt")
