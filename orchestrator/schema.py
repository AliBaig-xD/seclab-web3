"""Core types. The anti-hallucination invariant lives here: a Finding's confidence
tier is DERIVED from its evidence, never set by the model (see docs/WORKFLOW.md L2)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List
import time, hashlib, json


class Tier(str, Enum):
    PROVEN = "PROVEN"
    CORROBORATED = "CORROBORATED"
    CANDIDATE = "CANDIDATE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"; HIGH = "HIGH"; MEDIUM = "MEDIUM"
    LOW = "LOW"; INFO = "INFO"; UNKNOWN = "UNKNOWN"


REPORTABLE = {Tier.PROVEN, Tier.CORROBORATED}


@dataclass
class Evidence:
    kind: str                 # slither|semgrep|halmos|mythril|echidna|medusa|foundry_poc|dataflow|llm
    tool: str
    summary: str
    artifact_path: Optional[str] = None
    deterministic: bool = True
    repro: Optional[str] = None
    severity_hint: Optional[str] = None
    created: float = field(default_factory=time.time)

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]


@dataclass
class Hypothesis:
    vuln_type: str
    location: str
    precondition: str
    claimed_impact: str
    source: str = "llm"       # llm|static|heuristic
    rationale: str = ""
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.vuln_type}|{self.location}|{self.precondition}".encode()
            ).hexdigest()[:12]


@dataclass
class Finding:
    hypothesis: Hypothesis
    tier: Tier = Tier.CANDIDATE
    severity: Severity = Severity.UNKNOWN
    evidence: List[Evidence] = field(default_factory=list)
    repro_cmd: Optional[str] = None
    falsified: bool = False
    notes: str = ""

    def recompute_tier(self) -> Tier:
        if self.falsified:
            self.tier = Tier.CANDIDATE
            return self.tier
        kinds = {e.kind for e in self.evidence}
        independent = {e.tool for e in self.evidence if e.kind != "llm"}
        if "foundry_poc" in kinds and self.repro_cmd:
            self.tier = Tier.PROVEN
        elif len(independent) >= 2:
            self.tier = Tier.CORROBORATED
        else:
            self.tier = Tier.CANDIDATE
        return self.tier

    @property
    def reportable(self) -> bool:
        return self.tier in REPORTABLE and not self.falsified


def finding_json(f: "Finding") -> dict:
    return {
        "hypothesis": asdict(f.hypothesis),
        "tier": f.tier.value,
        "severity": f.severity.value,
        "repro_cmd": f.repro_cmd,
        "falsified": f.falsified,
        "notes": f.notes,
        "evidence": [asdict(e) for e in f.evidence],
    }
