# [EMNLP 2023] RethinkingTMSC

## [EMNLP 2023] RethinkingTMSC: An Empirical Study for Target-Oriented Multimodal Sentiment Classification
> Dataset and codes for paper "RethinkingTMSC: An Empirical Study for Target-Oriented Multimodal Sentiment Classification"

Junjie Ye

jjye23@m.fudan.edu.cn

Oct. 12, 2023

## Requirement
* Python 3.7+

- Run the command to install the packages required.
    ```bash
    pip install -r requirements.txt
    ```


## Download tweet images and ResNet-152
- Step 1: Download each [tweet's associated image](https://drive.google.com/file/d/1PpvvncnQkgDNeBMKVgG2zFYuRhbL873g/view).
- Step 2: Save the images to `data/Twitter15/images/` and `data/Twitter17/images/`, respectively.
- Step 3: Download the pre-trained [ResNet-152](https://download.pytorch.org/models/resnet152-b121ed2d.pth).
- Setp 4: Put the pre-trained ResNet-152 model under the folder named `Code/resnet/`.

## Prepare image features
> Since the files are too big to load, please extract them by yourself.

- Step 1: Download the pre-trained [Pretrained Faster R-CNN model](https://drive.google.com/file/d/18n_3V1rywgeADZ3oONO0DsuuS9eMW6sN/view?usp=sharing), which is trained with Visual Genome + Res101 + Pytorch and save it to the folder `Code/faster_rcnn/models/`.

- Step 2: Compile the cuda dependencies using following simple commands:

    ```bash
    cd Code/faster_rcnn
    python setup.py build develop
    ```

- Step 2: Extract the features and save them:

    ```bash
    cd Code/faster_rcnn
    python data_process.py --source_path ../../data/Twitter15/images --save_path ../../data/Twitter15/faster_features
    python data_process.py --source_path ../../data/Twitter17/images --save_path ../../data/Twitter17/faster_features
    ```


## Code Usage

### Training and Analysis
- This is the training code of tuning parameters on the dev set, and testing on the test set for all models.

    ```sh
    cd scripts
    bash run.sh
    ```

### Reminder
- You can find the results we report in our paper from the `output/` folder directly.

## Acknowledgements

- Most of the codes are based on the codes provided by huggingface: https://github.com/huggingface/transformers.

## Cite

- If you find our code is helpful, please cite our paper
```bibtex
@inproceedings{DBLP:conf/emnlp/YeZTWZG023,
  author       = {Junjie Ye and
                  Jie Zhou and
                  Junfeng Tian and
                  Rui Wang and
                  Qi Zhang and
                  Tao Gui and
                  Xuanjing Huang},
  editor       = {Houda Bouamor and
                  Juan Pino and
                  Kalika Bali},
  title        = {RethinkingTMSC: An Empirical Study for Target-Oriented Multimodal
                  Sentiment Classification},
  booktitle    = {Findings of the Association for Computational Linguistics: {EMNLP}
                  2023, Singapore, December 6-10, 2023},
  pages        = {270--277},
  publisher    = {Association for Computational Linguistics},
  year         = {2023},
  url          = {https://aclanthology.org/2023.findings-emnlp.21},
  timestamp    = {Wed, 13 Dec 2023 17:20:20 +0100},
  biburl       = {https://dblp.org/rec/conf/emnlp/YeZTWZG023.bib},
  bibsource    = {dblp computer science bibliography, https://dblp.org}
}
```

## 本仓库相对原项目的改动（复现与分析）

本仓库在原作者 [Junjie-Ye/RethinkingTMSC](https://github.com/Junjie-Ye/RethinkingTMSC)
的基础上，补充了以下内容（数据集图片与预训练权重等大文件不纳入版本库）：

### 新增
- `analysis/`：结果汇总（`collect_results.py`）、数据统计（`data_stats.py`）、
  错误分析（`error_analysis.py`）、图表生成（`make_figures.py`）、代码冒烟测试
  （`smoke_test.py`），以及由作者公开 220 组结果重新聚合的 CSV 与配图。
- `repro/`：面向 GPU 服务器的一键复现包——环境搭建（`setup_env.sh`）、资源下载
  （`download_assets.sh`）、全量运行（`run_all.sh`，支持模型过滤、断点续跑、可配置
  输出目录）、结果收集（`collect_results.py`），并附中文复现指南（`README.md`）。
- `论文/`：基于原论文的中文转述论文（Markdown 与 LaTeX 版）、项目介绍
  （`项目介绍.md`）、服务器运行手册（`服务器运行手册.md`）。
- `汇报/`：科研进展汇报 PPT 与演讲稿。

### 修改
- `requirements.txt`：移除 PyPI 上不存在的 `apex` 与 `modeling`（代码本身有 fallback，
  不影响运行），并标注 PyTorch 需按平台单独安装。
- `repro/run_all.sh`：增加 `PYTHONPATH` 导出（解决仓库根目录运行时 `No module named
  'Code'`）、`OUTPUT_ROOT` 可配置、`SKIP_EXISTING` 断点续跑、`MODELS` 模型过滤。
- `.gitignore`：新增对数据集图片、预训练权重、虚拟环境、SSH 密钥的忽略规则。

### 未纳入版本库
- `data/` 下的推文图片与原始数据集备份（tsv 标签文件保留，属于原仓库内容）；
- 预训练模型权重（`Code/resnet/*.pth`、`Code/faster_rcnn/models/*.pth` 等），请按
  `repro/download_assets.sh` 或官方 README 自行下载；
- 本地虚拟环境 `TMSC_env/` 与 SSH 密钥 `_ssh/`。
