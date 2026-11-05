# Using the lab (end-user guide)

The lab takes a **target**, discovers every contract in it, and hunts for bugs it can
*prove*. You never hand-pick contracts — point it at a thing, it does the rest.

## 1. One target — `seclab go <anything>`

```
seclab go https://github.com/org/protocol          # a repo (best: exact compiler settings)
seclab go https://etherscan.io/address/0xC02a...    # an explorer URL (chain auto-detected)
seclab go 0xC02aaA39...756Cc2 --chain 1             # a raw address
seclab go ./my-protocol                             # a local folder
```

A dApp *frontend* URL (e.g. `app.uniswap.org`) can't be scanned directly — a frontend
isn't the contracts. Use its repo or its deployed address instead; `go` tells you so.

### Engine depth (this is what controls runtime, not the target)

| flags | what runs | ~time on 1 small contract | use when |
|-------|-----------|---------------------------|----------|
| `--fast` | static only (Slither/Aderyn/Semgrep) | seconds | triage a big list cheaply |
| *(default)* | static + symbolic + fuzz | minutes | a normal pass |
| `--llm --swarm --rag --exploit` | + AI hunter, graph-sliced swarm, RAG, auto-PoC | minutes–hours | a real audit |
| `--thorough` | multi-sample + reviewer voting | more | highest recall |

`--fast` on WETH takes ~5s because WETH is ~150 lines and nothing deep runs. A real
audit of a protocol with `--llm --swarm --exploit` is minutes to hours. **The 20-second
number is triage, not a scan.**

Every target needs an authorization `--basis`: `own`, `bounty:<program>`, or
`engagement:<id>`. PoCs only ever run on a sandboxed Anvil fork — never broadcast.

## 2. Many targets — harvest a corpus, then batch

Don't hand-pick. Harvest a candidate list, then scan the whole thing and read the
leaderboard.

```
# harvest verified contracts into a list (no API key needed)
seclab targets --chain 1 --limit 500 --out corpus.txt

# only ones DEPLOYED before 2020 (needs ETHERSCAN_API_KEY; filters by deploy date)
seclab targets --chain 1 --limit 300 --before 2020-01-01 --out old.txt

# scan every target, ranked leaderboard (proven > reportable > findings)
seclab batch corpus.txt --basis bounty:myprogram --fast          # cheap triage first
seclab batch corpus.txt --basis bounty:myprogram --llm --swarm --exploit   # deep on survivors
```

A targets file is one per line; `#` comments; optional ` <chain>` after the target:

```
0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 1
https://arbiscan.io/address/0x...            # chain from the URL
https://github.com/org/protocol
./local/clone
```

Batch output lands in `results/batches/<id>/leaderboard.{md,json}`. Each target runs as
an isolated subprocess (one crash can't kill the batch), with `--timeout` per target and
automatic **resume** (re-running skips targets already done; `--no-resume` forces redo).
`--jobs N` scans N targets at once — keep it low with `--llm` (GPU-bound on one model).

### Typical workflow for a bounty / research sweep
1. `seclab targets ... --out corpus.txt` — harvest (optionally date/chain filtered).
2. `seclab batch corpus.txt --fast` — cheap triage, read the leaderboard.
3. `seclab batch <shortlist>.txt --llm --swarm --exploit` — deep pass on anything with findings.
4. Open the top run dirs' `report.md` / `disclosure.md`; only PROVEN/CORROBORATED are reportable.
