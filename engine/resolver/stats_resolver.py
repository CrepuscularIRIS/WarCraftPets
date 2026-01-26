from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


# -----------------------------------------------------------------------------
# State IDs (BattlePetState)
#
# We intentionally model only a pragmatic subset that is both common in the data
# and directly impacts battle outcomes.
# -----------------------------------------------------------------------------

STATE_MAX_HEALTH_BONUS = 2            # maxHealthBonus (flat)
STATE_MOD_MAX_HEALTH_PERCENT = 99     # Mod_MaxHealthPercent

STATE_STAT_POWER = 18                 # Stat_Power (flat)
STATE_STAT_SPEED = 20                 # Stat_Speed (flat)
STATE_MOD_SPEED_PERCENT = 25          # Mod_SpeedPercent

STATE_MOD_DAMAGE_DEALT_PERCENT = 23   # Mod_DamageDealtPercent
STATE_MOD_DAMAGE_TAKEN_PERCENT = 24   # Mod_DamageTakenPercent
STATE_ADD_FLAT_DAMAGE_TAKEN = 71      # Add_FlatDamageTaken
STATE_ADD_FLAT_DAMAGE_DEALT = 72      # Add_FlatDamageDealt
STATE_ADD_PERIODIC_DAMAGE_TAKEN = 202 # Add_PeriodicDamageTaken

STATE_MOD_HEALING_DEALT_PERCENT = 65  # Mod_HealingDealtPercent
STATE_MOD_HEALING_TAKEN_PERCENT = 66  # Mod_HealingTakenPercent

STATE_IGNORE_DAMAGE_BELOW = 191       # Ignore_Damage_Below_Threshold
STATE_IGNORE_DAMAGE_ABOVE = 200       # Ignore_Damage_Above_Threshold


@dataclass
class EffectiveStats:
    """Effective stats snapshot.

    raw_speed/raw_power are the *pre-percent* values.
    speed/max_hp include their percent modifiers.
    """

    max_hp: int
    hp_clamped: int
    power: int
    raw_speed: int
    speed: int


