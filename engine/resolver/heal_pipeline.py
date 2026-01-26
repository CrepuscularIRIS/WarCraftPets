from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from engine.constants.weather import get_weather_effect


@dataclass
class ResolvedHeal:
    final_heal: int
    trace: Dict[str, Any]


class HealPipeline:
    """Resolve a HealEvent into a final integer healing amount.

    Implemented numeric rules (subset):
      - Base formula: floor(points * (1 + Power/20))
      - State/Aura modifiers: healing dealt/taken percent
      - Weather: healing taken multiplier (e.g. Moonlight/Darkness)
      - Variance

    Notes:
      - By default, heals do not crit in this v1 engine (configurable via ctx.heal_can_crit).
      - Elemental passive: ignore negative weather effects (e.g. Darkness healing reduction).
    """

    def __init__(self, rng):
        self.rng = rng

    def _pet_type(self, pet: Any) -> int:
        try:
            return int(getattr(pet, "pet_type", -1) or -1)
        except Exception:
            return -1

    def resolve(self, ctx: Any, heal_event) -> ResolvedHeal:
        points = int(getattr(heal_event, "points", 0) or 0)
        actor = getattr(heal_event, "source_actor", None)
        target = getattr(heal_event, "target", None)

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

        # --- S1 base ---
        base = int(points * (1.0 + power / 20.0))

        # --- State/Aura heal multipliers ---
        mul_state = 1.0
        if stats is not None and hasattr(stats, "heal_multiplier"):
            try:
                mul_state = float(stats.heal_multiplier(ctx, actor_id=actor_id, target_id=target_id))
            except Exception:
                mul_state = 1.0

        # --- Weather heal-taken multiplier ---
        wid = 0
        mul_weather = 1.0
        wm = getattr(ctx, "weather", None)
        if wm is not None:
            try:
                wid = int(getattr(wm, "current", lambda _ctx: 0)(ctx))
            except Exception:
                wid = 0
            we = get_weather_effect(wid)
            if we is not None:
                try:
                    mul_weather = float(we.heal_taken_mult)
                except Exception:
                    mul_weather = 1.0

        # Elemental passive: ignore negative weather effects.
        if self._pet_type(target) == 6 and mul_weather < 1.0:
            mul_weather = 1.0

        # --- Variance ---
        v_override = getattr(heal_event, "variance", None)
        if v_override is not None:
            try:
                v = float(v_override)
            except Exception:
                v = float(self.rng.rand_variance())
        else:
            v = float(self.rng.rand_variance())

        # --- Optional crit (off by default) ---
        heal_can_crit = bool(getattr(ctx, "heal_can_crit", False))
        crit_chance = float(getattr(ctx, "crit_chance", 0.05) or 0.05)
        crit_mult = float(getattr(ctx, "crit_mult", 1.5) or 1.5)
        rcrit = float(self.rng.rand_crit())  # always consume
        is_crit = False
        if heal_can_crit and crit_chance > 0.0:
            if rcrit <= crit_chance:
                is_crit = True

        heal_f = float(base)
        heal_f *= float(mul_state)
        heal_f *= float(mul_weather)
        heal_f *= float(v)
        if is_crit:
            heal_f *= float(crit_mult)

        heal = int(heal_f)

        trace: Dict[str, Any] = {
            "S1_base": int(base),
            "S7_variance_roll": float(v),
        }
        if getattr(ctx, "trace_extended", False):
            trace.update({
                "S2_power": float(power),
                "S8_mul_state": float(mul_state),
                "S9_mul_weather": float(mul_weather),
                "S9_weather_state": int(wid),
                "S10_crit_roll": float(rcrit),
                "S10_is_crit": bool(is_crit),
            })

        return ResolvedHeal(final_heal=max(0, int(heal)), trace=trace)
