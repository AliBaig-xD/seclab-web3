# Runbook — Box operations

Box: `ubuntu@52.23.218.124` (g4dn.xlarge, T4 16GB). Repo: `~/seclab-web3`.

## Provision / verify
```
bash scripts/provision.sh all     # docker toolchain + model + custom mythril image
bash scripts/doctor.sh            # verify every tool + GPU + deterministic model probe
```

## Model server
```
docker compose -f docker/compose.yml up -d ollama     # start (GPU)
docker start seclab-ollama / docker stop seclab-ollama
```
Ollama holds ~9GB VRAM for the 14B. Training and inference cannot share the 16GB T4, so
`scripts/train.sh` stops Ollama during training and restarts it after.

## Tests
`bash scripts/test.sh` runs the orchestrator unit tests in a clean python:3.11 container.

## Cost
Stop the EC2 instance when idle (EBS persists). Resize to a bigger GPU with no rebuild.
