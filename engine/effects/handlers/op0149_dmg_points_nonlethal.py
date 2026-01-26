from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(149)
class H_Prop149_DmgPointsNonlethal:
    """Standard points-based damage but cannot reduce target HP below 1.

    ParamLabel: Points,Accuracy,IsPeriodic,,,
    Observed abilities in export:
      - 826 Weakening Blow
      - 1357 Superbark
    """

    PROP_ID = 149

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0)),
            is_periodic=bool(args.get("isperiodic", args.get("is_periodic", 0))),
            override_index=args.get("override_index"),
        )

        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)

        # Non-lethal cap: ensure target HP stays >= 1 after this damage.
        try:
            hp_before = int(getattr(target, "hp", 0) or 0)
        except Exception:
            hp_before = 0

        cap = max(0, hp_before - 1)
        if resolved.final_damage > cap:
            resolved.trace = dict(resolved.trace or {})
            resolved.trace["S_nonlethal_cap"] = {"hp_before": hp_before, "cap": cap}
            resolved.final_damage = int(cap)

        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)

        # For post-damage effects (e.g., Prop32 lifesteal)
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass

        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)

        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
