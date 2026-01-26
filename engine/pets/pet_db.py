from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any, Tuple


@dataclass(frozen=True)
class SelectedAbility:
    ability_id: int
    requires_pet_level: int
    name_en: str = ""
    name_zh: str = ""


class PetDB:
    """Lightweight access layer over pets_all.json.

    The repository ships a curated `pets_all.json` where each entry contains:
      - pet_id (species)
      - type
      - per-slot ability pools with required levels
      - a set of (breed_id, rarity_id) records at level 25 with exact stats

    This DB is used by PetFactory to resolve ability selections and, when possible,
    return exact level-25 stats.
    """

    def __init__(self, pets_all_path: str | Path):
        p = Path(pets_all_path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, list):
            raise TypeError("pets_all.json must be a list")

        self._pets: Dict[int, Dict[str, Any]] = {}
        for row in obj:
            if not isinstance(row, dict):
                continue
            try:
                pid = int(row.get("pet_id") or 0)
            except Exception:
                continue
            if pid <= 0:
                continue
            self._pets[pid] = row

    def get(self, pet_id: int) -> Dict[str, Any]:
        row = self._pets.get(int(pet_id))
        if row is None:
            raise KeyError(f"Unknown pet_id={int(pet_id)}")
        return row

    def pet_type(self, pet_id: int) -> int:
        return int(self.get(pet_id).get("pet_type_id") or 0)

    def names(self, pet_id: int) -> Tuple[str, str]:
        row = self.get(pet_id)
        return str(row.get("name_en") or ""), str(row.get("name_zh") or "")

    def resolve_slot_ability(self, pet_id: int, slot: int, level: int) -> Optional[SelectedAbility]:
        """Select the highest-level-allowed ability from a slot pool."""
        row = self.get(pet_id)
        abilities = (row.get("abilities") or {}).get(f"slot{int(slot)}")
        if not isinstance(abilities, list):
            return None

        best: Optional[SelectedAbility] = None
        for a in abilities:
            if not isinstance(a, dict):
                continue
            try:
                req = int(a.get("requires_pet_level") or 0)
                aid = int(a.get("ability_id") or 0)
            except Exception:
                continue
            if aid <= 0:
                continue
            if req > int(level):
                continue
            if best is None or req >= best.requires_pet_level:
                best = SelectedAbility(
                    ability_id=aid,
                    requires_pet_level=req,
                    name_en=str(a.get("name_en") or ""),
                    name_zh=str(a.get("name_zh") or ""),
                )
        return best

    def resolve_abilities(self, pet_id: int, level: int) -> Tuple[Dict[int, int], Dict[int, Dict[str, str]]]:
        out: Dict[int, int] = {}
        names: Dict[int, Dict[str, str]] = {}
        for slot in (1, 2, 3):
            sel = self.resolve_slot_ability(pet_id, slot, level)
            if sel is None:
                continue
            out[int(slot)] = int(sel.ability_id)
            names[int(slot)] = {"en": sel.name_en, "zh": sel.name_zh}
        return out, names

    def lookup_level25_stats(self, pet_id: int, breed_id: int, rarity_id: int) -> Optional[Dict[str, int]]:
        """Return exact stats from `records` when present (level 25 only)."""
        row = self.get(pet_id)
        records = row.get("records")
        if not isinstance(records, list):
            return None
        for rec in records:
            if not isinstance(rec, dict):
                continue
            try:
                b = int(rec.get("breed_id") or 0)
                r = int(rec.get("rarity_id") or 0)
            except Exception:
                continue
            if b == int(breed_id) and r == int(rarity_id):
                st = rec.get("stats")
                if isinstance(st, dict):
                    try:
                        return {
                            "health": int(st.get("health") or 0),
                            "power": int(st.get("power") or 0),
                            "speed": int(st.get("speed") or 0),
                        }
                    except Exception:
                        return None
        return None
