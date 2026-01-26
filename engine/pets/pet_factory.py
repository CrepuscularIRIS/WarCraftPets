from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from engine.pets.pet_db import PetDB
from engine.pets.progression import ProgressionDB
from engine.pets.pet_instance import PetInstance


@dataclass(frozen=True)
class PetFactoryConfig:
    """Factory configuration.

    strict_level25:
      When True, level must be 25 and the exact (breed_id, rarity_id) record must
      exist in pets_all.json. This guarantees stats match the shipped dataset.
      When False, fall back to progression-based approximation.
    """

    strict_level25: bool = True


class PetFactory:
    def __init__(
        self,
        *,
        pets_all_path: str | Path,
        progression_path: str | Path,
        config: Optional[PetFactoryConfig] = None,
    ):
        self.config = config or PetFactoryConfig()
        self.pet_db = PetDB(pets_all_path)
        self.prog = ProgressionDB(progression_path)

    def create(
        self,
        *,
        instance_id: int,
        pet_id: int,
        rarity_id: int,
        breed_id: int,
        level: int,
    ) -> PetInstance:
        """Create a PetInstance.

        instance_id must be unique within a battle (useful when the same species
        appears multiple times).
        """
        pet_id = int(pet_id)
        level = int(level)
        rarity_id = int(rarity_id)
        breed_id = int(breed_id)

        pet_type = int(self.pet_db.pet_type(pet_id))
        name_en, name_zh = self.pet_db.names(pet_id)
        abilities, ability_names = self.pet_db.resolve_abilities(pet_id, level)

        stats = None
        if level == 25:
            stats = self.pet_db.lookup_level25_stats(pet_id, breed_id, rarity_id)

        if self.config.strict_level25:
            if level != 25:
                raise ValueError("strict_level25=True requires level=25")
            if stats is None:
                raise KeyError(
                    f"No level-25 stats for pet_id={pet_id}, breed_id={breed_id}, rarity_id={rarity_id}"
                )
        if stats is None:
            stats = self.prog.compute_stats(pet_id, breed_id, rarity_id, level)

        p = PetInstance(
            id=int(instance_id),
            pet_id=pet_id,
            rarity_id=rarity_id,
            breed_id=breed_id,
            level=level,
            pet_type=pet_type,
            name_en=name_en,
            name_zh=name_zh,
            base_max_hp=int(stats["health"]),
            base_power=int(stats["power"]),
            base_speed=int(stats["speed"]),
            abilities=abilities,
            ability_names=ability_names,
        )
        p.reset_runtime()
        return p
