from __future__ import annotations

"""Prop170: DMG_IF_WEATHER

Ability-pack opcode schema (v1):
  Points,Accuracy,weatherState,Unused,IsPeriodic

Semantics (v0.1 engine):
  - Performs a hit check (Accuracy).
  - If the current battlefield weather matches `weatherState`, deal an *additional*
    damage instance of `Points`.
  - If weather does not match, this effect is a NOOP.

Notes:
  - We route damage through the normal DamagePipeline so that type advantages,
    weather numeric modifiers, crit, variance, shields, etc. remain consistent.
  - The schema includes an `Unused` slot in the exported pack; it is ignored.
"""

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(170)
class H_Prop170_DmgIfWeather:
    PROP_ID = 170

    def apply(self, ctx, actor, target, effect_row, args: dict) -> EffectResult:
        # Weather gating
        weather_state = int(args.get("weather_state", args.get("weatherstate", 0)) or 0)
        cur_weather = 0
        try:
            if hasattr(ctx, "weather") and ctx.weather is not None:
                cur_weather = int(ctx.weather.current(ctx) or 0)
        except Exception:
            cur_weather = 0

        if weather_state <= 0 or cur_weather != weather_state:
            # NOOP (do not stop ability; simply skip)
            try:
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="WEATHER_MISMATCH")
            except Exception:
                pass
            return EffectResult(executed=False)

        # Hit check
        hit, reason = True, "HIT"
        try:
            hit, reason = ctx.hitcheck.compute(
                ctx,
                actor,
                target,
                accuracy=args.get("accuracy", 1),
                dont_miss=bool(getattr(getattr(ctx, "acc_ctx", None), "dont_miss", False)),
            )
        except Exception:
            hit, reason = True, "HIT"

        if not hit:
            try:
                ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            except Exception:
                pass
            return EffectResult(executed=False)

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0) or 0),
            is_periodic=bool(args.get("is_periodic", args.get("isperiodic", 0))),
            override_index=args.get("override_index"),
        )

        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)

        # Post-damage context (lifesteal etc.)
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass

        try:
            ctx.log.damage(effect_row, actor, target, resolved)
        except Exception:
            pass
        try:
            ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
        except Exception:
            pass

        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
