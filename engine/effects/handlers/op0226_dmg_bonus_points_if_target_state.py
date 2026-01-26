from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(226)
class H_Prop226_DmgBonusPointsIfTargetState:
    """Damage with an additive bonus when the *target* has a state.

    Pack schema (v1): Points,Accuracy,BonusPoints,BonusState,IsPeriodic,OverrideIndex

    Conservative v1 interpretation:
      - Base damage uses Points.
      - If BonusState is present on the target (sum_state != 0), add BonusPoints.
      - Supports Accuracy (can miss) and IsPeriodic pass-through.
      - OverrideIndex is forwarded into DamageEvent for downstream tracing/future use.
    """

    PROP_ID = 226

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        base_points = int(args.get("points", 0) or 0)
        bonus_points = int(args.get("bonus_points", args.get("bonuspoints", 0)) or 0)
        bonus_state = int(args.get("bonus_state", args.get("bonusstate", 0)) or 0)
        is_periodic = bool(int(args.get("is_periodic", args.get("isperiodic", 0)) or 0))
        override_index = args.get("override_index", args.get("overrideindex", None))

        stats = getattr(ctx, "stats", None)
        target_id = int(getattr(target, "id", 0) or 0)

        def has_state(pet_id: int, state_id: int) -> bool:
            if state_id <= 0:
                return False
            if stats is None or not hasattr(stats, "sum_state"):
                sm = getattr(ctx, "states", None)
                if sm is None:
                    return False
                try:
                    return int(sm.get(pet_id, state_id, 0) or 0) != 0
                except Exception:
                    return False
            try:
                return int(stats.sum_state(ctx, pet_id, state_id) or 0) != 0
            except Exception:
                return False

        points = int(base_points)
        bonus_applied = False
        if bonus_state and has_state(target_id, bonus_state):
            points = int(points + bonus_points)
            bonus_applied = True

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
            is_periodic=bool(is_periodic),
            override_index=override_index,
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
            notes={
                "bonus_state": int(bonus_state),
                "bonus_points": int(bonus_points),
                "bonus_applied": bool(bonus_applied),
            },
        )
