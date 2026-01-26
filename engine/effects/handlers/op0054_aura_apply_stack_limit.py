from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(54)
class H_Prop54_AuraApplyStackLimit:
    PROP_ID = 54

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Params: ChainFailure,Accuracy,Duration,MaxStack
        cf = args.get("chain_failure", args.get("chainfailure", 0))
        try:
            cf = int(cf)
        except Exception:
            cf = 0

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
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
        max_stack = args.get("maxstack", args.get("max_stack", 1))

        ar = ctx.aura.apply_with_stack_limit(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            max_stacks=int(max_stack),
            source_effect_id=effect_row.effect_id,
        )

        # Auto-attach periodic DOT/HOT payloads from ScriptDB (if available)
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

        if ar.aura is not None:
            ctx.log.aura_stack(effect_row, actor, target, int(aura_id), int(ar.aura.stacks), int(max_stack))

        if ar.refreshed and ar.aura is not None:
            ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)

        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

        # Best-effort runtime stat sync so newly-applied aura immediately affects
        # subsequent effects in the same cast turn.
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        return EffectResult(executed=(ar.applied or ar.refreshed), flow_control="CONTINUE", notes={"aura_reason": ar.reason})
