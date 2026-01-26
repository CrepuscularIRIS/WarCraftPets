from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(29)
class H_Prop29_DmgRequiredState:
    """Damage gated on required states.

    DB2 ParamLabel: Points,Accuracy,RequiredCasterState,RequiredTargetState,IsPeriodic,,
    """

    PROP_ID = 29

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        req_caster = int(args.get("required_caster_state", args.get("requiredcasterstate", 0)) or 0)
        req_target = int(args.get("required_target_state", args.get("requiredtargetstate", 0)) or 0)
        is_periodic = bool(int(args.get("is_periodic", args.get("isperiodic", 0)) or 0))

        stats = getattr(ctx, "stats", None)
        actor_id = int(getattr(actor, "id", 0) or 0)
        target_id = int(getattr(target, "id", 0) or 0)

        def has_state(pet_id: int, state_id: int) -> bool:
            if state_id <= 0:
                return True
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

        if req_caster and not has_state(actor_id, req_caster):
            ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_CASTER:{req_caster}")
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "caster", "state": req_caster})

        if req_target and not has_state(target_id, req_target):
            ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_TARGET:{req_target}")
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "target", "state": req_target})

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
