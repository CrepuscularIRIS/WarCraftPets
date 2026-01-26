from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.heal import HealEvent


@register_handler(61)
class H_Prop61_HealSelfReqStateVariance:
    """Heal the caster (self) gated on required states with optional variance dampening.

    DB2 ParamLabel: Points,Accuracy,RequiredCasterState,RequiredTargetState,Variance,

    Observed use (pack): Ability 665 "Consume Corpse".

    Conservative modeling:
      - RequiredCasterState>0 => caster must have that state (sum_state>0).
      - RequiredTargetState>0 => target must have that state (sum_state>0).
      - Accuracy is a standard hit check.
      - Variance is treated as a dampener on the default RNG variance (same as Prop104/100):
            v = 1 - (Variance/100) * (1 - rand_variance)
        Variance=0 => use pipeline default.

    NOTE: This opcode heals *self* (actor) while using the provided (possibly corpse) target
    only for the required-state gate. This matches the common "consume corpse" semantics.
    """

    PROP_ID = 61

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
            roll = 1.0
            if hasattr(getattr(ctx, "rng", None), "rand_variance"):
                try:
                    roll = float(ctx.rng.rand_variance())
                except Exception:
                    roll = 1.0
            v_override = 1.0 - (float(variance_pct) / 100.0) * (1.0 - float(roll))
            if v_override < 0.0:
                v_override = 0.0
            if v_override > 2.0:
                v_override = 2.0

        heal_event = HealEvent(
            source_actor=actor,
            target=actor,  # self-heal
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0) or 0),
            is_periodic=False,
            variance=v_override,
        )
        resolved = ctx.heal_pipeline.resolve(ctx, heal_event)
        ctx.apply_heal(actor, resolved.final_heal, trace=resolved.trace)
        ctx.log.heal(effect_row, actor, actor, resolved.final_heal, trace=resolved.trace)
        ctx.event_bus.emit(Event.ON_HEAL, payload=resolved)
        return EffectResult(executed=True)
