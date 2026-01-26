from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(50)
class H_Prop50_AuraApplyCondStackLimit:
    PROP_ID = 50

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: ChainFailure,Accuracy,Duration,MaxAllowed,CasterState,TargetState
        cf = args.get("chain_failure", args.get("chainfailure", 0))
        try:
            cf = int(cf)
        except Exception:
            cf = 0

        accuracy = args.get("accuracy", 1)
        duration = int(args.get("duration", 0))
        max_allowed = int(args.get("max_allowed", args.get("maxallowed", 1)))
        caster_state = int(args.get("caster_state", args.get("casterstate", 0)))
        target_state = int(args.get("target_state", args.get("targetstate", 0)))

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.unsupported(effect_row, reason="AURA_ID_MISSING")
            return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")

        # Condition gates (state must be present/true)
        sm = getattr(ctx, "states", None)
        if sm is not None:
            if caster_state and sm.get(getattr(actor, "id", 0), caster_state, 0) <= 0:
                ctx.log.effect_result(effect_row, actor, target, code="COND_FAIL", reason=f"caster_state={caster_state}")
                return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")
            if target_state and sm.get(getattr(target, "id", 0), target_state, 0) <= 0:
                ctx.log.effect_result(effect_row, actor, target, code="COND_FAIL", reason=f"target_state={target_state}")
                return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")

        ar = ctx.aura.apply_with_stack_limit(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            max_stacks=int(max_allowed),
            source_effect_id=effect_row.effect_id,
        )

        # Auto-attach periodic DOT/HOT payloads + metadata from ScriptDB (if available)
        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and ar.aura is not None:
            try:
                scripts.attach_periodic_to_aura(ar.aura)
                scripts.attach_meta_to_aura(ar.aura)
            except Exception:
                pass

        # Weather tracking (if this aura defines a weather state bind)
        wm = getattr(ctx, "weather", None)
        if wm is not None and hasattr(wm, "on_aura_applied") and ar.aura is not None:
            try:
                wm.on_aura_applied(ar.aura)
            except Exception:
                pass

        if ar.aura is not None:
            if ar.refreshed:
                ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)
            ctx.log.aura_stack(effect_row, actor, target, int(aura_id), int(ar.aura.stacks), int(max_allowed))
            ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

            stats = getattr(ctx, "stats", None)
            if stats is not None and hasattr(stats, "sync_pet"):
                try:
                    stats.sync_pet(ctx, target)
                except Exception:
                    pass

        executed = (ar.applied or ar.refreshed)
        return EffectResult(executed=executed, flow_control="CONTINUE", notes={"aura_reason": ar.reason})
