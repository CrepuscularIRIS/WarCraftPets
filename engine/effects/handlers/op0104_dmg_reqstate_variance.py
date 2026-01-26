from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(104)
class H_Prop104_DmgReqStateVariance:
    """Damage with required state gate and variance override.

    Pack schema: Points,Accuracy,RequiredCasterState,RequiredTargetState,Variance

    Conservative modeling:
      - If RequiredCasterState>0, caster must have that state (sum_state>0).
      - If RequiredTargetState>0, target must have that state (sum_state>0).
      - Variance is treated as a *dampening factor* on the default RNG variance:
          v = 1 - (Variance/100) * (1 - rand_variance)
        (so Variance=0 means use the pipeline's variance).
    """

    PROP_ID = 104

    def _sum_state(self, ctx, pet_id: int, state_id: int) -> int:
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sum_state"):
            try:
                return int(stats.sum_state(ctx, int(pet_id), int(state_id)))
            except Exception:
                pass
        st = getattr(ctx, "states", None)
        if st is not None:
            try:
                return int(st.get(int(pet_id), int(state_id), 0) or 0)
            except Exception:
                return 0
        return 0

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        req_c = int(args.get("required_caster_state", args.get("requiredcasterstate", 0)) or 0)
        req_t = int(args.get("required_target_state", args.get("requiredtargetstate", 0)) or 0)
        if req_c > 0 and self._sum_state(ctx, int(getattr(actor, "id", 0) or 0), req_c) <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="REQ_CASTER_STATE")
            return EffectResult(executed=False, flow_control="CONTINUE")
        if req_t > 0 and self._sum_state(ctx, int(getattr(target, "id", 0) or 0), req_t) <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="REQ_TARGET_STATE")
            return EffectResult(executed=False, flow_control="CONTINUE")

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

        variance_pct = int(args.get("variance", 0) or 0)
        v_override = None
        if variance_pct > 0:
            # Consume one variance roll for determinism.
            roll = float(getattr(ctx, "rng").rand_variance()) if hasattr(getattr(ctx, "rng", None), "rand_variance") else 1.0
            v_override = 1.0 - (float(variance_pct) / 100.0) * (1.0 - float(roll))
            if v_override < 0.0:
                v_override = 0.0
            if v_override > 2.0:
                v_override = 2.0

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0) or 0),
            is_periodic=False,
            override_index=None,
            variance=v_override,
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
