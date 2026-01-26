from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(230)
class H_Prop230_AuraApplyDurationWithStates:
    """Prop230: apply aura with explicit duration (and optional state hints).

    Pack ParamSchema:
      ChainFailure, Accuracy, Duration, MaxAllowed, CasterState, TargetState

    Observed in this bundle:
      - Haunt / Deadly Dreaming: Duration=4, CasterState=68 (unkillable), TargetState=1 (Is_Dead)
      - Forbidden Hourglass: Duration=2, no states

    Conservative semantics:
      - Perform hitcheck; on miss respect ChainFailure.
      - Apply aura_ability_id to target with explicit duration.
      - If MaxAllowed > 1, apply with stack limit (otherwise overwrite as usual).
      - If CasterState is provided and not 0, set that state to 1 on the caster.
      - TargetState is treated as *metadata* in this bundle. To avoid incorrect "Is_Dead" tagging,
        we only set TargetState if it is non-zero and not the Is_Dead state (1).
    """

    PROP_ID = 230

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        cf = int(args.get("chain_failure", args.get("chainfailure", 0)) or 0)
        accuracy = args.get("accuracy", 100)
        duration = int(args.get("duration", 0) or 0)
        max_allowed = int(args.get("max_allowed", args.get("maxallowed", 0)) or 0)
        caster_state = int(args.get("caster_state", args.get("casterstate", 0)) or 0)
        target_state = int(args.get("target_state", args.get("targetstate", 0)) or 0)

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        # Apply aura with explicit duration.
        aura_id = int(getattr(effect_row, "aura_ability_id", 0) or 0)
        if aura_id:
            if max_allowed and max_allowed > 1:
                ar = ctx.aura.apply_with_stack_limit(
                    owner_pet_id=target.id,
                    caster_pet_id=actor.id,
                    aura_id=aura_id,
                    duration=duration,
                    max_stacks=max_allowed,
                    source_effect_id=effect_row.effect_id,
                )
            else:
                ar = ctx.aura.apply(
                    owner_pet_id=target.id,
                    caster_pet_id=actor.id,
                    aura_id=aura_id,
                    duration=duration,
                    tickdown_first_round=False,
                    source_effect_id=effect_row.effect_id,
                )
            ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

        # Optional state hints.
        if caster_state:
            sc = ctx.states.set(actor.id, caster_state, 1)
            ctx.log.state_set(effect_row, actor, actor, sc.state_id, sc.value)

        # Avoid marking Is_Dead (1) as a side-effect. Treat as metadata in this bundle.
        if target_state and target_state != 1:
            sc = ctx.states.set(target.id, target_state, 1)
            ctx.log.state_set(effect_row, actor, target, sc.state_id, sc.value)

        return EffectResult(executed=True)
