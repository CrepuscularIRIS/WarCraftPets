"""Pet battle racial passive system.

Implements all 10 racial passives according to WoW pet battle rules:
  0 Humanoid: Heal 4% max HP when dealing damage
  1 Dragonkin: +50% damage for one round after bringing target below 25% HP
  2 Flying: +50% speed when above 50% HP (implemented in stats_resolver.py)
  3 Undead: Resurrect for 1 round on death, immune during that round
  4 Critter: Faster recovery from crowd control effects
  5 Magic: Single hit damage capped at 35% max HP (implemented in damage_pipeline.py)
  6 Elemental: Ignore all weather effects (implemented in damage_pipeline.py and hitcheck.py)
  7 Beast: +25% damage when below 50% HP (implemented in damage_pipeline.py)
  8 Aquatic: -50% damage from periodic effects (implemented in damage_pipeline.py)
  9 Mechanical: Resurrect once at 20% HP on death
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

# Pet type IDs
PET_TYPE_HUMANOID = 0
PET_TYPE_DRAGONKIN = 1
PET_TYPE_FLYING = 2
PET_TYPE_UNDEAD = 3
PET_TYPE_CRITTER = 4
PET_TYPE_MAGIC = 5
PET_TYPE_ELEMENTAL = 6
PET_TYPE_BEAST = 7
PET_TYPE_AQUATIC = 8
PET_TYPE_MECHANICAL = 9


@dataclass
class RacialPassiveState:
    """Tracks per-pet racial passive state across rounds."""

    # Dragonkin: pet_id -> rounds remaining for +50% damage buff
    dragonkin_buff_rounds: Dict[int, int] = field(default_factory=dict)

    # Undead: pet_id -> True if currently in undead immortality round
    undead_immortality: Dict[int, bool] = field(default_factory=dict)
    # Undead: pet_id -> True if should die at end of current round
    undead_pending_death: Dict[int, bool] = field(default_factory=dict)

    # Mechanical: pet_id -> True if has already used mechanical revive
    mechanical_revived: Dict[int, bool] = field(default_factory=dict)

    # Critter: pet_id -> rounds to reduce from CC duration
    # (Critter passive: recover 1 round faster from CC = CC duration reduced by 1)
    critter_cc_reduction: int = 1

    # Humanoid: pet_id -> set of rounds where damage was dealt (for end-of-round heal)
    humanoid_dealt_damage: Dict[int, bool] = field(default_factory=dict)


class RacialPassiveManager:
    """Manages racial passive effects for all pets in battle.

    Integration points:
      - on_damage_dealt(): Called when a pet deals damage
      - on_pet_death(): Called when a pet's HP reaches 0
      - on_round_start(): Called at start of each round
      - on_round_end(): Called at end of each round
      - get_damage_multiplier(): Returns bonus damage multiplier for actor
      - apply_cc_duration_reduction(): Reduces CC duration for critter pets
    """

    def __init__(self):
        self.state = RacialPassiveState()

    def reset(self) -> None:
        """Reset all racial passive state (for new battle)."""
        self.state = RacialPassiveState()

    def _pet_type(self, pet: Any) -> int:
        """Get pet type from pet object."""
        try:
            return int(getattr(pet, "pet_type", -1) or -1)
        except Exception:
            return -1

    def _pet_id(self, pet: Any) -> int:
        """Get pet id from pet object."""
        try:
            return int(getattr(pet, "id", 0) or 0)
        except Exception:
            return 0

    def _max_hp(self, pet: Any) -> int:
        """Get max HP from pet object."""
        try:
            return int(getattr(pet, "max_hp", 0) or 0)
        except Exception:
            return 0

    def _hp(self, pet: Any) -> int:
        """Get current HP from pet object."""
        try:
            return int(getattr(pet, "hp", 0) or 0)
        except Exception:
            return 0

    # -------------------------------------------------------------------------
    # Damage multiplier (for Dragonkin passive)
    # -------------------------------------------------------------------------
    def get_damage_multiplier(self, ctx: Any, actor: Any) -> float:
        """Get damage multiplier from racial passives.

        Currently handles:
          - Dragonkin: +50% damage if target was brought below 25% HP previous round
        """
        actor_id = self._pet_id(actor)

        # Dragonkin passive
        if self._pet_type(actor) == PET_TYPE_DRAGONKIN:
            rounds_remaining = self.state.dragonkin_buff_rounds.get(actor_id, 0)
            if rounds_remaining > 0:
                return 1.5

        return 1.0

    # -------------------------------------------------------------------------
    # Damage event handling
    # -------------------------------------------------------------------------
    def on_damage_dealt(self, ctx: Any, actor: Any, target: Any, damage: int,
                        target_hp_before: int, target_hp_after: int) -> None:
        """Called when a pet deals damage to another pet.

        Handles:
          - Humanoid: Mark that this pet dealt damage (for end-of-round heal)
          - Dragonkin: Check if target dropped below 25% HP, grant buff
        """
        if damage <= 0:
            return

        actor_id = self._pet_id(actor)
        actor_type = self._pet_type(actor)

        # Humanoid passive: mark damage dealt for end-of-round processing
        if actor_type == PET_TYPE_HUMANOID:
            self.state.humanoid_dealt_damage[actor_id] = True

        # Dragonkin passive: check if target dropped below 25% HP
        if actor_type == PET_TYPE_DRAGONKIN:
            target_max_hp = self._max_hp(target)
            if target_max_hp > 0:
                threshold = target_max_hp * 0.25
                # Was above threshold before, now below or at threshold
                if target_hp_before > threshold and target_hp_after <= threshold:
                    # Grant +50% damage for next round
                    self.state.dragonkin_buff_rounds[actor_id] = 1

    # -------------------------------------------------------------------------
    # Death handling
    # -------------------------------------------------------------------------
    def on_pet_death(self, ctx: Any, pet: Any) -> bool:
        """Called when a pet's HP reaches 0.

        Returns True if the pet should be revived (Undead/Mechanical passive).
        Returns False if the pet should stay dead.

        Handles:
          - Undead: Enter immortality round (will die at end of round)
          - Mechanical: Resurrect at 20% HP (one-time)
        """
        pet_id = self._pet_id(pet)
        pet_type = self._pet_type(pet)

        # Undead passive
        if pet_type == PET_TYPE_UNDEAD:
            # Check if already in immortality or already used it
            if not self.state.undead_immortality.get(pet_id, False) and \
               not self.state.undead_pending_death.get(pet_id, False):
                # Enter immortality round
                self.state.undead_immortality[pet_id] = True
                self.state.undead_pending_death[pet_id] = True
                # Revive with 1 HP (will be immune to damage this round)
                try:
                    pet.hp = 1
                    pet.alive = True
                except Exception:
                    pass
                return True

        # Mechanical passive
        if pet_type == PET_TYPE_MECHANICAL:
            if not self.state.mechanical_revived.get(pet_id, False):
                # Mark as revived
                self.state.mechanical_revived[pet_id] = True
                # Resurrect at 20% HP
                try:
                    max_hp = self._max_hp(pet)
                    pet.hp = max(1, int(max_hp * 0.2))
                    pet.alive = True
                except Exception:
                    pass
                return True

        return False

    def is_undead_immortal(self, pet: Any) -> bool:
        """Check if a pet is currently in Undead immortality phase."""
        pet_id = self._pet_id(pet)
        return self.state.undead_immortality.get(pet_id, False)

    def should_ignore_damage(self, ctx: Any, target: Any) -> bool:
        """Check if damage should be ignored (Undead immortality)."""
        return self.is_undead_immortal(target)

    # -------------------------------------------------------------------------
    # Round lifecycle
    # -------------------------------------------------------------------------
    def on_round_start(self, ctx: Any, pets: list) -> None:
        """Called at start of each round.

        Handles:
          - Tick down Dragonkin buff duration
          - Reset Humanoid damage tracking
        """
        # Reset humanoid damage tracking for new round
        self.state.humanoid_dealt_damage.clear()

        # Tick down dragonkin buff
        expired = []
        for pet_id, rounds in self.state.dragonkin_buff_rounds.items():
            if rounds > 0:
                self.state.dragonkin_buff_rounds[pet_id] = rounds - 1
            if self.state.dragonkin_buff_rounds[pet_id] <= 0:
                expired.append(pet_id)
        for pet_id in expired:
            self.state.dragonkin_buff_rounds.pop(pet_id, None)

    def on_round_end(self, ctx: Any, pets: list) -> None:
        """Called at end of each round.

        Handles:
          - Humanoid: Heal 4% max HP if dealt damage this round
          - Undead: Kill pets in immortality phase
        """
        for pet in pets:
            pet_id = self._pet_id(pet)
            pet_type = self._pet_type(pet)

            # Check if pet is alive
            if not getattr(pet, "alive", False) and not self.is_undead_immortal(pet):
                continue

            # Humanoid passive: heal 4% max HP
            if pet_type == PET_TYPE_HUMANOID:
                if self.state.humanoid_dealt_damage.get(pet_id, False):
                    max_hp = self._max_hp(pet)
                    heal = max(1, int(max_hp * 0.04))
                    try:
                        current_hp = self._hp(pet)
                        new_hp = min(max_hp, current_hp + heal)
                        pet.hp = new_hp
                    except Exception:
                        pass

            # Undead passive: end immortality and kill
            if pet_type == PET_TYPE_UNDEAD:
                if self.state.undead_pending_death.get(pet_id, False):
                    # End immortality
                    self.state.undead_immortality[pet_id] = False
                    # Kill the pet
                    try:
                        pet.hp = 0
                        pet.alive = False
                    except Exception:
                        pass

    # -------------------------------------------------------------------------
    # CC duration reduction (Critter passive)
    # -------------------------------------------------------------------------
    def apply_cc_duration_reduction(self, pet: Any, base_duration: int) -> int:
        """Apply Critter CC duration reduction.

        Critter pets recover 1 round faster from CC effects.
        """
        if self._pet_type(pet) == PET_TYPE_CRITTER:
            return max(0, base_duration - self.state.critter_cc_reduction)
        return base_duration
