from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class PetInstance:
    """Runtime pet instance used by the battle loop.

    Design goals:
      - Minimal surface area: compatible with existing engine components.
      - Stable identity + base stats + mutable runtime stats.

    Required by the engine today:
      - id, hp, max_hp, power, speed, alive
      - pet_type (for type interactions, when enabled)
    """

    # --- identity / creation parameters ---
    id: int
    pet_id: int  # Species/DB2 id ("petid" in user terms)
    rarity_id: int
    breed_id: int
    level: int
    pet_type: int

    name_en: str = ""
    name_zh: str = ""

    # --- base stats (immutable after creation) ---
    base_max_hp: int = 0
    base_power: int = 0
    base_speed: int = 0

    # --- runtime stats (mutable) ---
    max_hp: int = 0
    hp: int = 0
    power: int = 0
    speed: int = 0
    alive: bool = True

    # --- chosen abilities for this instance ---
    # slot index is 1..3
    abilities: Dict[int, int] = field(default_factory=dict)
    ability_names: Dict[int, Dict[str, str]] = field(default_factory=dict)

    # --- optional scratchpad for advanced sims / RL ---
    tags: Dict[str, Any] = field(default_factory=dict)

    def reset_runtime(self) -> None:
        """Reset runtime fields to base values (useful across episodes)."""
        self.max_hp = int(self.base_max_hp)
        self.hp = int(self.base_max_hp)
        self.power = int(self.base_power)
        self.speed = int(self.base_speed)
        self.alive = True

    def take_damage(self, amount: int) -> int:
        """Apply damage; returns actual damage applied."""
        if not self.alive:
            return 0
        dmg = int(max(0, amount))
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return dmg

    def receive_heal(self, amount: int) -> int:
        """Apply healing; returns actual healing applied."""
        if not self.alive:
            return 0
        heal = int(max(0, amount))
        before = int(self.hp)
        self.hp = min(int(self.max_hp), int(self.hp) + heal)
        return int(self.hp) - before

    def chosen_ability_id(self, slot: int) -> Optional[int]:
        return self.abilities.get(int(slot))
