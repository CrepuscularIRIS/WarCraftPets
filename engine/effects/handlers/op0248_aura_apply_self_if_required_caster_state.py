from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(248)
class H_Prop248_AuraApplySelfIfRequiredCasterState:
    """Prop248: Apply aura to *self* if RequiredCasterState is present.

    Ability-pack schema:
      Unused, Accuracy, Duration, TickDownFirstRound, RequiredCasterState

    Observed in this pack:
      - Evolving Bite: if Dealt_KillingBlow (302) then apply Attack Boost / Speed Boost to caster
      - The Biggest Hammer: if Special_Auto_Rebuilder (304) then apply Auto-Rebuilder aura to caster
    """

    PROP_ID = 248

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Best-effort ChainFailure: the pack calls it 'Unused' but historically slot0 is often used
        # as chain-failure gate (miss may stop ability).
        chain_failure = args.get("unused", args.get("chainfailure", 0))

        accuracy = args.get("accuracy", 1)
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            try:
                if int(chain_failure) != 0:
                    return EffectResult(executed=False, stop_ability=True)
            except Exception:
                pass
            return EffectResult(executed=False)

        req_state = args.get(
            "requiredcasterstate",
            args.get("required_caster_state", args.get("casterstate", 0))
        )
        try:
            req_state = int(req_state) if req_state is not None else 0
        except Exception:
            req_state = 0

        if req_state:
            if int(ctx.states.get(actor.id, req_state) or 0) == 0:
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason=f"REQ_CASTER_STATE_{req_state}_MISSING")
                return EffectResult(executed=False)

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False)

        duration = args.get("duration", 0)
        tdf = args.get("tickdownfirstround", args.get("tickdown_first_round", 0))
        try:
            tdf = bool(int(tdf))
        except Exception:
            tdf = bool(tdf)

        ctx.aura.apply(
            owner_pet_id=actor.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration) if duration is not None else 0,
            tickdown_first_round=tdf,
            source_effect_id=getattr(effect_row, "effect_id", 0),
        )
        ctx.log.effect_result(effect_row, actor, actor, code="AURA_APPLIED", reason=f"AURA_{aura_id}")
        return EffectResult(executed=True)
