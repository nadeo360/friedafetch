"""The shape of websocket answers: which fields, of which type. The dev preview's mocks are checked against it.

tests/contracts/ws.json holds the shapes of the real answers (written by test_contracts.py). The browser tests of the
dev preview (tools/preview/tests) ask the mocks the same commands and check that they answer with every field the
real backend sends, so the preview cannot fall behind the integration unnoticed.

A shape is a type name ("str", "num", "bool", "null", several joined by "|"), a dict of shapes, or a list holding the
merged shape of all elements. Keys that only some list elements have are marked optional with a leading "?".
Dicts keyed by data (counts per folder, per AI entity, per rule) are maps: {"*": shape of their values}.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONTRACTS = Path(__file__).parent / "contracts" / "ws.json"
MAPS = {"entities", "folders", "rules", "kinds", "opts"}  # dict fields whose keys are data, not names
FREE = {"params", "details"}  # whatever the tool in question takes or reports: not part of the contract


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int | float):
        return "num"
    return "str"


def shape(value: Any, key: str = "") -> Any:
    if key in FREE:
        return "any"
    if isinstance(value, dict) and key in MAPS:
        merged: Any = None
        for item in value.values():
            merged = shape(item) if merged is None else merge(merged, shape(item))
        return {"*": merged} if merged is not None else {"*": "null"}
    if isinstance(value, dict):
        return {k: shape(v, k) for k, v in sorted(value.items())}
    if isinstance(value, list):
        merged: Any = None
        for item in value:
            merged = shape(item) if merged is None else merge(merged, shape(item))
        return [merged] if merged is not None else []
    return _scalar(value)


def _types(s: Any) -> set[str]:
    return set(s.split("|")) if isinstance(s, str) else {"dict" if isinstance(s, dict) else "list"}


def merge(a: Any, b: Any) -> Any:
    """Both shapes in one: keys missing on one side become optional, differing types are joined."""
    if isinstance(a, dict) and isinstance(b, dict):
        keys = {k.lstrip("?") for k in [*a, *b]}
        out = {}
        for key in sorted(keys):
            va = a.get(key, a.get("?" + key))
            vb = b.get(key, b.get("?" + key))
            optional = key not in a or key not in b
            value = merge(va, vb) if va is not None and vb is not None else (va if vb is None else vb)
            out[("?" if optional else "") + key] = value
        return out
    if isinstance(a, list) and isinstance(b, list):
        if not a or not b:
            return a or b
        return [merge(a[0], b[0])]
    if isinstance(a, str) and isinstance(b, str):
        return "|".join(sorted(_types(a) | _types(b)))
    if a == "null":
        return b
    if b == "null":
        return a
    return a  # dict or list against a scalar: keep the richer side


def check(contract: Any, value: Any, path: str = "$") -> list[str]:
    """Where `value` (a mock's answer) lacks something the contract has; extra fields are fine."""
    if value is None:
        return []  # an empty value: the panel handles null wherever the backend may send nothing
    if isinstance(contract, dict) and set(contract) == {"*"}:
        if not isinstance(value, dict):
            return [f"{path}: expected an object"]
        found = [p for v in value.values() for p in check(contract["*"], v, f"{path}.*")]
        return list(dict.fromkeys(found))
    if isinstance(contract, dict):
        if not isinstance(value, dict):
            return [f"{path}: expected an object, got {_scalar(value) if not isinstance(value, list) else 'list'}"]
        problems = []
        for key, sub in contract.items():
            name = key.lstrip("?")
            if name not in value:
                if not key.startswith("?"):
                    problems.append(f"{path}.{name}: missing")
                continue
            problems += check(sub, value[name], f"{path}.{name}")
        return problems
    if isinstance(contract, list):
        if not isinstance(value, list):
            return [f"{path}: expected a list"]
        if not contract or not value:
            return []
        found = [p for item in value for p in check(contract[0], item, f"{path}[]")]
        return list(dict.fromkeys(found))  # the same gap in many entries is reported once
    allowed = _types(contract)
    if "any" in allowed or allowed == {"null"}:
        return []  # only seen empty in the backend test: any type is fine
    got = "dict" if isinstance(value, dict) else "list" if isinstance(value, list) else _scalar(value)
    if got in allowed or got == "null" or (got in ("dict", "list") and allowed & {"dict", "list"}):
        return []
    return [f"{path}: {got} where the backend sends {contract}"]


def assert_contract(name: str, answer: Any) -> None:
    """Compares a real answer with tests/contracts/ws.json; UPDATE_CONTRACTS=1 writes it instead."""
    data = json.loads(CONTRACTS.read_text()) if CONTRACTS.exists() else {}
    current = shape(answer)
    if os.environ.get("UPDATE_CONTRACTS"):
        data[name] = (
            merge(data[name], current) if name in data and os.environ["UPDATE_CONTRACTS"] == "merge" else current
        )
        CONTRACTS.parent.mkdir(exist_ok=True)
        CONTRACTS.write_text(json.dumps(dict(sorted(data.items())), indent=1, ensure_ascii=False) + "\n")
        return
    assert name in data, f"no contract for {name}: run UPDATE_CONTRACTS=1 pytest tests/test_contracts.py"
    assert data[name] == current, (
        f"the answer of {name} changed shape – if that is intended, run UPDATE_CONTRACTS=1 pytest "
        "tests/test_contracts.py and update the dev preview's mock (tools/preview)"
    )
