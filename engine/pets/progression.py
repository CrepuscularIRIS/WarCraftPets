from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


class ProgressionDB:
    """Fallback stat computation using pet_progression_tables.json.

    Notes:
      - The repository's `pets_all.json` contains exact stats at level 25 for many
        (pet_id, breed_id, rarity_id) tuples. When those are available, PetFactory
        should prefer them.
      - For non-covered tuples (or non-25 levels), we provide a deterministic
        approximation derived from the same progression tables.

    This is sufficient for an RL environment where the engine needs consistent
    and monotonic scaling, even if some edge cases differ from retail.
    """

    def __init__(self, progression_path: str | Path):
        p = Path(progression_path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise TypeError("pet_progression_tables.json must be an object")

        self._quality: Dict[int, float] = {}
        for k, v in (obj.get("quality_multiplier") or {}).items():
            try:
                # 质量乘数的基准为0.5，所以需要乘以2来得到真实的质量乘数
                self._quality[int(k)] = float(v) * 2.0
            except Exception:
                continue

        self._breeds: Dict[int, Dict[str, float]] = {}
        for k, v in (obj.get("breed_stats") or {}).items():
            try:
                bid = int(k)
            except Exception:
                continue
            if isinstance(v, dict):
                self._breeds[bid] = v

        self._base: Dict[int, Optional[Dict[str, float]]] = {}
        for k, v in (obj.get("base_pet_stats") or {}).items():
            try:
                pid = int(k)
            except Exception:
                continue
            self._base[pid] = v if isinstance(v, dict) else None

    def has_base(self, pet_id: int) -> bool:
        return isinstance(self._base.get(int(pet_id)), dict)

    def compute_stats(self, pet_id: int, breed_id: int, rarity_id: int, level: int) -> Dict[str, int]:
        """Compute (health, power, speed) for the given tuple using the official formulas.

        Formulas:
          Health: ((Base Health + (Health_BreedPoints / 10)) * 5 * Level * Quality) + 100
          Power: ((Base Power + (Power_BreedPoints / 10)) * Level * Quality)
          Speed: ((Base Speed + (Speed_BreedPoints / 10)) * Level * Quality)

        When the base/breed/rarity tuple is not available, raises KeyError.
        """
        base = self._base.get(int(pet_id))
        if not isinstance(base, dict):
            raise KeyError(f"No base stats for pet_id={int(pet_id)}")
        breed = self._breeds.get(int(breed_id))
        if not isinstance(breed, dict):
            raise KeyError(f"No progression for breed_id={int(breed_id)}")
        q = float(self._quality.get(int(rarity_id), 0.0))
        if q <= 0:
            raise KeyError(f"No quality multiplier for rarity_id={int(rarity_id)}")

        lvl = max(1, int(level))

        # Extract base stats
        base_health = float(base.get("base_health") or 0.0)
        base_power = float(base.get("base_power") or 0.0)
        base_speed = float(base.get("base_speed") or 0.0)

        # Extract breed points
        health_breed_points = float(breed.get("health_add") or 0.0)
        power_breed_points = float(breed.get("power_add") or 0.0)
        speed_breed_points = float(breed.get("speed_add") or 0.0)

        # Apply formulas:
        # 注意：breed_stats中的值已经是除以10后的结果
        # 所以直接使用这些值，不需要再除以10
        # Health: ((Base Health + HealthPts_from_data) * 5 * Level * Quality) + 100
        # Power: (Base Power + PowerPts_from_data) * Level * Quality
        # Speed: (Base Speed + SpeedPts_from_data) * Level * Quality
        health = int(round((base_health + health_breed_points) * 5.0 * lvl * q + 100.0))
        power = int(round((base_power + power_breed_points) * lvl * q))
        speed = int(round((base_speed + speed_breed_points) * lvl * q))

        # Ensure minimum values
        if power < 0:
            power = 0
        if speed < 1:
            speed = 1
        if health < 1:
            health = 1
        return {"health": health, "power": power, "speed": speed}
