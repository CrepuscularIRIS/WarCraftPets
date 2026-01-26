from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(178)
class H_Prop178_CCApplyWithResilient:
    """Apply a crowd-control aura with resilient reduction.

    Params (from pack schema):
      - StatePoints: how many resilient stacks to add on success (commonly 1)
      - Accuracy: hit chance (pct)
      - Duration: base duration in rounds
      - TargetState: resilient state id (commonly 149)
      - ChainFailure: if set, stop the remaining effects in the ability when this fails
      - ReportFailsAsImmune: if set, report resilient failures as IMMUNE instead of MISS
    """

    PROP_ID = 178

    _RESILIENT_CLAMP_MAX = 2

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        sp = args.get("state_points", args.get("statepoints", 0))
        acc = args.get("accuracy", 1)
        duration = args.get("duration", 0)
        target_state = args.get("target_state", args.get("targetstate", 0))
        cf = args.get("chain_failure", args.get("chainfailure", 0))
        report_immune = args.get("report_fails_as_immune", args.get("reportfailsasimmune", 0))

        try:
            sp = int(sp)
        except Exception:
            sp = 0
        try:
            duration = int(duration)
        except Exception:
            duration = 0
        try:
            target_state = int(target_state)
        except Exception:
            target_state = 0
        try:
            cf = int(cf)
        except Exception:
            cf = 0
        try:
            report_immune = int(report_immune)
        except Exception:
            report_immune = 0

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=acc,
            dont_miss=bool(getattr(getattr(ctx, "acc_ctx", None), "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        resilient = 0
        if target_state and hasattr(ctx, "states"):
            try:
                resilient = int(ctx.states.get(int(getattr(target, "id", 0)), int(target_state), 0))
            except Exception:
                resilient = 0

        eff_dur = int(duration) - int(resilient)
        if eff_dur <= 0:
            code = "IMMUNE" if report_immune else "MISS"
            ctx.log.effect_result(effect_row, actor, target, code=code, reason="RESILIENT")
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"), notes={"resilient": resilient})

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(eff_dur),
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

        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(eff_dur), False, ar.reason)

        # Apply resilient stack increment on success.
        if target_state and sp and hasattr(ctx, "states"):
            try:
                pid = int(getattr(target, "id", 0))
                cur = int(ctx.states.get(pid, int(target_state), 0))
                nxt = cur + int(sp)
                if nxt < 0:
                    nxt = 0
                if nxt > self._RESILIENT_CLAMP_MAX:
                    nxt = self._RESILIENT_CLAMP_MAX
                ctx.states.set(pid, int(target_state), int(nxt))
                ctx.log.state_set(effect_row, actor, target, int(target_state), int(nxt))
            except Exception:
                pass

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        executed = (ar.applied or ar.refreshed)
        return EffectResult(
            executed=executed,
            flow_control="CONTINUE",
            notes={"effective_duration": int(eff_dur), "resilient": int(resilient), "aura_reason": ar.reason},
        )
