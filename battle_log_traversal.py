#!/usr/bin/env python3
"""Generate per-pet and per-skill battle logs."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from main import DataLoader, run_battle


def _sanitize(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-\.\u4e00-\u9fff]+", "_", name)
    cleaned = cleaned.strip("_")
    return cleaned or "unknown"


def _ability_index(pets_data: Dict[int, dict]) -> Dict[int, List[Tuple[int, int, int]]]:
    index: Dict[int, List[Tuple[int, int, int]]] = {}
    for pet_id, pet in pets_data.items():
        ability_pool = pet.get("AbilityPool", {}) or {}
        for slot_str, options in ability_pool.items():
            try:
                slot = int(slot_str)
            except Exception:
                continue
            if not isinstance(options, list):
                continue
            for opt_idx, ability_id in enumerate(options):
                try:
                    aid = int(ability_id)
                except Exception:
                    continue
                if aid <= 0:
                    continue
                index.setdefault(aid, []).append((int(pet_id), slot, opt_idx))
    return index


def _choice_list(slot: int, opt_idx: int) -> List[int]:
    choices = [0, 0, 0]
    if 0 <= slot < len(choices):
        choices[slot] = int(opt_idx)
    return choices


def _default_dummy(pets_data: Dict[int, dict], prefer: int | None) -> int:
    if prefer is not None and prefer in pets_data:
        return int(prefer)
    if pets_data:
        return int(sorted(pets_data.keys())[0])
    raise RuntimeError("No pets loaded")


def generate_logs(
    *,
    output_dir: Path,
    seed_base: int,
    max_rounds: int,
    level: int,
    rarity_id: int,
    max_pets: int | None,
    max_skills: int | None,
    dummy_pet_id: int | None,
    write_events: bool,
) -> None:
    data_loader = DataLoader(".")
    data_loader.load_all()

    pets_data = data_loader.pets_data
    if not pets_data:
        raise RuntimeError("No pet data loaded")

    dummy_id = _default_dummy(pets_data, dummy_pet_id)

    by_pet_dir = output_dir / "by_pet"
    by_skill_dir = output_dir / "by_skill"
    report_dir = output_dir / "reports"
    by_pet_event_dir = output_dir / "events" / "by_pet"
    by_skill_event_dir = output_dir / "events" / "by_skill"
    by_pet_dir.mkdir(parents=True, exist_ok=True)
    by_skill_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    if write_events:
        by_pet_event_dir.mkdir(parents=True, exist_ok=True)
        by_skill_event_dir.mkdir(parents=True, exist_ok=True)

    ability_index = _ability_index(pets_data)
    all_ability_ids = sorted(int(x) for x in data_loader.abilities_data.keys())

    pet_ids = sorted(pets_data.keys())
    if max_pets is not None:
        pet_ids = pet_ids[: max_pets]

    skill_ids = all_ability_ids
    if max_skills is not None:
        skill_ids = skill_ids[: max_skills]

    pet_logs: List[Dict[str, str | int]] = []
    skill_logs: List[Dict[str, str | int]] = []
    missing_skills: List[int] = []

    for i, pet_id in enumerate(pet_ids, start=1):
        name_zh = pets_data.get(pet_id, {}).get("Names", {}).get("zh", f"pet_{pet_id}")
        filename = f"pet_{pet_id}_{_sanitize(str(name_zh))}.txt"
        log_path = by_pet_dir / filename
        event_log = None
        if write_events:
            event_log = by_pet_event_dir / f"pet_{pet_id}_{_sanitize(str(name_zh))}.jsonl"
        run_battle(
            data_loader=data_loader,
            team0_pet_ids=[pet_id],
            team1_pet_ids=[dummy_id],
            level=level,
            rarity_id=rarity_id,
            seed=seed_base + int(pet_id),
            max_rounds=max_rounds,
            log_file=str(log_path),
            ability_slot=1,
            ability_choices_by_pet=None,
            ability_override_by_pet_slot=None,
            verbose=False,
            event_log_file=str(event_log) if event_log else None,
        )
        pet_logs.append({"pet_id": int(pet_id), "name_zh": str(name_zh), "log": str(log_path)})
        if i % 50 == 0:
            print(f"[pet] {i}/{len(pet_ids)}")

    for i, ability_id in enumerate(skill_ids, start=1):
        carriers = ability_index.get(int(ability_id)) or []
        if carriers:
            pet_id, slot, opt_idx = carriers[0]
            ability_choices_by_pet = {int(pet_id): _choice_list(slot, opt_idx)}
            ability_override_by_pet_slot = None
        else:
            missing_skills.append(int(ability_id))
            pet_id = int(dummy_id)
            slot = 0
            opt_idx = 0
            ability_choices_by_pet = None
            ability_override_by_pet_slot = {int(pet_id): {1: int(ability_id)}}
        ability_name_zh, _ = data_loader.get_ability_name(int(ability_id))
        filename = f"ability_{ability_id}_{_sanitize(str(ability_name_zh))}.txt"
        log_path = by_skill_dir / filename
        event_log = None
        if write_events:
            event_log = by_skill_event_dir / f"ability_{ability_id}_{_sanitize(str(ability_name_zh))}.jsonl"
        run_battle(
            data_loader=data_loader,
            team0_pet_ids=[int(pet_id)],
            team1_pet_ids=[dummy_id],
            level=level,
            rarity_id=rarity_id,
            seed=seed_base + int(ability_id),
            max_rounds=max_rounds,
            log_file=str(log_path),
            ability_slot=int(slot) + 1 if carriers else 1,
            ability_choices_by_pet=ability_choices_by_pet,
            ability_override_by_pet_slot=ability_override_by_pet_slot,
            verbose=False,
            event_log_file=str(event_log) if event_log else None,
        )
        skill_logs.append({
            "ability_id": int(ability_id),
            "ability_name_zh": str(ability_name_zh),
            "pet_id": int(pet_id),
            "slot": int(slot) + 1,
            "log": str(log_path),
        })
        if i % 50 == 0:
            print(f"[skill] {i}/{len(skill_ids)}")

    report = {
        "pets_total": len(pet_ids),
        "skills_total": len(skill_ids),
        "dummy_pet_id": int(dummy_id),
        "pet_logs": pet_logs,
        "skill_logs": skill_logs,
        "missing_skills": missing_skills,
    }
    report_path = report_dir / "log_traversal_summary.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Summary written to: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-pet and per-skill battle logs")
    parser.add_argument("--output", type=str, default="logs", help="Output base directory")
    parser.add_argument("--seed-base", type=int, default=1000, help="Seed base for deterministic runs")
    parser.add_argument("--rounds", type=int, default=25, help="Max rounds per battle")
    parser.add_argument("--level", type=int, default=25, help="Pet level")
    parser.add_argument("--rarity", type=int, default=4, help="Rarity id")
    parser.add_argument("--max-pets", type=int, help="Limit number of pets")
    parser.add_argument("--max-skills", type=int, help="Limit number of skills")
    parser.add_argument("--dummy", type=int, help="Dummy target pet id")
    parser.add_argument("--events", action="store_true", help="Write JSONL event logs")
    args = parser.parse_args()

    generate_logs(
        output_dir=Path(args.output),
        seed_base=args.seed_base,
        max_rounds=args.rounds,
        level=args.level,
        rarity_id=args.rarity,
        max_pets=args.max_pets,
        max_skills=args.max_skills,
        dummy_pet_id=args.dummy,
        write_events=args.events,
    )


if __name__ == "__main__":
    main()
