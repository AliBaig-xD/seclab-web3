#!/usr/bin/env bash
# Keeps training alive: if finetune dies before finishing, resume from the last checkpoint.
# Caps restarts to avoid an infinite crash loop. Runs in its own tmux session.
cd "$(dirname "$0")/.."
RESTARTS=0; MAX=8
log(){ echo "[watchdog] $(date -u +%H:%M:%SZ) $*" >> results/watchdog.log; }
log "started"
while true; do
  if grep -q 'TRAIN_EXIT=0' results/train_prod.log 2>/dev/null || [ -f model/adapters/adapter_model.safetensors ]; then
    log "training finished cleanly"; break
  fi
  if ! pgrep -f training/finetune.py >/dev/null 2>&1; then
    if [ "$RESTARTS" -ge "$MAX" ]; then log "hit MAX restarts ($MAX); giving up"; break; fi
    RESTARTS=$((RESTARTS+1)); log "training down -> restart #$RESTARTS"
    tmux kill-session -t train 2>/dev/null || true
    if ls model/adapters/checkpoint-* >/dev/null 2>&1; then
      tmux new-session -d -s train 'scripts/resume_train.sh > results/train_prod.log 2>&1; echo "TRAIN_EXIT=$?" >> results/train_prod.log'
    else
      tmux new-session -d -s train 'scripts/train.sh > results/train_prod.log 2>&1; echo "TRAIN_EXIT=$?" >> results/train_prod.log'
    fi
    sleep 120
  fi
  sleep 300
done
