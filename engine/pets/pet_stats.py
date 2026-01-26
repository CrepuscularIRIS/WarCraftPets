"""
Pet stat calculation system for WoW pet battles.

Provides the complete calculation pipeline:
  1. Load progression tables from pet_progression_tables.json
  2. Calculate base stats (Health, Power, Speed) for a pet
  3. Calculate skill panel damage values
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

from engine.pets.progression import ProgressionDB
from engine.pets.skill_math import SkillMath


@dataclass
class PetStats:
    """Computed stats for a pet at a given level."""
    pet_id: int
    rarity_id: int
    breed_id: int
    level: int

    health: int
    power: int
    speed: int

    @property
    def quality_multiplier(self) -> float:
        """Get the quality multiplier for this pet's rarity."""
        # This will be set by PetStatsCalculator
        return getattr(self, '_quality_multiplier', 0.0)

    def skill_panel_damage(self, skill_base_points: int) -> int:
        """Calculate panel damage for a skill based on power.

        Formula: floor(points * (1 + power/20))
        """
        return SkillMath.panel_value(skill_base_points, self.power)

    def skill_panel_heal(self, skill_base_points: int) -> int:
        """Calculate panel healing for a skill based on power.

        Formula: floor(points * (1 + power/20))
        """
        return SkillMath.panel_value(skill_base_points, self.power)

    def skill_duration_based_damage(self, base_damage: int, duration_seconds: int) -> int:
        """Calculate damage per tick for duration-based skills.

        Example: A skill that deals damage over 3 turns.
        """
        return int(max(1, self.skill_panel_damage(base_damage) // max(1, duration_seconds)))


class PetStatsCalculator:
    """Main calculator for pet stats using progression tables."""

    def __init__(self, progression_db: ProgressionDB):
        self.progression_db = progression_db

    def calculate(
        self,
        pet_id: int,
        rarity_id: int,
        breed_id: int,
        level: int,
    ) -> PetStats:
        """Calculate complete stats for a pet.

        Args:
            pet_id: The pet species ID
            rarity_id: The rarity/quality ID (1-6)
            breed_id: The breed ID
            level: The pet's level

        Returns:
            PetStats object with computed health, power, and speed

        Raises:
            KeyError: If required data is missing
        """
        stats_dict = self.progression_db.compute_stats(pet_id, breed_id, rarity_id, level)

        pet_stats = PetStats(
            pet_id=int(pet_id),
            rarity_id=int(rarity_id),
            breed_id=int(breed_id),
            level=int(level),
            health=stats_dict["health"],
            power=stats_dict["power"],
            speed=stats_dict["speed"],
        )

        # Store quality multiplier for reference
        pet_stats._quality_multiplier = self.progression_db._quality.get(int(rarity_id), 0.0)

        return pet_stats

    def batch_calculate(
        self,
        pets: list[dict],
    ) -> Dict[tuple, PetStats]:
        """Calculate stats for multiple pets.

        Args:
            pets: List of dicts with keys: pet_id, rarity_id, breed_id, level

        Returns:
            Dictionary mapping (pet_id, rarity_id, breed_id, level) tuples to PetStats
        """
        results = {}
        for pet_spec in pets:
            try:
                stats = self.calculate(
                    pet_spec['pet_id'],
                    pet_spec['rarity_id'],
                    pet_spec['breed_id'],
                    pet_spec['level'],
                )
                key = (stats.pet_id, stats.rarity_id, stats.breed_id, stats.level)
                results[key] = stats
            except KeyError as e:
                # Skip pets with missing data
                continue
        return results

    def calculate_skill_damages(
        self,
        pet_stats: PetStats,
        skills: Dict[str, int],
    ) -> Dict[str, int]:
        """Calculate panel damage for all skills of a pet.

        Args:
            pet_stats: The pet's calculated stats
            skills: Dictionary mapping skill_name to base_damage_points

        Returns:
            Dictionary mapping skill_name to panel_damage
        """
        damages = {}
        for skill_name, base_points in skills.items():
            damages[skill_name] = pet_stats.skill_panel_damage(base_points)
        return damages
