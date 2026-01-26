from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from engine.constants.type_advantage import type_multiplier
from engine.constants.weather import get_weather_effect


@dataclass
class ResolvedDamage:
    final_damage: int
    trace: Dict[str, Any]


class DamagePipeline:
    """Resolve a DamageEvent into a final integer damage amount.

    v1 goals:
      - Be deterministic given the RNG.
      - Be robust for both "full ctx" (battle loop) and unit-test MiniCtx.
      - Keep trace stable for existing tests.

    Implemented numeric rules (pragmatic subset):
      - Base formula: floor(points * (1 + Power/20))
      - Aura/State modifiers: damage dealt/taken percent, flat adds
      - Type advantage: strong=1.5, weak=2/3
      - Weather: per-attack-type multipliers, optional flat adds
      - Crit: default 5% chance, 1.5x multiplier (configurable via ctx)
      - Racial passives (numeric-only):
          * Beast: +25% damage dealt when below 50% HP
          * Aquatic: -25% damage taken from periodic damage
          * Magic: cap non-periodic hits at 35% of max HP
          * Elemental: ignore negative weather effects (for flat adds and hit handled elsewhere)

    Out-of-scope in v1 (not modeled here):
      - Mechanical revive / Undead extra round / Humanoid lifesteal / Dragonkin kill buff
    """

    def __init__(self, rng):
        self.rng = rng

    def _attack_type(self, ctx: Any, ability_id: int, actor: Any) -> int:
        # Prefer ability's declared type (skill type).
        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and hasattr(scripts, "get_ability_info"):
            try:
                info = scripts.get_ability_info(int(ability_id))
                if isinstance(info, dict) and "pet_type_enum" in info:
                    return int(info.get("pet_type_enum") or 0)
            except Exception:
                pass
        # Fallback: actor family type.
        try:
            return int(getattr(actor, "pet_type", -1) or -1)
        except Exception:
            return -1

    def _pet_type(self, pet: Any) -> int:
        try:
            return int(getattr(pet, "pet_type", -1) or -1)
        except Exception:
            return -1

    def _snap(self, stats: Any, ctx: Any, pet: Any):
        if stats is None:
            return None
        try:
            if hasattr(stats, "snapshot_for_pet"):
                return stats.snapshot_for_pet(ctx, pet)
        except Exception:
            return None
        return None

    def resolve(self, ctx: Any, dmg_event) -> ResolvedDamage:
        points = int(getattr(dmg_event, "points", 0) or 0)
        actor = getattr(dmg_event, "source_actor", None)
        target = getattr(dmg_event, "target", None)

        actor_id = int(getattr(actor, "id", 0) or 0)
        target_id = int(getattr(target, "id", 0) or 0)

        stats = getattr(ctx, "stats", None)

        # --- Effective Power ---
        power = float(getattr(actor, "power", 0) or 0)
        if stats is not None:
            try:
                if hasattr(stats, "effective_power_for_pet"):
                    power = float(stats.effective_power_for_pet(ctx, actor))
                elif hasattr(stats, "effective_power"):
                    power = float(stats.effective_power(ctx, actor_id))
            except Exception:
                power = float(getattr(actor, "power", 0) or 0)

        # --- S1: base damage ---
        base = int(points * (1.0 + power / 20.0))

        # --- State/Aura multipliers + flats ---
        mul_state = 1.0
        flat_state = 0
        is_periodic = bool(getattr(dmg_event, "is_periodic", False))
        if stats is not None:
            try:
                if hasattr(stats, "damage_multiplier"):
                    mul_state = float(stats.damage_multiplier(ctx, actor_id=actor_id, target_id=target_id))
                if hasattr(stats, "damage_flat_add"):
                    flat_state = int(stats.damage_flat_add(ctx, actor_id=actor_id, target_id=target_id, is_periodic=is_periodic))
            except Exception:
                mul_state = 1.0
                flat_state = 0

        # --- Type advantage ---
        atk_override = getattr(dmg_event, "attack_type_override", None)
        if atk_override is not None:
            try:
                attack_type = int(atk_override)
            except Exception:
                attack_type = self._attack_type(ctx, int(getattr(dmg_event, "ability_id", 0) or 0), actor)
        else:
            attack_type = self._attack_type(ctx, int(getattr(dmg_event, "ability_id", 0) or 0), actor)
        target_type = self._pet_type(target)
        mul_type, type_reason = type_multiplier(attack_type, target_type)

        # --- Weather ---
        wid = 0
        mul_weather = 1.0
        flat_weather = 0
        we = None
        wm = getattr(ctx, "weather", None)
        if wm is not None:
            try:
                wid = int(getattr(wm, "current", lambda _ctx: 0)(ctx))
            except Exception:
                wid = 0
            we = get_weather_effect(wid)
            if we is not None:
                try:
                    mul_weather = float(we.damage_mult_by_attack_type.get(int(attack_type), 1.0))
                except Exception:
                    mul_weather = 1.0
                try:
                    flat_weather = int(we.flat_damage_taken_add)
                except Exception:
                    flat_weather = 0

        # Elemental passive: ignore negative weather effects.
        if target_type == 6 and flat_weather > 0:
            flat_weather = 0

        # --- Racial passives (numeric-only) ---
        mul_beast = 1.0
        eff_actor = self._snap(stats, ctx, actor)
        if self._pet_type(actor) == 7 and eff_actor is not None:
            try:
                if int(eff_actor.max_hp) > 0 and int(eff_actor.hp_clamped) * 2 < int(eff_actor.max_hp):
                    mul_beast = 1.25
            except Exception:
                mul_beast = 1.0

        mul_aquatic = 1.0
        if is_periodic and target_type == 8:
            mul_aquatic = 0.50  # Aquatic passive: -50% DoT damage taken

        # --- Dragonkin passive: +50% damage buff from RacialPassiveManager ---
        mul_dragonkin = 1.0
        racial = getattr(ctx, "racial", None)
        if racial is not None and hasattr(racial, "get_damage_multiplier"):
            try:
                mul_dragonkin = float(racial.get_damage_multiplier(ctx, actor))
            except Exception:
                mul_dragonkin = 1.0

        # --- Undead immortality check ---
        undead_immune = False
        if racial is not None and hasattr(racial, "should_ignore_damage"):
            try:
                undead_immune = bool(racial.should_ignore_damage(ctx, target))
            except Exception:
                undead_immune = False

        # --- S7: variance (deterministic) ---
        v_override = getattr(dmg_event, "variance", None)
        if v_override is not None:
            try:
                v = float(v_override)
            except Exception:
                v = float(self.rng.rand_variance())
        else:
            v = float(self.rng.rand_variance())

        # --- Crit ---
        crit_chance = float(getattr(ctx, "crit_chance", 0.05) or 0.05)
        crit_mult = float(getattr(ctx, "crit_mult", 1.5) or 1.5)
        periodic_can_crit = bool(getattr(ctx, "periodic_can_crit", False))
        rcrit = float(self.rng.rand_crit())  # always consume for determinism
        is_crit = False
        if crit_chance > 0.0 and (not is_periodic or periodic_can_crit):
            if rcrit <= crit_chance:
                is_crit = True

        # --- Undead immortality: immune to all damage ---
        if undead_immune:
            trace: Dict[str, Any] = {"S1_base": 0, "S7_variance_roll": 0.0, "undead_immune": True}
            return ResolvedDamage(final_damage=0, trace=trace)

        # --- Compose ---
        dmg_f = float(base)
        dmg_f *= float(mul_state)
        dmg_f *= float(mul_type)
        dmg_f *= float(mul_weather)
        dmg_f *= float(mul_beast)
        dmg_f *= float(mul_aquatic)
        dmg_f *= float(mul_dragonkin)
        dmg_f *= float(v)
        if is_crit:
            dmg_f *= float(crit_mult)

        dmg = int(dmg_f)
        dmg += int(flat_state) + int(flat_weather)

        # Magic passive: cap non-periodic hits to 35% max HP.
        eff_target = self._snap(stats, ctx, target)
        if target_type == 5 and not is_periodic and eff_target is not None:
            try:
                cap = int(float(eff_target.max_hp) * 0.35)
                if cap < 0:
                    cap = 0
                if dmg > cap:
                    dmg = cap
            except Exception:
                pass

        # State thresholds (ignore/clamp).
        if stats is not None and hasattr(stats, "apply_damage_thresholds"):
            try:
                dmg = int(stats.apply_damage_thresholds(ctx, target_id=target_id, dmg=int(dmg)))
            except Exception:
                pass

        trace: Dict[str, Any] = {
            "S1_base": int(base),
            "S7_variance_roll": float(v),
        }
        if getattr(ctx, "trace_extended", False):
            trace.update({
                "S2_power": float(power),
                "S3_mul_state": float(mul_state),
                "S4_attack_type": int(attack_type),
                "S5_target_type": int(target_type),
                "S6_mul_type": float(mul_type),
                "S6_type_reason": str(type_reason),
                "S6_mul_weather": float(mul_weather),
                "S6_weather_state": int(wid),
                "S6_flat_weather": int(flat_weather),
                "S6_mul_beast": float(mul_beast),
                "S6_mul_aquatic": float(mul_aquatic),
                "S6_mul_dragonkin": float(mul_dragonkin),
                "S8_crit_roll": float(rcrit),
                "S8_is_crit": bool(is_crit),
                "S8_crit_mult": float(crit_mult if is_crit else 1.0),
                "S9_flat_state": int(flat_state),
                "S10_is_periodic": bool(is_periodic),
            })

        return ResolvedDamage(final_damage=max(0, int(dmg)), trace=trace)
