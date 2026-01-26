from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(141)
class H_Prop141_DmgBonusIfState:
    """Damage with an additive bonus when a state condition holds.

    DB2 ParamLabel: Points,Accuracy,BonusState,BonusPoints,,,

    In v1 we interpret BonusState as a *battlefield/weather* state id. If the current
    weather matches BonusState, we add BonusPoints to Points prior to the standard
    damage formula.
    """

    PROP_ID = 141

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        base_points = int(args.get("points", 0) or 0)
        bonus_state = int(args.get("bonus_state", args.get("bonusstate", 0)) or 0)
        bonus_points = int(args.get("bonus_points", args.get("bonuspoints", 0)) or 0)

        points = int(base_points)
        bonus_applied = False

        weather = getattr(ctx, "weather", None)
        if bonus_state and weather is not None and hasattr(weather, "current"):
            try:
                if int(weather.current(ctx) or 0) == int(bonus_state):
                    points = int(points + bonus_points)
                    bonus_applied = True
            except Exception:
                pass

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 100),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"miss_reason": reason})

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(points),
            is_periodic=False,
            override_index=None,
        )
        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass
        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
        return EffectResult(
            executed=True,
            spawned_damage_events=[dmg_event],
            notes={"bonus_state": int(bonus_state), "bonus_points": int(bonus_points), "bonus_applied": bool(bonus_applied)},
        )
