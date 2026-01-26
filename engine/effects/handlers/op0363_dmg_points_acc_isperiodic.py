from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(363)
class H_Prop363_DmgPointsAccIsPeriodic:
    """Damage: Points, Accuracy, IsPeriodic.

    Pack schema: Points,Accuracy,IsPeriodic
    """

    PROP_ID = 363

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
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

        is_periodic = bool(int(args.get("is_periodic", args.get("isperiodic", 0)) or 0))
        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0) or 0),
            is_periodic=bool(is_periodic),
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
        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