class StatsResolver:
    """Resolve effective pet stats and common damage/heal modifiers.

    Sources of modifiers:
      1) ctx.states (Prop31 / direct state values)
      2) ctx.aura meta bindings from ScriptDB:
           aura.meta["state_binds"] = [{"state_id":..,"value":..,"flags":..}, ...]

    Stacking policy:
      - For auras with stacks > 1, each bind is multiplied by stacks.
      - StateManager values are treated as already-aggregated.
    """

    @staticmethod
    def _ensure_base_fields(pet: Any) -> None:
        """Ensure pet.base_* fields exist.

        Many unit tests use a lightweight MiniPet model which does not define
        base stats separately. To prevent drift when max_hp is modified by auras
        (e.g. Mod_MaxHealthPercent), we lazily capture current values as base_*
        the first time we see the pet.
        """
        if not hasattr(pet, "base_max_hp"):
            setattr(pet, "base_max_hp", int(getattr(pet, "max_hp", 0)))
        if not hasattr(pet, "base_power"):
            setattr(pet, "base_power", int(getattr(pet, "power", 0)))
        if not hasattr(pet, "base_speed"):
            setattr(pet, "base_speed", int(getattr(pet, "speed", 0)))

    # ------------------------
    # Low-level aggregation
    # ------------------------
    def sum_state(self, ctx: Any, pet_id: int, state_id: int) -> int:
        pet_id = int(pet_id)
        state_id = int(state_id)

        total = 0
        if hasattr(ctx, "states") and ctx.states is not None:
            try:
                total += int(ctx.states.get(pet_id, state_id, 0) or 0)
            except Exception:
                pass

        if hasattr(ctx, "aura") and ctx.aura is not None:
            try:
                for aura in ctx.aura.list_owner(pet_id).values():
                    meta = getattr(aura, "meta", None) or {}
                    binds = meta.get("state_binds") or []
                    if not isinstance(binds, list):
                        continue
                    stacks = int(getattr(aura, "stacks", 1) or 1)
                    if stacks < 1:
                        stacks = 1
                    for b in binds:
                        if not isinstance(b, dict):
                            continue
                        try:
                            sid = int(b.get("state_id") or 0)
                        except Exception:
                            continue
                        if sid != state_id:
                            continue
                        try:
                            val = int(b.get("value") or 0)
                        except Exception:
                            val = 0
                        total += int(val) * stacks
            except Exception:
                # keep resolver non-fatal
                pass

        return int(total)

    def _pct_mult(self, pct_sum: int) -> float:
        # pct_sum is additive percentage, eg +50 => 1.5, -25 => 0.75
        return max(0.0, (100.0 + float(pct_sum)) / 100.0)

    # ------------------------
    # Effective stats
    # ------------------------
    def effective_power(self, ctx: Any, pet_id: int) -> int:
        pet = getattr(ctx, "pets", {}).get(int(pet_id)) if hasattr(ctx, "pets") else None
        if pet is None:
            return 0
        base = int(getattr(pet, "base_power", getattr(pet, "power", 0)) or 0)
        add = self.sum_state(ctx, int(pet_id), STATE_STAT_POWER)
        return int(base + add)

    def effective_speed(self, ctx: Any, pet_id: int) -> int:
        pet = getattr(ctx, "pets", {}).get(int(pet_id)) if hasattr(ctx, "pets") else None
        if pet is None:
            return 0
        base = int(getattr(pet, "base_speed", getattr(pet, "speed", 0)) or 0)
        add = self.sum_state(ctx, int(pet_id), STATE_STAT_SPEED)
        raw = int(base + add)
        pct = self.sum_state(ctx, int(pet_id), STATE_MOD_SPEED_PERCENT)
        sp = int(raw * self._pct_mult(pct))

        # Flying passive: +50% speed while above 50% HP.
        try:
            if int(getattr(pet, "pet_type", -1) or -1) == 2:
                mhp = int(self.effective_max_hp(ctx, int(pet_id)))
                hp = int(getattr(pet, "hp", 0) or 0)
                if mhp > 0 and hp * 2 > mhp:
                    sp = int(sp * 1.5)
        except Exception:
            pass

        return 1 if sp < 1 else int(sp)

    def effective_max_hp(self, ctx: Any, pet_id: int) -> int:
        pet = getattr(ctx, "pets", {}).get(int(pet_id)) if hasattr(ctx, "pets") else None
        if pet is None:
            return 0
        base = int(getattr(pet, "base_max_hp", getattr(pet, "max_hp", 0)) or 0)
        add = self.sum_state(ctx, int(pet_id), STATE_MAX_HEALTH_BONUS)
        pct = self.sum_state(ctx, int(pet_id), STATE_MOD_MAX_HEALTH_PERCENT)
        mhp = int((base + add) * self._pct_mult(pct))
        return 1 if mhp < 1 else int(mhp)

    def snapshot_effective(self, ctx: Any, pet_id: int) -> EffectiveStats:
        """Compute effective stats by pet_id (requires ctx.pets)."""
        pet_id = int(pet_id)
        pet = getattr(ctx, "pets", {}).get(pet_id) if hasattr(ctx, "pets") else None
        return self._snapshot_effective_for_pet(ctx, pet)

    def snapshot_for_pet(self, ctx: Any, pet: Any) -> EffectiveStats:
        """Compute effective stats for a concrete pet object.

        This is the public counterpart of _snapshot_effective_for_pet and does not require ctx.pets.
        """
        return self._snapshot_effective_for_pet(ctx, pet)

    def _snapshot_effective_for_pet(self, ctx: Any, pet: Any) -> EffectiveStats:
        """Compute effective stats for a concrete pet object.

        This does not rely on ctx.pets, so it is safe for unit tests where pets are
        passed around directly.
        """
        if pet is None:
            return EffectiveStats(max_hp=0, hp_clamped=0, power=0, raw_speed=0, speed=0)

        pid = int(getattr(pet, "id", 0) or 0)

        base_max_hp = int(getattr(pet, "base_max_hp", getattr(pet, "max_hp", 0)) or 0)
        base_power = int(getattr(pet, "base_power", getattr(pet, "power", 0)) or 0)
        base_speed = int(getattr(pet, "base_speed", getattr(pet, "speed", 0)) or 0)

        max_hp = int((base_max_hp + self.sum_state(ctx, pid, STATE_MAX_HEALTH_BONUS)) * self._pct_mult(self.sum_state(ctx, pid, STATE_MOD_MAX_HEALTH_PERCENT)))
        if max_hp < 1:
            max_hp = 1

        power = int(base_power + self.sum_state(ctx, pid, STATE_STAT_POWER))

        raw_speed = int(base_speed + self.sum_state(ctx, pid, STATE_STAT_SPEED))
        speed = int(raw_speed * self._pct_mult(self.sum_state(ctx, pid, STATE_MOD_SPEED_PERCENT)))
        if speed < 1:
            speed = 1

        hp = int(getattr(pet, "hp", 0) or 0)
        hp_clamped = min(int(max_hp), int(max(0, hp)))
        # Flying passive: +50% speed while above 50% HP.
        try:
            if int(getattr(pet, "pet_type", -1) or -1) == 2 and hp_clamped * 2 > max_hp:
                speed = int(speed * 1.5)
        except Exception:
            pass
        return EffectiveStats(max_hp=max_hp, hp_clamped=hp_clamped, power=power, raw_speed=raw_speed, speed=speed)

    def effective_power_for_pet(self, ctx: Any, pet: Any) -> int:
        return int(self._snapshot_effective_for_pet(ctx, pet).power)

    def sync_pet(self, ctx: Any, pet: Any) -> None:
        """Best-effort runtime sync for UI/RL.

        Policy:
          - Do NOT overwrite base_* fields when they exist.
          - For generic pet objects used in tests, infer base_* once and store.
          - Update runtime max_hp/power/speed to *raw* values (speed percent is not folded into pet.speed).
          - Store effective_* into pet.tags for easy inspection.
        """
        if pet is None:
            return

        self._ensure_base_fields(pet)

        eff = self._snapshot_effective_for_pet(ctx, pet)

        # Update runtime values (raw speed, effective max_hp)
        try:
            pet.max_hp = int(eff.max_hp)
        except Exception:
            pass
        try:
            pet.power = int(eff.power)
        except Exception:
            pass
        try:
            pet.speed = int(eff.raw_speed)
        except Exception:
            pass
        try:
            pet.hp = int(eff.hp_clamped)
        except Exception:
            pass

        # Tags (optional)
        try:
            tags = getattr(pet, "tags", None)
            if tags is None or not isinstance(tags, dict):
                tags = {}
                setattr(pet, "tags", tags)
            tags["effective_max_hp"] = int(eff.max_hp)
            tags["effective_power"] = int(eff.power)
            tags["effective_speed"] = int(eff.speed)
        except Exception:
            pass

    def sync(self, ctx: Any, pets: Iterable[Any]) -> None:
        for p in pets:
            self.sync_pet(ctx, p)

    # ------------------------
    # Damage/heal modifiers
    # ------------------------
    def damage_multiplier(self, ctx: Any, *, actor_id: int, target_id: int) -> float:
        dealt = self.sum_state(ctx, int(actor_id), STATE_MOD_DAMAGE_DEALT_PERCENT)
        taken = self.sum_state(ctx, int(target_id), STATE_MOD_DAMAGE_TAKEN_PERCENT)
        return self._pct_mult(dealt) * self._pct_mult(taken)

    def damage_flat_add(self, ctx: Any, *, actor_id: int, target_id: int, is_periodic: bool) -> int:
        add = 0
        add += self.sum_state(ctx, int(actor_id), STATE_ADD_FLAT_DAMAGE_DEALT)
        add += self.sum_state(ctx, int(target_id), STATE_ADD_FLAT_DAMAGE_TAKEN)
        if is_periodic:
            add += self.sum_state(ctx, int(target_id), STATE_ADD_PERIODIC_DAMAGE_TAKEN)
        return int(add)

    def apply_damage_thresholds(self, ctx: Any, *, target_id: int, dmg: int) -> int:
        """Apply common ignore/clamp thresholds.

        Semantics (approx):
          - Ignore_Damage_Below_Threshold: if dmg < threshold => 0
          - Ignore_Damage_Above_Threshold: if dmg > threshold => clamp to threshold
        """
        thr_lo = self.sum_state(ctx, int(target_id), STATE_IGNORE_DAMAGE_BELOW)
        if thr_lo > 0 and dmg < thr_lo:
            return 0
        thr_hi = self.sum_state(ctx, int(target_id), STATE_IGNORE_DAMAGE_ABOVE)
        if thr_hi > 0 and dmg > thr_hi:
            return int(thr_hi)
        return int(dmg)

    def heal_multiplier(self, ctx: Any, *, actor_id: int, target_id: int) -> float:
        dealt = self.sum_state(ctx, int(actor_id), STATE_MOD_HEALING_DEALT_PERCENT)
        taken = self.sum_state(ctx, int(target_id), STATE_MOD_HEALING_TAKEN_PERCENT)
        return self._pct_mult(dealt) * self._pct_mult(taken)
