#!/usr/bin/env bash
# RethinkingTMSC 服务器复现环境安装脚本（Ubuntu/CentOS + NVIDIA GPU）。
# 用法: bash repro/setup_env.sh [venv路径, 默认 ./TMSC_GPU_env]
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ENV_DIR="${1:-$REPO_ROOT/TMSC_GPU_env}"
echo "环境目录: $ENV_DIR"

echo "==> [1/5] 创建虚拟环境 (python 3.8)"
PY_BIN=""
for cand in python3.9 python3.8 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver=$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    if [[ "$ver" == 3.8 || "$ver" == 3.9 ]]; then
      PY_BIN="$cand"
      break
    fi
  fi
done
if [ -z "$PY_BIN" ]; then
  echo "错误: 需要 Python 3.8 或 3.9（torch==1.10 不支持 3.10+）。"
  echo "建议: conda create -n tmsc python=3.8 && conda activate tmsc && bash repro/setup_env.sh"
  exit 1
fi
echo "使用解释器: $PY_BIN"
"$PY_BIN" -m venv "$ENV_DIR"
source "$ENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools==52.0.0 wheel

echo "==> [2/5] 安装 PyTorch 1.10 (CUDA 11.3)。"
echo "    若服务器 CUDA 为 12.x，请改用: torch==1.13.1+cu117 / torchvision==0.14.1+cu117"
pip install torch==1.10.0+cu113 torchvision==0.11.0+cu113 \
  --extra-index-url https://download.pytorch.org/whl/cu113

echo "==> [3/5] 安装 requirements.txt（已移除 apex/modeling 两个 PyPI 不存在的包）"
pip install -r requirements.txt
pip install gdown

echo "==> [4/5] 修复代码中硬编码的 /root/RethinkingTMSC 路径"
python - <<'PY'
import pathlib
p = pathlib.Path("Code/training/run_data_analysis.py")
s = p.read_text(encoding="utf-8")
root = pathlib.Path.cwd().as_posix()
if "/root/RethinkingTMSC" in s:
    s = s.replace("/root/RethinkingTMSC", root)
    p.write_text(s, encoding="utf-8")
    print(f"已替换 /root/RethinkingTMSC -> {root}")
else:
    print("未发现硬编码路径，跳过。")
PY

echo "==> [5/5] 编译 Faster R-CNN 的 CUDA 依赖（仅 Faster* 模型需要）"
if [ -f "Code/faster_rcnn/models/faster_rcnn_res101_vg.pth" ]; then
  cd Code/faster_rcnn
  python setup.py build develop || echo "警告: faster_rcnn 编译失败，可跳过 Faster* 模型（MODELS 过滤）"
  cd "$REPO_ROOT"
else
  echo "未找到 Faster R-CNN 权重，跳过编译。如后续要跑 Faster* 模型，请先执行 bash repro/download_assets.sh"
fi

echo "==> 验证"
python - <<'PY'
import torch, transformers
print("torch:", torch.__version__, "cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
print("transformers:", transformers.__version__)
PY

echo "环境就绪。开始复现: bash repro/run_all.sh"
