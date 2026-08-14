#!/usr/bin/env bash
# 下载 RethinkingTMSC 复现所需的外部资源（图片、预训练权重）。
# 依赖: gdown (pip install gdown) ; 下载后请核对解压目录结构。
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> [1/4] 推文图片"
if [ -d "data/Twitter15/images" ] && [ -d "data/Twitter17/images" ] \
   && [ "$(ls -A data/Twitter15/images)" ] && [ "$(ls -A data/Twitter17/images)" ]; then
  echo "    已存在 data/Twitter15/images 与 data/Twitter17/images，跳过下载。"
else
  echo "    下载中 (Google Drive) ..."
  mkdir -p data/_downloads
  gdown 1PpvvncnQkgDNeBMKVgG2zFYuRhbL873g -O data/_downloads/tweet_images.zip
fi

echo "==> [2/4] 下载 Faster R-CNN 预训练模型 (Visual Genome + Res101)"
mkdir -p Code/faster_rcnn/models
gdown 18n_3V1rywgeADZ3oONO0DsuuS9eMW6sN -O Code/faster_rcnn/models/faster_rcnn_res101_vg.pth

echo "==> [3/4] 下载 ResNet-152 预训练权重"
mkdir -p Code/resnet
curl -L -o Code/resnet/resnet152.pth \
  https://download.pytorch.org/models/resnet152-b121ed2d.pth

echo "==> [4/4] 解压图片到 data/Twitter15/images 与 data/Twitter17/images"
python - <<'PY'
import zipfile, os, shutil
zpath = "data/_downloads/tweet_images.zip"
out15 = "data/Twitter15/images"
out17 = "data/Twitter17/images"
os.makedirs(out15, exist_ok=True)
os.makedirs(out17, exist_ok=True)
with zipfile.ZipFile(zpath) as z:
    names = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    for n in names:
        base = os.path.basename(n)
        if base in os.listdir(out15) or base in os.listdir(out17):
            continue
        # 按文件名前缀判断归属（请根据实际压缩包结构调整）
        target = out17 if base[:3].isdigit() else out15
        with z.open(n) as src, open(os.path.join(target, base), "wb") as dst:
            shutil.copyfileobj(src, dst)
    print(f"解压完成: Twitter15={len(os.listdir(out15))} 张, Twitter17={len(os.listdir(out17))} 张")
print("提示: 若数量与样本数不符，请人工核对压缩包目录结构并调整上面的归属逻辑。")
PY

echo "全部资源下载完成。下一步: bash repro/setup_env.sh"
