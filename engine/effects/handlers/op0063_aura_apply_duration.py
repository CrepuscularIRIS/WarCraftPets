from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(63)
class H_Prop63_AuraApplyDurationSimple:
    """Prop63: Apply aura with explicit duration.

    ParamLabel (pack): Unused,Accuracy,Duration

    Observed in pack for short-duration HoTs like Tranquility/Photosynthesis/Wish/Renewing Mists.
    We treat slot1 as a non-functional/unused field; if it is non-zero we interpret it as a
    best-effort ChainFailure flag to match the broader opcode family (miss stops ability).
    """

    PROP_ID = 63

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Slot1 is labeled Unused in the pack; keep a conservative compatibility behavior.
        cf = args.get("unused", args.get("chain_failure", args.get("chainfailure", 0)))
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
        if aura_id is None or int(aura_id) == 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False)

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

        if ar.refreshed and ar.aura is not None:
            ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)
        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        return EffectResult(
            executed=bool(ar.applied or ar.refreshed),
            notes={"aura_id": int(aura_id), "duration": int(duration), "aura_reason": ar.reason},
        )
