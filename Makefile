.RECIPEPREFIX = >
SHELL := /bin/bash
.PHONY: provision check model analysis doctor up down ps logs
provision:
> bash scripts/provision.sh all
check:
> bash scripts/provision.sh check
model:
> bash scripts/provision.sh model
analysis:
> bash scripts/provision.sh analysis
doctor:
> bash scripts/doctor.sh
up:
> docker compose -f docker/compose.yml up -d ollama
down:
> docker compose -f docker/compose.yml down
ps:
> docker compose -f docker/compose.yml ps
logs:
> docker compose -f docker/compose.yml logs -f --tail=100
