from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(59)
class H_Prop059_DmgDesperation:
    """Desperation damage.

    Observed pack usage (this repo's ability pack): params_raw = [Points, Accuracy, 0, 0, 0, 0].

    Conservative semantics:
      - Standard hit check.
      - If caster current HP is *strictly lower* than target current HP, double the base points.
      - Otherwise, deal base points.

    This matches the common "Desperation" family behavior in Pet Battles where the user
    hits harder when behind.
    """

    PROP_ID = 59

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        base_points = int(args.get("points", 0) or 0)

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

        actor_hp = int(getattr(actor, "hp", 0) or 0)
        target_hp = int(getattr(target, "hp", 0) or 0)

        points = int(base_points)
        desperation = False
        if actor_hp > 0 and target_hp > 0 and actor_hp < target_hp:
            points = int(points * 2)
            desperation = True

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
            notes={"desperation": bool(desperation), "base_points": int(base_points), "points": int(points)},
        )
