from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(256)
class H_Prop256_BuffPeriodic:
    PROP_ID = 256

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        """
        Buff with periodic effect (opcode 256)
        Used by ability_id: [615]
        """
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False)

        duration = args.get("duration", 0)
        tdf = args.get("tickdown_first_round", args.get("tickdownfirstround", 0))
        try:
            tdf = bool(int(tdf))
        except Exception:
            tdf = bool(tdf)

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            tickdown_first_round=tdf,
            source_effect_id=effect_row.effect_id,
        )

        # Auto-attach periodic DOT/HOT payloads
        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and ar.aura is not None:
            try:
                scripts.attach_periodic_to_aura(ar.aura)
                scripts.attach_meta_to_aura(ar.aura)
            except Exception:
                pass

        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), tdf, ar.reason)
        
        return EffectResult(executed=(ar.applied or ar.refreshed), notes={"aura_reason": ar.reason})
