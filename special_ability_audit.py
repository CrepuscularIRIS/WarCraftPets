#!/usr/bin/env python3
"""Audit abilities with special opcodes vs simulator coverage."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from skill_traversal import SKILL_CATALOG


def _strip_jsonc(text: str) -> str:
    return re.sub(r"//.*", "", text)


def _load_pack(path: Path) -> Dict[str, Any]:
    text = _strip_jsonc(path.read_text(encoding="utf-8"))
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit special abilities")
    parser.add_argument("--pack", type=str, default="data/petbattle_ability_pack.v1.debug.jsonc")
    parser.add_argument("--output", type=str, default="logs/reports/special_ability_audit.json")
    args = parser.parse_args()

    obj = _load_pack(Path(args.pack))
    abilities = obj.get("abilities", []) or []

    opcode_type = {}
    for op_id, meta in SKILL_CATALOG.items():
        try:
            opcode_type[int(op_id.replace("op", ""))] = meta.get("type", "unknown")
        except Exception:
            continue

    special: List[Dict[str, Any]] = []
    unknown_opcodes = set()

    for ab in abilities:
        ability_id = int(ab.get("ability_id") or 0)
        name_zh = (ab.get("name", {}) or {}).get("zh", f"技能{ability_id}")
        cast = ab.get("cast", {}) or {}
        turns = cast.get("turns", []) or []
        opcodes: List[Dict[str, Any]] = []
        types = set()
        for turn in turns:
            for eff in (turn.get("effects", []) or []):
                opcode_id = int(eff.get("opcode_id") or 0)
                t = opcode_type.get(opcode_id)
                if t is None:
                    unknown_opcodes.add(opcode_id)
                    t = "unknown"
                types.add(t)
                opcodes.append({"opcode_id": opcode_id, "type": t})

        # if any non-damage opcode type => special
        special_types = {t for t in types if t not in {"damage"}}
        if special_types:
            special.append({
                "ability_id": ability_id,
                "name_zh": name_zh,
                "types": sorted(types),
                "special_types": sorted(special_types),
                "opcodes": opcodes,
                "note": "main.py only simulates direct damage; special types likely unsupported",
            })

    out = {
        "total_abilities": len(abilities),
        "special_count": len(special),
        "unknown_opcode_ids": sorted(x for x in unknown_opcodes if x != 0),
        "special": special,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    main()
