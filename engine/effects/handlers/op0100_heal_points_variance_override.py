from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.heal import HealEvent


@register_handler(100)
class H_Prop100_HealPointsVarianceOverride:
    """Heal with variance override.

    Pack schema:
      Points,Accuracy,RequiredCasterPetType,RequiredTargetPetType,Variance

    Notes:
      - In the current v0.1 pack, Prop100 appears only in a small set of healing abilities
        (e.g. Rebuild / Healing Stream / Draconic Remedy) as additional heal components.
      - RequiredCasterPetType / RequiredTargetPetType are not enforced here (pack usage is
        inconsistent with standard PetTypeEnum). We keep them as metadata-only for now.
      - Variance is treated as a dampener on the default RNG variance, identical to Prop104:
          v = 1 - (Variance/100) * (1 - rand_variance)
    """

    PROP_ID = 100

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 100),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"miss_reason": reason})

        variance_pct = int(args.get("variance", 0) or 0)
        v_override = None
        if variance_pct > 0:
            # Consume one variance roll for determinism (the pipeline will not consume again).
            roll = 1.0
            if hasattr(getattr(ctx, "rng", None), "rand_variance"):
                try:
                    roll = float(ctx.rng.rand_variance())
                except Exception:
                    roll = 1.0
            v_override = 1.0 - (float(variance_pct) / 100.0) * (1.0 - float(roll))
            if v_override < 0.0:
                v_override = 0.0
            if v_override > 2.0:
                v_override = 2.0

        heal_event = HealEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0) or 0),
            is_periodic=False,
            variance=v_override,
        )

        resolved = ctx.heal_pipeline.resolve(ctx, heal_event)
        ctx.apply_heal(target, resolved.final_heal, trace=resolved.trace)
        ctx.log.heal(effect_row, actor, target, resolved.final_heal, trace=resolved.trace)
        ctx.event_bus.emit(Event.ON_HEAL, payload=resolved)

        return EffectResult(executed=True)
