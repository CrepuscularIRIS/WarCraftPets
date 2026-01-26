from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(137)
class H_Prop137_AuraApplyDurationReqStateValue:
    """Prop137: Apply aura with explicit duration, gated by exact state values.

    Pack ParamSchema:
      CasterState, CasterStateValue, Duration, TargetState, TargetStateValue, ChainFailure

    Observed in this bundle:
      - Spiny Carapace (1073): applies aura_ability_id=1075 with Duration=1,
        gated by (CasterState=158 == 1) in upstream DB2.

    Conservative semantics:
      - If CasterState != 0, require ctx.states.get(actor.id, CasterState) == CasterStateValue.
      - If TargetState != 0, require ctx.states.get(target.id, TargetState) == TargetStateValue.
      - Perform a standard hitcheck (fixed Accuracy=100 for this opcode; it has no Accuracy param).
      - On miss or gate-fail, respect ChainFailure (STOP_ABILITY vs CONTINUE).
      - On hit, apply aura_ability_id to target with explicit Duration.
    """

    PROP_ID = 137

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        caster_state = int(args.get("caster_state", args.get("casterstate", 0)) or 0)
        caster_state_value = int(args.get("caster_state_value", args.get("casterstatevalue", 0)) or 0)
        duration = int(args.get("duration", 0) or 0)
        target_state = int(args.get("target_state", args.get("targetstate", 0)) or 0)
        target_state_value = int(args.get("target_state_value", args.get("targetstatevalue", 0)) or 0)
        cf = int(args.get("chain_failure", args.get("chainfailure", 0)) or 0)

        if caster_state:
            if int(ctx.states.get(actor.id, caster_state, 0)) != int(caster_state_value):
                ctx.log.effect_result(effect_row, actor, target, code="SKIP", reason="CASTER_STATE_VALUE")
                return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        if target_state:
            if int(ctx.states.get(target.id, target_state, 0)) != int(target_state_value):
                ctx.log.effect_result(effect_row, actor, target, code="SKIP", reason="TARGET_STATE_VALUE")
                return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        # No Accuracy param is exposed for this opcode in the current pack schema.
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=100,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        aura_id = int(getattr(effect_row, "aura_ability_id", 0) or 0)
        if aura_id <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=aura_id,
            duration=duration,
            tickdown_first_round=False,
            source_effect_id=effect_row.effect_id,
        )

        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and ar.aura is not None:
            try:
                scripts.attach_periodic_to_aura(ar.aura)
                scripts.attach_meta_to_aura(ar.aura)
            except Exception:
                pass

        wm = getattr(ctx, "weather", None)
        if wm is not None and ar.aura is not None:
            try:
                wm.on_aura_applied(ar.aura)
            except Exception:
                pass

        if ar.refreshed and ar.aura is not None:
            ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)

        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        executed = bool(ar.applied or ar.refreshed)
        return EffectResult(
            executed=executed,
            flow_control="CONTINUE",
            notes={
                "duration": int(duration),
                "caster_state": int(caster_state),
                "caster_state_value": int(caster_state_value),
                "target_state": int(target_state),
                "target_state_value": int(target_state_value),
            },
        )
