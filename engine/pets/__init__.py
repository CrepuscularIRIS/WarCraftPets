"""Pet management subsystem.

This package provides:
  - Data accessors for pet definitions and progression tables
  - A factory to build runtime pet instances from (pet_id, rarity_id, breed_id, level)
  - Math helpers for deterministic "panel" damage/heal values

The battle engine is intentionally decoupled from this package: any object with
the expected attributes (id/hp/max_hp/power/speed/pet_type/alive) can participate
in combat. Using :class:`~engine.pets.pet_instance.PetInstance` is recommended
for end-to-end simulations and RL environments.
"""

from .pet_instance import PetInstance
from .pet_db import PetDB
from .progression import ProgressionDB
from .pet_factory import PetFactory, PetFactoryConfig
from .skill_math import SkillMath
from .pet_manager import PetManager

__all__ = [
    "PetInstance",
    "PetDB",
    "ProgressionDB",
    "PetFactory",
    "PetFactoryConfig",
    "SkillMath",
    "PetManager",
]
