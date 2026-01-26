from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(96)
class H_Prop96_DmgStateGate:
    """Damage gated on caster/target states.

    This opcode appears in the pack as a state-gated damage effect:

    - If `CasterState` is non-zero, the effect only executes when the caster has
      that state.
    - If `TargetState` is non-zero, the effect only executes when the target has
      that state.

    If the gate fails, the effect does not execute and the ability continues.

    DB2/Pack ParamLabel: Points,Accuracy,CasterState,TargetState,IsPeriodic,,
    """

    PROP_ID = 96

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        points = int(args.get("points", 0) or 0)
        accuracy = int(args.get("accuracy", 100) or 0)

        caster_state = int(args.get("caster_state", args.get("casterstate", 0)) or 0)
        target_state = int(args.get("target_state", args.get("targetstate", 0)) or 0)
        is_periodic = bool(int(args.get("is_periodic", args.get("isperiodic", 0)) or 0))

        stats = getattr(ctx, "stats", None)
        actor_id = int(getattr(actor, "id", 0) or 0)
        target_id = int(getattr(target, "id", 0) or 0)

        def has_state(pet_id: int, state_id: int) -> bool:
            if state_id <= 0:
                return True
            # Prefer StatsResolver if present; fall back to raw state map.
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

        if caster_state and not has_state(actor_id, caster_state):
            ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_CASTER:{caster_state}")
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "caster", "state": caster_state})

        if target_state and not has_state(target_id, target_state):
            ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_TARGET:{target_state}")
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "target", "state": target_state})

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=accuracy,
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
            points=points,
            is_periodic=is_periodic,
            override_index=None,
        )
        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)

        # Expose last-damage fields for downstream conditionals (best-effort).
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass

        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
