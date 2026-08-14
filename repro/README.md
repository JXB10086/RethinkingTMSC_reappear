# RethinkingTMSC 服务器复现指南（中文）

本目录为在**租用的 GPU 服务器（Linux）**上完整复现
[RethinkingTMSC（EMNLP 2023 Findings）](https://aclanthology.org/2023.findings-emnlp.21/)
而准备的一键式脚本与注意事项。本机（Windows，CPU-only）无法完成完整复现，
但代码链路已经过冒烟验证（见 `../analysis/smoke_test_log.txt`）。

## 1. 硬件与软件要求

- Linux + NVIDIA GPU（显存 ≥ 11GB 更稳妥；BERT-base + batch=32 大约需 8GB）
- CUDA 11.3（或 12.x，需相应调整 PyTorch 版本，见 setup 脚本注释）
- Python 3.8
- 磁盘空间：图片约 1–2GB，BERT/ResNet/ViT 权重与中间输出另需数 GB

## 2. 三步复现

> 提示：本仓库 `data/Twitter15/images/`（3502 张）与 `data/Twitter17/images/`
> （2908 张）**已就绪**（来源为原始 IJCAI2019 数据集，已与 tsv 的 ImageID 逐张核对，
> 缺失 0 张）。第一步可跳过图片下载，只需下载两个预训练权重。

```bash
# ① 下载外部资源（推文图片若已就绪可跳过；ResNet-152、Faster R-CNN 权重必需）
bash repro/download_assets.sh

# ② 安装环境（自动修复代码中硬编码的 /root/RethinkingTMSC 路径、编译 faster_rcnn）
bash repro/setup_env.sh

# ③ 全量复现（2 数据集 × 22 模型 × 5 种子 = 220 次训练）
bash repro/run_all.sh
```

常用变体：

```bash
# 只跑文本基线 BERT（先验证管线，约半小时~1小时）
MODELS="Bert" bash repro/run_all.sh

# 双卡并行 + 断点续跑（已有输出自动跳过）
DEVICES=0,1 SKIP_EXISTING=1 bash repro/run_all.sh

# 只跑某类模型
MODELS="Res22Bert Bert2Vit" bash repro/run_all.sh
```

运行日志在 `logs/`，每个实验输出在 `Code/output/<数据集>/<模型>/<种子>_output_test/`
（含 `eval_results.txt`、`pred.txt`、`true.txt`）。

## 3. 结果回收

```bash
python repro/collect_results.py Code/output
# 生成 Code/output/results_all.csv 与 results_summary.csv
```

把 `Code/output/` 下的结果拷回本仓库的 `output/` 后，
本机已有的分析脚本（`analysis/collect_results.py`、`analysis/error_analysis.py`、
`analysis/make_figures.py`）可直接重新生成统计表与论文配图。

## 4. 原项目里的坑（复现前必读）

1. **硬编码路径**：`Code/training/run_data_analysis.py` 对 Twitter15/17 的图片目录
   写死了 `/root/RethinkingTMSC/...`，不位于该路径时会直接找不到图片。
   `setup_env.sh` 会自动把该前缀替换为仓库实际路径。
2. **run.sh 的 CWD**：README 写的是 `cd scripts && bash run.sh`，但脚本内的相对路径
   （`Code/training/...`、`data/...`）要求**在仓库根目录执行** `bash scripts/run.sh`。
   本目录的 `run_all.sh` 已按根目录方式实现。
3. **ResNet-152 路径与文件名**：`--resnet_root` 默认是 `./resnet`，而 README 要求权重放在
   `Code/resnet/`，且代码固定读取文件名 `resnet152.pth`。若在根目录执行，必须显式传
   `--resnet_root Code/resnet`（本脚本已处理），并把权重命名为 `Code/resnet/resnet152.pth`。
4. **依赖缺失**：requirements.txt 里的 `apex` 与 `modeling` 在 PyPI 上不存在，
   代码本身有 fallback（无 apex 也可训练），本仓库的 requirements.txt 已移除这两项。
5. **Faster* 模型**：`Code/faster_rcnn/data_process.py` 固定读取
   `Code/faster_rcnn/models/faster_rcnn_res101_vg.pth`（Visual Genome + Res101 预训练
   权重，请按此路径与文件名放置），用该脚本从原图提取 `faster_features/*.json`
   （需要编译 CUDA 依赖）。若编译失败，可用 `MODELS` 过滤跳过 Faster* 模型，
   不影响 BERT/ResNet/ViT 系复现。
6. **图片归属**：`download_assets.sh` 解压时按文件名前缀把图片分到
   Twitter15/Twitter17 两个目录。本仓库已用 `data/twitter2015_images/` 与
   `data/twitter2017_images/`（原始 IJCAI2019 数据集）的图片整理完毕并逐张核对
   （Twitter15 3502 张、Twitter17 2908 张，缺失 0），无需再下载图片；若使用其他来源，
   请务必核对图片数量与 tsv 中的 ImageID 是否一一对应。
7. **评测口径**：训练 8 个 epoch，batch=32，学习率 2e-5，5 个种子
   （0/42/199/2022/11122）；`run_data_analysis.py` 训练中在 dev 上选最优、最后在 test 上评测，
   `eval_results.txt` 即为 test 结果。

## 5. 预期结果对照

作者随仓库提供了 `output/`（即论文报告结果）。复现完成后，可将自己跑的
`results_summary.csv` 与 `analysis/results_summary.csv` 对比：
同种子下 F1 偏差通常在 ±1 个百分点以内可视为复现成功；若偏差较大，
优先检查图片数据完整性、CUDA 版本与随机数环境。
