from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(28)
class H_Prop28_AuraApplyDurationSpecial:
    PROP_ID = 28

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: Unused,Accuracy,Duration,TickDownFirstRound,,
        accuracy = args.get("accuracy", 1)
        duration = int(args.get("duration", 0))
        tdf = int(args.get("tickdown_first_round", args.get("tickdownfirstround", 0)))

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.unsupported(effect_row, reason="AURA_ID_MISSING")
            return EffectResult(executed=False)

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            tickdown_first_round=bool(tdf),
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

        wm = getattr(ctx, "weather", None)
        if wm is not None and ar.aura is not None:
            try:
                wm.on_aura_applied(ar.aura)
            except Exception:
                pass

        if ar.aura is not None:
            if ar.refreshed:
                ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), bool(tdf))
            ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), bool(tdf), ar.reason)

            stats = getattr(ctx, "stats", None)
            if stats is not None and hasattr(stats, "sync_pet"):
                try:
                    stats.sync_pet(ctx, target)
                except Exception:
                    pass

        executed = (ar.applied or ar.refreshed)
        return EffectResult(executed=executed, notes={"aura_reason": ar.reason})
