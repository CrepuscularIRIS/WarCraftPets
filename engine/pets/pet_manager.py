from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from engine.pets.pet_instance import PetInstance


@dataclass
class PetManager:
    """Container + helper operations for runtime pets.

    Responsibilities:
      - Own the pet instances used by a battle episode
      - Provide safe apply_damage/apply_heal helpers (clamps, alive flag)
      - Offer snapshots for logging / RL observations

    Non-responsibilities (handled elsewhere):
      - Aura lifecycles, state values, cooldowns, turn order
    """

    pets: Dict[int, PetInstance] = field(default_factory=dict)

    def add(self, pet: PetInstance) -> None:
        self.pets[int(pet.id)] = pet

    def get(self, pet_id: int) -> Optional[PetInstance]:
        return self.pets.get(int(pet_id))

    def all(self) -> Iterable[PetInstance]:
        return self.pets.values()

    def apply_damage(self, target_id: int, amount: int) -> int:
        p = self.get(target_id)
        if p is None:
            return 0
        return p.take_damage(int(amount))

    def apply_heal(self, target_id: int, amount: int) -> int:
        p = self.get(target_id)
        if p is None:
            return 0
        return p.receive_heal(int(amount))

    def snapshot(self, pet_id: int) -> Optional[Dict[str, int]]:
        p = self.get(pet_id)
        if p is None:
            return None
        return {
            "id": int(p.id),
            "pet_id": int(p.pet_id),
            "hp": int(p.hp),
            "max_hp": int(p.max_hp),
            "power": int(p.power),
            "speed": int(p.speed),
            "alive": 1 if bool(p.alive) else 0,
        }
