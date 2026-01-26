from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List


def _normalize_param_label(s: str) -> str:
    """Normalize a DB2 ParamLabel string for comparison.

    We do not depend on the ParamParser implementation here, but we keep the
    normalization rules consistent (trim tokens, collapse empties).
    """
    toks = [t.strip() for t in (s or "").split(",")]
    # keep positional empties, but strip trailing empties to avoid false mismatches
    while toks and toks[-1] == "":
        toks.pop()
    return ",".join(toks)


@dataclass(frozen=True)
class OpcodeSemantics:
    prop_id: int
    category: str = ""
    param_label: str = ""
    args_schema: Dict[str, str] = None
    nodes: List[str] = None
    affects_steps: List[str] = None
    notes: List[str] = None

    def schema(self) -> Dict[str, str]:
        return self.args_schema or {}


def _default_semantic_path() -> Optional[Path]:
    # Search order:
    # 1) repo root next to effect_properties_semantic.json
    # 2) repo root next to effect_properties_semantic.yml (not loaded by default, kept as documentation)
    # 3) current working directory
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # .../engine/effects -> .../
    cand_json = repo_root / "effect_properties_semantic.json"
    if cand_json.exists():
        return cand_json
    cand_json_cwd = Path.cwd() / "effect_properties_semantic.json"
    if cand_json_cwd.exists():
        return cand_json_cwd
    return None


class SemanticRegistry:
    """Loads opcode semantics (property_id -> schema/category/notes) from JSON.

    This is intentionally lightweight:
    - No YAML dependency at runtime
    - Safe to ship inside a minimal engine skeleton
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path
        self._by_prop: Dict[int, OpcodeSemantics] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        path = self._path or _default_semantic_path()
        if path is None or not path.exists():
            return

        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # Corrupt or unreadable semantics file: fail closed (no semantics)
            return

        props = obj.get("properties", []) if isinstance(obj, dict) else []
        if not isinstance(props, list):
            return

        for p in props:
            if not isinstance(p, dict):
                continue
            prop_id = int(p.get("prop_id", 0) or 0)
            if prop_id <= 0:
                continue
            self._by_prop[prop_id] = OpcodeSemantics(
                prop_id=prop_id,
                category=str(p.get("category", "") or ""),
                param_label=str(p.get("param_label", "") or ""),
                args_schema=(p.get("args_schema", {}) or {}),
                nodes=(p.get("nodes", []) or []),
                affects_steps=(p.get("affects_steps", []) or []),
                notes=(p.get("notes", []) or []),
            )

    def get(self, prop_id: int) -> Optional[OpcodeSemantics]:
        if not self._loaded:
            self.load()
        return self._by_prop.get(int(prop_id))

    def label_mismatch(self, prop_id: int, observed_param_label: str) -> Optional[Dict[str, str]]:
        """Return mismatch detail if the observed ParamLabel differs from semantics."""
        sem = self.get(prop_id)
        if sem is None:
            return None
        a = _normalize_param_label(observed_param_label)
        b = _normalize_param_label(sem.param_label)
        if a != b:
            return {"observed": a, "expected": b}
        return None


_DEFAULT_REGISTRY: Optional[SemanticRegistry] = None


def get_default_registry() -> SemanticRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = SemanticRegistry()
    return _DEFAULT_REGISTRY


def normalize_args(args: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
    """Type-normalize args according to schema produced by effect_properties_semantic.json.

    Supported specs (from current semantic pack):
      - int
      - int(0/1)
      - int|float
      - int|null
    """
    if not schema:
        return args

    out = dict(args)

    def to_int(x: Any) -> int:
        try:
            return int(float(x))
        except Exception:
            return 0

    def to_float(x: Any) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    for k, spec in schema.items():
        if not isinstance(k, str) or not k:
            continue
        v = out.get(k, 0)
        s = (spec or "").strip().lower()

        if s == "int" or s == "int|null":
            out[k] = to_int(v)
        elif s == "int(0/1)":
            iv = to_int(v)
            out[k] = 1 if iv != 0 else 0
        elif s == "int|float":
            # Preserve floats if present; accept ints as well.
            if isinstance(v, float):
                out[k] = v
            elif isinstance(v, int):
                out[k] = v
            else:
                # Try float first, then int
                fv = to_float(v)
                if abs(fv - int(fv)) < 1e-9:
                    out[k] = int(fv)
                else:
                    out[k] = fv
        else:
            # Unknown spec: keep original
            out[k] = v

    return out


def validate_and_fill_args(args: Dict[str, Any], schema: Dict[str, str]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Validate args against schema.

    Returns: (new_args, report)
      report may contain: missing_keys, extra_keys

    Policy (skeletal, conservative):
      - Missing schema keys are filled with 0
      - Extra keys are kept (handlers might still use them), but reported
    """
    if not schema:
        return args, {}

    out = dict(args)
    missing = [k for k in schema.keys() if k not in out]
    for k in missing:
        out[k] = 0
    extra = [k for k in out.keys() if k not in schema]
    report: Dict[str, Any] = {}
    if missing:
        report["missing_keys"] = missing
    if extra:
        report["extra_keys"] = extra
    return out, report
