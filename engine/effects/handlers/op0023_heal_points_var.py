from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.heal import HealEvent

@register_handler(23)
class H_Prop23_HealPointsVar:
    PROP_ID = 23

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="CONTINUE")

        heal_event = HealEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0)),
            is_periodic=bool(args.get("isperiodic", args.get("is_periodic", 0))),
        )
        resolved = ctx.heal_pipeline.resolve(ctx, heal_event)
        ctx.apply_heal(target, resolved.final_heal, trace=resolved.trace)
        ctx.log.heal(effect_row, actor, target, resolved.final_heal, trace=resolved.trace)
        ctx.event_bus.emit(Event.ON_HEAL, payload=resolved)

        return EffectResult(executed=True)
