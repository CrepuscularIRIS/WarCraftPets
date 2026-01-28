#!/usr/bin/env python3
"""Analyze JSONL event logs and emit a bug list (event diff)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_events(path: Path) -> List[Dict[str, Any]]:
    events = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                events.append({"event": "__PARSE_ERROR__", "raw": line})
    return events


def _hp_delta_from_diff(diff: Dict[str, Any]) -> Optional[int]:
    hp = diff.get("hp") if isinstance(diff, dict) else None
    if not isinstance(hp, dict):
        return None
    return hp.get("delta")


def analyze_events(path: Path) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    events = _load_events(path)
    current_cast: Optional[Dict[str, Any]] = None

    for rec in events:
        ev = rec.get("event")
        payload = rec.get("payload") or {}
        seq = rec.get("seq")

        if ev == "ABILITY_CAST_START":
            current_cast = {
                "ability_id": payload.get("ability_id"),
                "actor_id": payload.get("actor_id"),
                "target_id": payload.get("target_id"),
                "seq": seq,
                "damage": None,
            }

        elif ev == "DAMAGE_APPLIED":
            # direct consistency check
            hp_before = payload.get("target_hp_before")
            hp_after = payload.get("target_hp_after")
            dmg = payload.get("actual_damage")
            if isinstance(hp_before, int) and isinstance(hp_after, int) and isinstance(dmg, int):
                expected_after = max(hp_before - dmg, 0)
                if expected_after != hp_after:
                    issues.append({
                        "type": "damage_hp_mismatch",
                        "seq": seq,
                        "ability_id": payload.get("ability_id"),
                        "details": {"hp_before": hp_before, "damage": dmg, "hp_after": hp_after},
                    })
            if current_cast is not None:
                current_cast["damage"] = dmg
                current_cast["hp_before"] = hp_before

        elif ev == "ABILITY_EFFECTS":
            target_diff = payload.get("target_diff") or {}
            delta = _hp_delta_from_diff(target_diff)
            target_after = (payload.get("target_after") or {})
            max_hp = target_after.get("max_hp")
            hp = target_after.get("hp")

            if isinstance(hp, int) and isinstance(max_hp, int):
                if hp < 0 or hp > max_hp:
                    issues.append({
                        "type": "hp_out_of_range",
                        "seq": seq,
                        "ability_id": payload.get("ability_id"),
                        "details": {"hp": hp, "max_hp": max_hp},
                    })

            if current_cast is not None:
                dmg = current_cast.get("damage")
                hp_before = current_cast.get("hp_before")
                if isinstance(delta, int) and isinstance(dmg, int) and isinstance(hp_before, int):
                    expected_delta = -min(dmg, hp_before)
                    if delta != expected_delta:
                        issues.append({
                            "type": "diff_damage_mismatch",
                            "seq": seq,
                            "ability_id": payload.get("ability_id"),
                            "details": {"diff_delta": delta, "damage": dmg, "hp_before": hp_before},
                        })
                elif isinstance(delta, int) and dmg is None and delta != 0:
                    issues.append({
                        "type": "diff_without_damage",
                        "seq": seq,
                        "ability_id": payload.get("ability_id"),
                        "details": {"diff_delta": delta},
                    })

        elif ev == "ABILITY_CAST_END":
            current_cast = None

        elif ev == "__PARSE_ERROR__":
            issues.append({
                "type": "parse_error",
                "seq": seq,
                "details": {"raw": rec.get("raw")},
            })

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Event diff checker for battle JSONL logs")
    parser.add_argument("--input", type=str, required=True, help="JSONL file or directory")
    parser.add_argument("--output", type=str, default="logs/reports/event_diff_report.json", help="Output report")
    args = parser.parse_args()

    input_path = Path(args.input)
    outputs: Dict[str, Any] = {"files": [], "issues": []}

    paths: List[Path] = []
    if input_path.is_dir():
        paths = sorted(input_path.rglob("*.jsonl"))
    else:
        paths = [input_path]

    for p in paths:
        issues = analyze_events(p)
        outputs["files"].append({"path": str(p), "issue_count": len(issues)})
        for issue in issues:
            issue["file"] = str(p)
            outputs["issues"].append(issue)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    main()
