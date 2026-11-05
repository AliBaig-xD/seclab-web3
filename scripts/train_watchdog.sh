#!/usr/bin/env bash
# Keeps training alive: if the training pipeline dies before writing its exit marker,
# resume from the last checkpoint. Treats the post-train eval phase as alive. Capped.
cd "$(dirname "$0")/.."
RESTARTS=0; MAX=8
log(){ echo "[watchdog] $(date -u +%H:%M:%SZ) $*" >> results/watchdog.log; }
log "started"
sleep 60   # let the current run settle before first check
while true; do
  if grep -q 'TRAIN_EXIT=0' results/train_prod.log 2>/dev/null; then
    log "training pipeline exited (marker present); done watching"; break
  fi
  if pgrep -f 'training/finetune.py' >/dev/null 2>&1 || pgrep -f 'training/evaluate.py' >/dev/null 2>&1; then
    :   # alive (training or evaluating)
  else
    if [ "$RESTARTS" -ge "$MAX" ]; then log "hit MAX restarts ($MAX); stopping"; break; fi
    RESTARTS=$((RESTARTS+1)); log "pipeline down, no exit marker -> restart #$RESTARTS"
    tmux kill-session -t train 2>/dev/null || true
    if ls model/adapters/checkpoint-* >/dev/null 2>&1; then
      tmux new-session -d -s train 'scripts/resume_train.sh > results/train_prod.log 2>&1; echo "TRAIN_EXIT=$?" >> results/train_prod.log'
    else
      tmux new-session -d -s train 'scripts/train.sh > results/train_prod.log 2>&1; echo "TRAIN_EXIT=$?" >> results/train_prod.log'
    fi
    sleep 150
  fi
  sleep 300
done
