"""Scope gate (docs/DECISIONS.md D10). No target is processed without an affirmed
authorization record. PoC execution requires explicit poc_allowed (and is always
sandboxed to a fork elsewhere)."""
from __future__ import annotations
import yaml


class AuthorizationError(Exception):
    pass


def _basis_ok(b: str) -> bool:
    return b == "own" or b.startswith("bounty:") or b.startswith("engagement:")


class ScopeGate:
    def __init__(self, path: str):
        with open(path) as fh:
            doc = yaml.safe_load(fh) or {}
        self.records = {t["id"]: t for t in doc.get("targets", [])}

    def assert_authorized(self, target_id: str, poc: bool = False) -> dict:
        r = self.records.get(target_id)
        if not r:
            raise AuthorizationError(f"no authorization record for '{target_id}'")
        if not _basis_ok(str(r.get("basis", ""))):
            raise AuthorizationError(f"invalid authorization basis '{r.get('basis')}' for '{target_id}'")
        if not r.get("affirmed_by"):
            raise AuthorizationError(f"authorization for '{target_id}' not affirmed")
        if poc and not r.get("poc_allowed", False):
            raise AuthorizationError(f"PoC execution not permitted for '{target_id}'")
        return r
