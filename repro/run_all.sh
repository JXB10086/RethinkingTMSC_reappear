#!/usr/bin/env bash
# 全量复现 RethinkingTMSC：对 2 个数据集 x 22 个模型进行训练与测试。
# 默认只跑 1 个随机种子（seed=0），新结果输出到 OUTPUT_ROOT（默认数据盘新目录）。
# 用法示例:
#   bash repro/run_all.sh                          # 全部模型
#   MODELS="Bert" bash repro/run_all.sh            # 只跑文本基线（快速验证管线）
#   SEEDS="0 42 199 2022 11122" bash repro/run_all.sh  # 恢复 5 种子
#   DEVICES=0,1 bash repro/run_all.sh              # 使用两张卡（简单按轮次交替）
#   SKIP_EXISTING=1 bash repro/run_all.sh          # 跳过已有输出（断点续跑）
set -u
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
# 服务器直连 huggingface.co 会超时，默认走国内镜像；可自行覆盖
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

DEVICES="${DEVICES:-0}"
LR="${LR:-2e-5}"
EPOCHS="${EPOCHS:-8.0}"
SEEDS="${SEEDS:-0}"
DATASETS="${DATASETS:-Twitter15 Twitter17}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/autodl-fs/data/RethinkingTMSC_output_1seed}"
MODELS="${MODELS:-}"

if [ -n "$MODELS" ]; then
  ALL_MODELS="$MODELS"
else
  ALL_MODELS="Bert ResNet ResBert ResBertTFN Res2Bert Bert2Res Res22Bert ResBertAtt \
Vit VitBert VitBertTFN Vit2Bert Bert2Vit Vit22Bert VitBertAtt \
FasterRCNN FasterBert FasterBertTFN Faster2Bert Bert2Faster Faster22Bert FasterBertAtt"
fi

enc_for() {
  case "$1" in
    *2Vit)     echo vit ;;
    *2Faster)  echo faster ;;
    Bert|Res*) echo resnet ;;
    Vit*)      echo vit ;;
    Faster*)   echo faster ;;
    *)         echo resnet ;;
  esac
}

mkdir -p logs
DEVICE_ARR=(${DEVICES//,/ })
NDEV=${#DEVICE_ARR[@]}
job_idx=0

run_one() {
  local ds=$1 model=$2 enc=$3 seed=$4 device=$5
  local out="${OUTPUT_ROOT}/${ds}/${model}/${seed}_output_test"
  if [ "$SKIP_EXISTING" = "1" ] && { [ -f "$out/eval_results_test.txt" ] || [ -f "$out/eval_results.txt" ]; }; then
    echo "[skip] $ds/$model/$seed 已存在"
    return 0
  fi
  echo "[run ] $ds/$model/$seed (encoder=$enc, device=$device, lr=$LR, epochs=$EPOCHS)"
  PYTHONIOENCODING=utf-8 CUDA_VISIBLE_DEVICES="$device" python Code/training/run_data_analysis.py \
    --data_dir "data/${ds}" \
    --task_name "$ds" \
    --output_dir "$out" \
    --learning_rate "$LR" \
    --seed "$seed" \
    --test_file test.tsv \
    --bert_model bert-base-uncased \
    --encoder "$enc" \
    --do_train --do_eval \
    --train_batch_size 32 \
    --mm_model "$model" \
    --num_train_epochs "$EPOCHS" \
    --resnet_root "$REPO_ROOT/Code/resnet" \
    > "logs/${ds}_${model}_${seed}.log" 2>&1 || {
      echo "[FAIL] $ds/$model/$seed 见 logs/${ds}_${model}_${seed}.log"
      return 1
    }
  echo "[done] $ds/$model/$seed"
}

for ds in $DATASETS; do
  for model in $ALL_MODELS; do
    enc="$(enc_for "$model")"
    for seed in $SEEDS; do
      dev="${DEVICE_ARR[$((job_idx % NDEV))]}"
      run_one "$ds" "$model" "$enc" "$seed" "$dev" &
      job_idx=$((job_idx + 1))
      # 并发任务数 = GPU 数，等待一批完成再继续
      if (( job_idx % NDEV == 0 )); then
        wait
      fi
    done
  done
done
wait

echo "全部完成，汇总结果:"
python repro/collect_results.py "$OUTPUT_ROOT"
