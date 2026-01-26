from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(229)
class H_Prop229_MarkApplyDuration:
    """Prop229: apply aura with explicit duration (used by type-override marks).

    ParamLabel (pack): ChainFailure,Accuracy,Duration,Unused,CasterState,TargetState
    """

    PROP_ID = 229

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ChainFailure controls whether a miss stops the remaining effects for the ability.
        cf = args.get("chain_failure", args.get("chainfailure", 0))
        try:
            cf = int(cf)
        except Exception:
            cf = 0

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        duration = args.get("duration", 0)
        try:
            duration = int(duration)
        except Exception:
            duration = 0

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            tickdown_first_round=False,
            source_effect_id=effect_row.effect_id,
        )

        # Auto-attach periodic payloads and state binds (if ScriptDB is available)
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

        notes = {
            "aura_reason": ar.reason,
            "duration": int(duration),
            "caster_state": int(args.get("caster_state", 0) or 0),
            "target_state": int(args.get("target_state", 0) or 0),
        }
        executed = (ar.applied or ar.refreshed)
        return EffectResult(executed=executed, flow_control="CONTINUE", notes=notes)
