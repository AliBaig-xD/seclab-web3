#!/usr/bin/env bash
# Verify every component; fail loudly on any miss. Writes a timestamped report.
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; source config/versions.env; set +a
mkdir -p results
TS=$(date +%Y%m%d-%H%M%S); OUT="results/doctor-$TS.txt"
fail=0
ok(){ echo "OK   $*"  | tee -a "$OUT"; }
bad(){ echo "MISS $*" | tee -a "$OUT"; fail=1; }
echo "seclab-web3 doctor $TS" | tee "$OUT"

docker version >/dev/null 2>&1 && ok "docker $(docker version --format '{{.Server.Version}}')" || bad docker
nvidia-smi -L >/dev/null 2>&1 && ok "gpu $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)" || bad gpu

if curl -sf http://127.0.0.1:11434/api/version >/dev/null; then
  ok "ollama up"
  docker exec seclab-ollama ollama list 2>/dev/null | grep -q "${MODEL_REF%%:*}" && ok "model $MODEL_REF present" || bad "model $MODEL_REF"
  resp=$(curl -sf http://127.0.0.1:11434/api/generate -d "{\"model\":\"$MODEL_REF\",\"prompt\":\"Reply with one word: REENTRANCY\",\"stream\":false,\"options\":{\"temperature\":0,\"seed\":0}}" | jq -r '.response' 2>/dev/null | tr -d '\n')
  echo "model-probe: ${resp:0:80}" | tee -a "$OUT"
else bad ollama; fi

IMG=seclab-web3/analysis:latest
if docker image inspect "$IMG" >/dev/null 2>&1; then
  for cmd in "forge --version" "anvil --version" "cast --version" "slither --version" \
             "semgrep --version" "halmos --version" \
             "echidna --version" "medusa --version" "aderyn --version" "solc --version"; do
    out=$(docker run --rm "$IMG" bash -lc "$cmd" 2>&1 | head -1)
    if [ -n "$out" ] && ! echo "$out" | grep -qiE "not found|no such|error"; then ok "${cmd%% *}: $out"; else bad "${cmd%% *} ($out)"; fi
  done
else bad "analysis image"; fi

# isolated mythril image
mv=$(docker run --rm mythril/myth version 2>&1 | head -1)
if [ -n "$mv" ] && ! echo "$mv" | grep -qiE "no such|not found|error|unable"; then ok "mythril: $mv"; else bad "mythril image ($mv)"; fi

echo "---" | tee -a "$OUT"
if [ $fail -eq 0 ]; then echo "DOCTOR: ALL GREEN" | tee -a "$OUT"; else echo "DOCTOR: MISSING ITEMS" | tee -a "$OUT"; fi
echo "report: $OUT"
exit $fail
